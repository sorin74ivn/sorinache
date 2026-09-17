#!/usr/bin/env python3
"""Minimal Gmail API adapter using the existing Hermes Google OAuth module.

The adapter never starts OAuth, reads mail, or sends mail by default.  Its
Google module path is configurable with GOOGLE_API_MODULE_PATH; the default is
the shared Hermes Google Workspace implementation.
"""

import argparse
import base64
import importlib.util
import json
import os
import sys
from email.mime.text import MIMEText
from pathlib import Path

DEFAULT_GOOGLE_API_MODULE = "/opt/data/skills/productivity/google-workspace/scripts/google_api.py"


class SendValidationError(ValueError):
    """Raised when a caller has not made a fully explicit send request."""


def validate_send_arguments(*, confirmed, recipient, subject, body):
    values = {
        "confirmed": confirmed,
        "recipient": recipient,
        "subject": subject,
        "body": body,
    }
    if not confirmed:
        raise SendValidationError("send requires --confirm-send")
    for name in ("recipient", "subject", "body"):
        if not isinstance(values[name], str) or not values[name].strip():
            raise SendValidationError(f"send requires a non-empty {name}")
    return values


def _message_payload(*, recipient, subject, body):
    message = MIMEText(body, "plain", "utf-8")
    message["To"] = recipient
    message["Subject"] = subject
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode("ascii")
    return {"raw": raw}


def redact_secrets(value):
    """Return a logging-safe copy of nested token-like data."""
    if isinstance(value, dict):
        return {
            key: "[REDACTED]" if any(marker in key.lower() for marker in ("token", "secret", "password", "credential"))
            else redact_secrets(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact_secrets(item) for item in value]
    return value


def audit_token_scopes(token_path):
    """Read only the token's declared scopes; never expose token fields."""
    try:
        payload = json.loads(Path(token_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"scopes": []}
    scopes = payload.get("scopes", [])
    return {"scopes": scopes if isinstance(scopes, list) else []}


def load_existing_google_module(module_path=None):
    """Load the shared Google module instead of creating OAuth/client code."""
    path = Path(module_path or os.environ.get("GOOGLE_API_MODULE_PATH", DEFAULT_GOOGLE_API_MODULE))
    spec = importlib.util.spec_from_file_location("shared_google_api", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load shared Google module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def default_service_factory():
    module = load_existing_google_module()
    return module.build_service("gmail", "v1")


class GmailAdapter:
    def __init__(self, *, service_factory=default_service_factory):
        self._service_factory = service_factory

    def create_draft(self, *, recipient, subject, body):
        result = self._service_factory().users().drafts().create(
            userId="me", body={"message": _message_payload(recipient=recipient, subject=subject, body=body)}
        ).execute()
        return {"id": result["id"], "message_id": result.get("message", {}).get("id", "")}

    def verify_draft(self, draft_id):
        draft = self._service_factory().users().drafts().get(
            userId="me", id=draft_id, format="metadata"
        ).execute()
        message = draft.get("message", {})
        return {
            "id": draft["id"],
            "message_id": message.get("id", ""),
            "thread_id": message.get("threadId", ""),
            "labels": message.get("labelIds", []),
        }

    def health_readonly(self):
        """Check profile availability only; it never lists or fetches messages."""
        try:
            profile = self._service_factory().users().getProfile(userId="me").execute()
        except Exception:
            return {"status": "alert"}
        return {"status": "ok", "history_id": profile.get("historyId", "")}

    def send_explicit(self, *, confirmed, recipient, subject, body):
        validate_send_arguments(
            confirmed=confirmed, recipient=recipient, subject=subject, body=body
        )
        result = self._service_factory().users().messages().send(
            userId="me", body=_message_payload(recipient=recipient, subject=subject, body=body)
        ).execute()
        return {"status": "sent", "id": result["id"], "thread_id": result.get("threadId", "")}


def build_parser():
    parser = argparse.ArgumentParser(description="Safe persistent Gmail API adapter")
    commands = parser.add_subparsers(dest="command", required=True)

    draft_create = commands.add_parser("draft-create", help="create a Gmail draft; does not send")
    draft_create.add_argument("--to", required=True)
    draft_create.add_argument("--subject", required=True)
    draft_create.add_argument("--body", required=True)

    draft_verify = commands.add_parser("draft-verify", help="read draft metadata only")
    draft_verify.add_argument("--draft-id", required=True)

    commands.add_parser("health-readonly", help="check Gmail profile without reading inbox")
    commands.add_parser("scope-audit", help="report only OAuth scope names")

    send = commands.add_parser("send-explicit", help="send only with all fields and confirmation")
    send.add_argument("--confirm-send", action="store_true")
    send.add_argument("--to", required=True)
    send.add_argument("--subject", required=True)
    send.add_argument("--body", required=True)
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    if args.command == "scope-audit":
        module = load_existing_google_module()
        print(json.dumps(audit_token_scopes(module.TOKEN_PATH), ensure_ascii=False))
        return 0

    adapter = GmailAdapter()
    if args.command == "draft-create":
        result = adapter.create_draft(recipient=args.to, subject=args.subject, body=args.body)
    elif args.command == "draft-verify":
        result = adapter.verify_draft(args.draft_id)
    elif args.command == "health-readonly":
        result = adapter.health_readonly()
    else:
        try:
            result = adapter.send_explicit(
                confirmed=args.confirm_send, recipient=args.to, subject=args.subject, body=args.body
            )
        except SendValidationError as error:
            print(json.dumps({"status": "blocked", "reason": str(error)}), file=sys.stderr)
            return 2
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
