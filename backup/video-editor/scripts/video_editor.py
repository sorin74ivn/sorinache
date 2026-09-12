#!/usr/bin/env python3

import argparse
import subprocess
from pathlib import Path
import shlex
import sys
sys.path.insert(0, "/opt/data/lazy-packages")
from faster_whisper import WhisperModel

FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
OUTPUT_DIR = Path("/opt/media/Video/edited")


def run(cmd):
    print("FFmpeg:", " ".join(shlex.quote(str(x)) for x in cmd))
    subprocess.run(cmd, check=True)


def escape_text(text):
    return text.replace(chr(92), chr(92)+chr(92)).replace(chr(58), chr(92)+chr(58)).replace(chr(39), chr(92)+chr(39)).replace(chr(37), chr(92)+chr(37))


def format_srt_time(seconds):
    milliseconds = int(seconds * 1000)
    hours = milliseconds // 3600000
    milliseconds %= 3600000
    minutes = milliseconds // 60000
    milliseconds %= 60000
    secs = milliseconds // 1000
    milliseconds %= 1000
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"


def edit_video(input_file, output_file, start=None, end=None, text=None, music=None, enhance=False):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    cmd = ["ffmpeg", "-y"]

    if start is not None:
        cmd += ["-ss", str(start)]

    cmd += ["-i", str(input_file)]

    if end is not None and start is not None:
        duration = float(end) - float(start)
        cmd += ["-t", str(duration)]
    elif end is not None:
        cmd += ["-to", str(end)]

    if music:
        cmd += ["-stream_loop", "-1", "-i", str(music)]

    filters = []
    if enhance:
        filters.append("eq=contrast=1.05:brightness=0.02:saturation=1.05")

    if text:
        safe = escape_text(text)
        filters.append(
            "drawtext="
            f"fontfile={FONT}:"
            f"text={safe}:"
            "fontcolor=white:"
            "fontsize=48:"
            "borderw=3:"
            "bordercolor=black:"
            "x=(w-text_w)/2:"
            "y=h-120"
        )

    if filters:
        cmd += ["-vf", ",".join(filters)]

    if music:
        cmd += [
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "20",
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest"
        ]
    else:
        cmd += [
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "20",
            "-c:a", "aac",
            "-b:a", "192k",
            "-movflags", "+faststart"
        ]

    cmd += [str(output_file)]
    run(cmd)


def concat_videos(inputs, output_file):
    if len(inputs) < 2:
        raise ValueError("Pentru imbinare sunt necesare cel putin doua videoclipuri.")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    list_file = OUTPUT_DIR / ".concat_list.txt"

    with list_file.open("w", encoding="utf-8") as f:
        for item in inputs:
            path = Path(item).resolve()
            f.write(chr(102)+chr(105)+chr(108)+chr(101)+chr(32)+chr(39)+str(path).replace(chr(39), chr(92)+chr(39))+chr(39)+chr(10))

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(list_file),
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "20",
        "-c:a", "aac",
        "-b:a", "192k",
        "-movflags", "+faststart",
        str(output_file)
    ]

    try:
        run(cmd)
    finally:
        list_file.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description="Editor video local Python + FFmpeg")
    parser.add_argument("--input", action="append", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--start")
    parser.add_argument("--end")
    parser.add_argument("--text")
    parser.add_argument("--music")
    parser.add_argument("--enhance", action="store_true")
    parser.add_argument("--concat", action="store_true")

    args = parser.parse_args()

    output = Path(args.output)

    if args.concat:
        concat_videos(args.input, output)
    else:
        edit_video(
            args.input[0],
            output,
            args.start,
            args.end,
            args.text,
            args.music,
            args.enhance
        )

    if not output.exists():
        raise RuntimeError("Videoclipul rezultat nu a fost creat.")

    print("VIDEO EDITAT CU SUCCES:", output)


if __name__ == "__main__":
    main()
