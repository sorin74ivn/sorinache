import subprocess
import sys
from pathlib import Path

MIN_SILENCE = 1.2

def duration(video):
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", video],
        capture_output=True, text=True, check=True
    )
    return float(r.stdout.strip())

def silences(video):
    r = subprocess.run(
        ["ffmpeg", "-hide_banner", "-i", video,
         "-af", "silencedetect=noise=-35dB:d=0.8",
         "-f", "null", "-"],
        capture_output=True, text=True
    )
    result = []
    start = None
    for line in r.stderr.splitlines():
        if "silence_start:" in line:
            start = float(line.split("silence_start:")[1].split()[0])
        elif "silence_end:" in line and start is not None:
            end = float(line.split("silence_end:")[1].split()[0])
            if end - start >= MIN_SILENCE:
                result.append((start, end))
            start = None
    return result

if len(sys.argv) != 2:
    print("Usage: auto_apply.py INPUT_VIDEO")
    sys.exit(1)

src = Path(sys.argv[1])
out = Path("/opt/media/Video/edited") / f"{src.stem}_AUTO_EDITED.mp4"

d = duration(str(src))
cuts = silences(str(src))

parts = []
pos = 0.0

for start, end in cuts:
    if start > pos + 0.05:
        parts.append((pos, start))
    pos = end

if pos < d - 0.05:
    parts.append((pos, d))

if len(parts) < 2:
    subprocess.run([
        "ffmpeg", "-y", "-i", str(src),
        "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart",
        str(out)
    ], check=True)
else:
    filters = []
    labels = []

    for i, (start, end) in enumerate(parts):
        filters.append(
            f"[0:v]trim=start={start}:end={end},setpts=PTS-STARTPTS[v{i}]"
        )
        filters.append(
            f"[0:a]atrim=start={start}:end={end},asetpts=PTS-STARTPTS[a{i}]"
        )
        labels.append(f"[v{i}][a{i}]")

    fc = ";".join(filters)
    fc += ";" + "".join(labels) + f"concat=n={len(parts)}:v=1:a=1[outv][outa]"

    subprocess.run([
        "ffmpeg", "-y", "-i", str(src),
        "-filter_complex", fc,
        "-map", "[outv]", "-map", "[outa]",
        "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart",
        str(out)
    ], check=True)

print(f"ORIGINAL: {src}")
print(f"OUTPUT: {out}")
print(f"ORIGINAL DURATION: {d:.2f}s")
print(f"REMOVED SILENCES: {len(cuts)}")
print("AUTO EDIT COMPLETE")
