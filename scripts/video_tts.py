#!/usr/bin/env python3
"""D2: TTS Engine — generate voiceover audio for each scene using Edge TTS.

Edge TTS is free, async, high quality. No API key needed.
Per FLAG-5: skips scenes whose audio already exists (stage-level resume).
"""

import asyncio
from pathlib import Path
from typing import Optional


async def generate_scene_audio(
    scene_id: str,
    narration: str,
    voice: str,
    output_dir: Path,
) -> dict:
    """Generate audio for a single scene.

    Returns dict with 'audio' path and 'duration' in seconds.
    """
    import edge_tts
    from pydub import AudioSegment

    audio_path = output_dir / f"{scene_id}.mp3"

    # FLAG-5: skip if already exists
    if audio_path.exists() and audio_path.stat().st_size > 100:
        audio = AudioSegment.from_mp3(str(audio_path))
        return {
            'audio': str(audio_path),
            'duration': len(audio) / 1000.0,
        }

    communicate = edge_tts.Communicate(narration, voice=voice)
    await communicate.save(str(audio_path))

    audio = AudioSegment.from_mp3(str(audio_path))
    return {
        'audio': str(audio_path),
        'duration': len(audio) / 1000.0,
    }


async def generate_voiceover(script: dict, output_dir: Path) -> dict:
    """Generate audio files for all scenes.

    Args:
        script: Video script dict with 'scenes' and 'voice'.
        output_dir: Directory for audio output files.

    Returns:
        dict mapping scene_id → {audio, duration}.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    voice = script.get('voice', 'en-US-GuyNeural')

    timeline = {}
    for scene in script['scenes']:
        result = await generate_scene_audio(
            scene['id'],
            scene['narration'],
            voice,
            output_dir,
        )
        timeline[scene['id']] = result
        print(f"  🔊 {scene['id']}: {result['duration']:.1f}s")

    total = sum(v['duration'] for v in timeline.values())
    print(f"  Total audio: {total:.1f}s ({total/60:.1f}min)")
    return timeline


def generate_voiceover_sync(script: dict, output_dir: Path) -> dict:
    """Synchronous wrapper for generate_voiceover."""
    return asyncio.run(generate_voiceover(script, output_dir))


if __name__ == '__main__':
    import argparse
    import yaml

    parser = argparse.ArgumentParser(description='Generate TTS audio from video script')
    parser.add_argument('script', help='Path to script.yaml')
    parser.add_argument('--output-dir', '-o', default='video_output/audio',
                        help='Output directory for audio files')
    args = parser.parse_args()

    script = yaml.safe_load(Path(args.script).read_text())
    timeline = generate_voiceover_sync(script, Path(args.output_dir))
    print(f"\n✅ Generated {len(timeline)} audio files")
