import base64
import json
import tempfile
import unittest
from email import message_from_bytes

from gmail_adapter import (
    GmailAdapter,
    SendValidationError,
    audit_token_scopes,
    build_parser,
    redact_secrets,
    validate_send_arguments,
)


class FakeRequest:
    def __init__(self, result):
        self.result = result

    def execute(self):
        return self.result


class FakeSendRequest(FakeRequest):
    def __init__(self):
        super().__init__({"id": "sent-1"})


class FakeMessages:
    def __init__(self):
        self.send_calls = 0
        self.list_calls = 0

    def send(self, **_kwargs):
        self.send_calls += 1
        return FakeSendRequest()

    def list(self, **_kwargs):
        self.list_calls += 1
        return FakeRequest({})


class FakeDrafts:
    def __init__(self):
        self.create_kwargs = None
        self.get_kwargs = None

    def create(self, **kwargs):
        self.create_kwargs = kwargs
        return FakeRequest({"id": "draft-1", "message": {"id": "message-1"}})

    def get(self, **kwargs):
        self.get_kwargs = kwargs
        return FakeRequest({
            "id": "draft-1",
            "message": {"id": "message-1", "threadId": "thread-1", "labelIds": ["DRAFT"]},
        })


class FakeUsers:
    def __init__(self):
        self.messages_api = FakeMessages()
        self.drafts_api = FakeDrafts()
        self.profile_kwargs = None

    def messages(self):
        return self.messages_api

    def drafts(self):
        return self.drafts_api

    def getProfile(self, **kwargs):
        self.profile_kwargs = kwargs
        return FakeRequest({"emailAddress": "self@example.com", "historyId": "42"})


class FakeService:
    def __init__(self):
        self.users_api = FakeUsers()

    def users(self):
        return self.users_api


class GmailAdapterTests(unittest.TestCase):
    def test_constructing_adapter_never_sends_mail(self):
        service = FakeService()

        GmailAdapter(service_factory=lambda: service)

        self.assertEqual(service.users_api.messages_api.send_calls, 0)

    def test_send_requires_confirmation_recipient_subject_and_body(self):
        valid = {"confirmed": True, "recipient": "self@example.com", "subject": "Test", "body": "Hello"}
        self.assertEqual(validate_send_arguments(**valid), valid)

        for field, value in (("confirmed", False), ("recipient", ""), ("subject", ""), ("body", "")):
            invalid = dict(valid)
            invalid[field] = value
            with self.subTest(field=field):
                with self.assertRaises(SendValidationError):
                    validate_send_arguments(**invalid)

    def test_draft_create_builds_plain_text_payload_without_sending(self):
        service = FakeService()
        adapter = GmailAdapter(service_factory=lambda: service)

        result = adapter.create_draft(recipient="self@example.com", subject="Subject", body="Body")

        request = service.users_api.drafts_api.create_kwargs
        self.assertEqual(request["userId"], "me")
        self.assertEqual(result, {"id": "draft-1", "message_id": "message-1"})
        raw = base64.urlsafe_b64decode(request["body"]["message"]["raw"])
        message = message_from_bytes(raw)
        self.assertEqual(message["To"], "self@example.com")
        self.assertEqual(message["Subject"], "Subject")
        self.assertEqual(message.get_payload(decode=True), b"Body")
        self.assertEqual(service.users_api.messages_api.send_calls, 0)

    def test_draft_verify_returns_metadata_without_body(self):
        service = FakeService()
        adapter = GmailAdapter(service_factory=lambda: service)

        result = adapter.verify_draft("draft-1")

        self.assertEqual(service.users_api.drafts_api.get_kwargs, {"userId": "me", "id": "draft-1", "format": "metadata"})
        self.assertEqual(result, {"id": "draft-1", "message_id": "message-1", "thread_id": "thread-1", "labels": ["DRAFT"]})

    def test_health_is_readonly_and_never_reads_inbox(self):
        service = FakeService()
        adapter = GmailAdapter(service_factory=lambda: service)

        result = adapter.health_readonly()

        self.assertEqual(service.users_api.profile_kwargs, {"userId": "me"})
        self.assertEqual(service.users_api.messages_api.list_calls, 0)
        self.assertEqual(result, {"status": "ok", "history_id": "42"})

    def test_scope_audit_emits_only_scopes_and_redacts_secrets(self):
        token = {
            "scopes": ["https://www.googleapis.com/auth/gmail.readonly"],
            "token": "access-secret",
            "refresh_token": "refresh-secret",
            "client_secret": "client-secret",
        }
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8") as token_file:
            json.dump(token, token_file)
            token_file.flush()
            audit = audit_token_scopes(token_file.name)

        self.assertEqual(audit, {"scopes": token["scopes"]})
        safe = redact_secrets(token)
        self.assertNotIn("access-secret", json.dumps(safe))
        self.assertNotIn("refresh-secret", json.dumps(safe))
        self.assertNotIn("client-secret", json.dumps(safe))

    def test_cli_exposes_separate_safe_commands_and_explicit_send_flag(self):
        parser = build_parser()
        self.assertEqual(parser.parse_args(["health-readonly"]).command, "health-readonly")
        self.assertEqual(parser.parse_args(["draft-verify", "--draft-id", "draft-1"]).command, "draft-verify")
        send = parser.parse_args([
            "send-explicit", "--confirm-send", "--to", "self@example.com", "--subject", "Test", "--body", "Body"
        ])
        self.assertTrue(send.confirm_send)


if __name__ == "__main__":
    unittest.main()
