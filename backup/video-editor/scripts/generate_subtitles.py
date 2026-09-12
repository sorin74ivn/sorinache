import sys
from pathlib import Path

sys.path.insert(0, "/opt/data/lazy-packages")

from faster_whisper import WhisperModel

MODEL = "/opt/data/.cache/huggingface/hub/models--Systran--faster-whisper-base/snapshots/ebe41f70d5b6dfa9166e2c581c45c9c0cfc57b66"

def srt_time(seconds):
    ms = int(round(seconds * 1000))
    h = ms // 3600000
    ms %= 3600000
    m = ms // 60000
    ms %= 60000
    s = ms // 1000
    ms %= 1000
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

def generate_subtitles(input_file, output_srt):
    model = WhisperModel(MODEL, device="cpu", compute_type="int8")
    segments, info = model.transcribe(
        str(input_file),
        task="translate",
        vad_filter=True
    )

    lines = []
    for number, segment in enumerate(segments, 1):
        text = segment.text.strip()
        if not text:
            continue
        lines.append(str(number))
        lines.append(f"{srt_time(segment.start)} --> {srt_time(segment.end)}")
        lines.append(text)
        lines.append("")

    Path(output_srt).write_text("\n".join(lines), encoding="utf-8")
    print("SUBTITLES CREATED: " + str(output_srt))
    print(f"DETECTED LANGUAGE: {info.language}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: generate_subtitles.py INPUT_VIDEO OUTPUT_SRT")
        raise SystemExit(2)
    generate_subtitles(sys.argv[1], sys.argv[2])
