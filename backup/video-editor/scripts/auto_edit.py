import subprocess
import sys
from pathlib import Path

MIN_SILENCE = 1.2

def probe_duration(video):
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", video],
        capture_output=True, text=True, check=True
    )
    return float(r.stdout.strip())

def detect_silence(video):
    r = subprocess.run(
        ["ffmpeg", "-hide_banner", "-i", video,
         "-af", "silencedetect=noise=-35dB:d=0.8",
         "-f", "null", "-"],
        capture_output=True, text=True
    )
    return r.stderr

def parse_silence(log, duration):
    silences = []
    start = None
    for line in log.splitlines():
        if "silence_start:" in line:
            try:
                start = float(line.split("silence_start:")[1].split()[0])
            except Exception:
                start = None
        elif "silence_end:" in line and start is not None:
            try:
                end = float(line.split("silence_end:")[1].split()[0])
                if end - start >= MIN_SILENCE and start > 0.05 and end < duration - 0.05:
                    silences.append((start, end))
            except Exception:
                pass
            start = None
    return silences

if len(sys.argv) != 2:
    print("Usage: auto_edit.py INPUT_VIDEO")
    sys.exit(1)

video = Path(sys.argv[1])

if not video.exists():
    print("ERROR: input video not found")
    sys.exit(1)

duration = probe_duration(str(video))
log = detect_silence(str(video))
silences = parse_silence(log, duration)

print(f"VIDEO: {video}")
print(f"DURATION: {duration:.2f} seconds")
print(f"INTERNAL SILENCES >= {MIN_SILENCE:.1f}s:")

if not silences:
    print("None")
else:
    for start, end in silences:
        print(f"REMOVE CANDIDATE: {start:.2f} -> {end:.2f} ({end-start:.2f}s)")

print("ANALYSIS COMPLETE - ORIGINAL VIDEO WAS NOT MODIFIED")
