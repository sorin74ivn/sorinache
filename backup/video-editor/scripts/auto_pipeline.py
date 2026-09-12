import subprocess
import sys
from pathlib import Path

if len(sys.argv) != 2:
    print("Usage: auto_pipeline.py INPUT_VIDEO")
    sys.exit(1)

src = Path(sys.argv[1])

if not src.exists():
    print("ERROR: input video not found")
    sys.exit(1)

base = src.stem
outdir = Path("/opt/media/Video/edited")

auto_video = outdir / f"{base}_AUTO_EDITED.mp4"
srt=outdir/f"{base}_AUTO_EDITED_EN.srt"
final = outdir / f"{base}_FINAL.mp4"

scripts = Path("/opt/data/skills/video-editor/scripts")

print("STEP 1: AUTO EDIT")
subprocess.run([
    "python3", str(scripts / "auto_apply.py"), str(src)
], check=True)

print("STEP 2: ENGLISH SUBTITLES")
subprocess.run([
    "python3", str(scripts / "generate_subtitles.py"),
    str(auto_video), str(srt)
], check=True)

print("STEP 3: BURN SUBTITLES")
subprocess.run([
    "python3", str(scripts / "burn_subtitles.py"),
    str(auto_video), str(srt), str(final)
], check=True)

if not auto_video.is_file() or auto_video.stat().st_size == 0 or not srt.is_file() or srt.stat().st_size == 0 or not final.is_file() or final.stat().st_size == 0:
    print("ERROR: one or more output files are missing or empty")
    sys.exit(1)

print(f"FINAL VIDEO: {final}")
print("PIPELINE COMPLETE")
