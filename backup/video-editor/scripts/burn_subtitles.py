import subprocess
import sys
from pathlib import Path

if len(sys.argv) != 4:
    print("Usage: burn_subtitles.py INPUT_VIDEO INPUT_SRT OUTPUT_VIDEO")
    sys.exit(1)

input_video = sys.argv[1]
input_srt = sys.argv[2]
output_video = sys.argv[3]

filter_text = "subtitles=" + input_srt + ":force_style=FontName=DejaVu Sans\\,FontSize=20\\,PrimaryColour=&H00FFFFFF\\,OutlineColour=&H00000000\\,Outline=2\\,Shadow=1\\,Alignment=2\\,MarginV=50"

cmd = ["ffmpeg", "-y", "-i", input_video, "-vf", filter_text, "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-c:a", "copy", "-movflags", "+faststart", output_video]

print("BURNING ENGLISH SUBTITLES...")
subprocess.run(cmd, check=True)

if Path(output_video).exists():
    print("SUBTITLES BURNED SUCCESSFULLY:", output_video)
else:
    print("ERROR: OUTPUT VIDEO NOT CREATED")
    sys.exit(1)
