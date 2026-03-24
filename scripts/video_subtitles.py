#!/usr/bin/env python3
"""D5: Subtitle Generator — generate SRT subtitle file from script + timeline.

V1: Uniform word distribution timing (FLAG-4 accepted for V1).
V2: Use Edge TTS SubMaker word-level timestamps for accurate alignment.
"""

from pathlib import Path


def format_srt_time(seconds: float) -> str:
    """Format seconds as SRT timestamp HH:MM:SS,mmm."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def generate_srt(script: dict, timeline: dict, output_path: Path) -> Path:
    """Generate SRT subtitle file from script + timeline.

    Splits narration into ~10-word chunks and distributes them
    evenly across each scene's audio duration.

    Args:
        script: Video script dict with 'scenes'.
        timeline: Dict mapping scene_id → {audio, duration}.
        output_path: Path for the .srt file.

    Returns:
        Path to the generated SRT file.
    """
    offset = 0.0
    entries = []
    chunk_size = 10  # words per subtitle line

    for scene in script['scenes']:
        sid = scene['id']
        if sid not in timeline:
            continue

        duration = timeline[sid]['duration']
        text = scene['narration'].strip()

        if not text:
            offset += duration
            continue

        # Split into chunks
        words = text.split()
        chunks = []
        for j in range(0, len(words), chunk_size):
            chunk = ' '.join(words[j:j + chunk_size])
            chunks.append(chunk)

        if not chunks:
            offset += duration
            continue

        chunk_duration = duration / len(chunks)

        for chunk in chunks:
            start = format_srt_time(offset)
            end = format_srt_time(offset + chunk_duration)
            idx = len(entries) + 1
            entries.append(f"{idx}\n{start} --> {end}\n{chunk}\n")
            offset += chunk_duration

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text('\n'.join(entries), encoding='utf-8')
    return output_path


if __name__ == '__main__':
    import argparse
    import yaml

    parser = argparse.ArgumentParser(description='Generate SRT subtitles from video script')
    parser.add_argument('script', help='Path to script.yaml')
    parser.add_argument('--output', '-o', default='video_output/subtitles.srt',
                        help='Output SRT path')
    args = parser.parse_args()

    script = yaml.safe_load(Path(args.script).read_text())

    # Reconstruct timeline from audio files
    from pydub import AudioSegment
    audio_dir = Path(args.script).parent / 'audio'
    if not audio_dir.exists():
        audio_dir = Path('video_output/audio')
    timeline = {}
    for scene in script['scenes']:
        audio_path = audio_dir / f"{scene['id']}.mp3"
        if audio_path.exists():
            audio = AudioSegment.from_mp3(str(audio_path))
            timeline[scene['id']] = {
                'audio': str(audio_path),
                'duration': len(audio) / 1000.0,
            }

    result = generate_srt(script, timeline, Path(args.output))
    print(f"✅ Subtitles: {result} ({len(open(str(result)).readlines())} lines)")
