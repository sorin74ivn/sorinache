---
name: video-editor
description: Local video editing with Python and FFmpeg for cutting, joining, text overlays, background music and export.
version: 1.0.0
---

# Video Editor

This skill provides local video editing using Python and FFmpeg.

## Role

Hermes analyzes the user request and determines the required editing operations. The Python script executes the operations, while FFmpeg performs the actual video processing locally.

## Operations

- trim a video
- join multiple videos
- add text overlays
- add background music
- export the final video

## Folders

Source videos are stored in /opt/media/Video/inbox.
Edited videos are stored in /opt/media/Video/edited.

## Subtitles

- Generate English subtitles from speech using the local faster-whisper model.
- Detect the spoken language automatically.
- Translate non-English speech to English when English subtitles are requested.
- Keep subtitle timing synchronized with the speech.
- Save subtitle files in /opt/media/Video/edited.
- Burn subtitles into the final video when the user requests visible subtitles.
## Workflow

When the user requests video editing or automatic video improvement, use the local video-editor pipeline.
Run /opt/data/skills/video-editor/scripts/auto_pipeline.py with the source video from /opt/media/Video/inbox.
Use the resulting *_FINAL.mp4 as the final video.
Preserve the original source video.

## Rules

- Use local Python and FFmpeg for standard video editing.
- Do not use video generation services for standard editing tasks.
- Keep source videos in /opt/media/Video/inbox.
- Save edited videos and subtitle files in /opt/media/Video/edited.
- Verify every output file exists and is non-empty before reporting success.
- Preserve the original source video and avoid unnecessary quality loss.
- Apply only useful changes; do not apply every effect automatically.
