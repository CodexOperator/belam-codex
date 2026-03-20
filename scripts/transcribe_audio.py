#!/usr/bin/env python3
"""
Audio Transcription via faster-whisper.

Usage:
    python3 scripts/transcribe_audio.py <audio_file> [--model small] [--json]
"""

import argparse
import json
import sys
from pathlib import Path


def transcribe(audio_path: str, model_size: str = "small") -> dict:
    """Transcribe an audio file and return results."""
    from faster_whisper import WhisperModel

    path = Path(audio_path)
    if not path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    model = WhisperModel(model_size, device="cpu", compute_type="int8")
    segments, info = model.transcribe(str(path), beam_size=5)

    result_segments = []
    full_text = ""
    for seg in segments:
        result_segments.append({
            "start": round(seg.start, 1),
            "end": round(seg.end, 1),
            "text": seg.text.strip(),
        })
        full_text += seg.text

    return {
        "file": str(path),
        "language": info.language,
        "language_probability": round(info.language_probability, 2),
        "text": full_text.strip(),
        "segments": result_segments,
    }


def main():
    parser = argparse.ArgumentParser(description="Transcribe audio files")
    parser.add_argument("audio_file", help="Path to audio file (ogg, mp3, wav, etc.)")
    parser.add_argument("--model", default="small", choices=["tiny", "base", "small", "medium"],
                        help="Whisper model size (default: small)")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    try:
        result = transcribe(args.audio_file, args.model)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(result["text"])


if __name__ == "__main__":
    main()
