#!/usr/bin/env python3
"""D4: Video Assembler — compose visuals + audio into final video using MoviePy 2.x.

Audio is the master clock (per design spec). Visual duration matches audio duration.
MoviePy 2.x API (FLAG-3 verified): imports from moviepy directly.
"""

from pathlib import Path
from typing import Optional


def assemble_video(
    script: dict,
    timeline: dict,
    assets_dir: Path,
    output_path: Path,
    fps: int = 30,
    bitrate: str = '8000k',
) -> Path:
    """Assemble all scene assets into a final video.

    Args:
        script: Video script dict with 'scenes'.
        timeline: Dict mapping scene_id → {audio, duration}.
        assets_dir: Directory containing visual assets (visuals/ subdir).
        output_path: Path for the final video file.
        fps: Frames per second.
        bitrate: Video bitrate string.

    Returns:
        Path to the output video.
    """
    from moviepy import (
        VideoFileClip,
        AudioFileClip,
        ImageClip,
        concatenate_videoclips,
    )

    resolution = script.get('resolution', '1920x1080')
    w, h = [int(x) for x in resolution.split('x')]

    visuals_dir = assets_dir / 'visuals' if (assets_dir / 'visuals').is_dir() else assets_dir
    audio_dir = assets_dir / 'audio' if (assets_dir / 'audio').is_dir() else assets_dir

    clips = []
    for scene in script['scenes']:
        sid = scene['id']
        if sid not in timeline:
            print(f"  ⚠️  Skipping {sid}: no audio in timeline")
            continue

        audio_path = timeline[sid]['audio']
        audio_duration = timeline[sid]['duration']

        # Load audio
        audio_clip = AudioFileClip(str(audio_path))

        # Find visual: prefer .mp4, then .png
        mp4_path = visuals_dir / f"{sid}.mp4"
        png_path = visuals_dir / f"{sid}.png"

        if mp4_path.exists():
            visual_clip = VideoFileClip(str(mp4_path))
            # Loop or trim video to match audio duration
            if visual_clip.duration < audio_duration:
                # Loop the video
                from moviepy import vfx
                n_loops = int(audio_duration / visual_clip.duration) + 1
                visual_clip = visual_clip.with_effects([vfx.Loop(n_loops)])
            visual_clip = visual_clip.subclipped(0, audio_duration)
            # Resize to target resolution
            visual_clip = visual_clip.resized((w, h))
        elif png_path.exists():
            # Static image → video clip with duration
            visual_clip = (
                ImageClip(str(png_path))
                .with_duration(audio_duration)
                .resized((w, h))
            )
        else:
            # Generate a black frame fallback
            print(f"  ⚠️  No visual for {sid}, using black frame")
            from PIL import Image
            import tempfile
            black = Image.new('RGB', (w, h), '#1a1a2e')
            tmp = Path(tempfile.mktemp(suffix='.png'))
            black.save(str(tmp))
            visual_clip = (
                ImageClip(str(tmp))
                .with_duration(audio_duration)
                .resized((w, h))
            )

        # Combine visual + audio
        clip = visual_clip.with_audio(audio_clip)
        clips.append(clip)
        print(f"  🎬 {sid}: {audio_duration:.1f}s")

    if not clips:
        raise ValueError("No clips to assemble!")

    # Concatenate all clips
    final = concatenate_videoclips(clips, method="compose")

    # Export
    output_path.parent.mkdir(parents=True, exist_ok=True)
    final.write_videofile(
        str(output_path),
        fps=fps,
        codec='libx264',
        audio_codec='aac',
        bitrate=bitrate,
        logger='bar',
    )

    # Clean up clips
    for clip in clips:
        clip.close()
    final.close()

    return output_path


if __name__ == '__main__':
    import argparse
    import yaml

    parser = argparse.ArgumentParser(description='Assemble video from script + assets')
    parser.add_argument('script', help='Path to script.yaml')
    parser.add_argument('--assets-dir', '-a', default='video_output',
                        help='Directory containing audio/ and visuals/ subdirs')
    parser.add_argument('--output', '-o', default='video_output/final.mp4',
                        help='Output video path')
    parser.add_argument('--fps', type=int, default=30)
    parser.add_argument('--bitrate', default='8000k')
    args = parser.parse_args()

    script = yaml.safe_load(Path(args.script).read_text())

    # Load timeline from audio files
    audio_dir = Path(args.assets_dir) / 'audio'
    from pydub import AudioSegment
    timeline = {}
    for scene in script['scenes']:
        audio_path = audio_dir / f"{scene['id']}.mp3"
        if audio_path.exists():
            audio = AudioSegment.from_mp3(str(audio_path))
            timeline[scene['id']] = {
                'audio': str(audio_path),
                'duration': len(audio) / 1000.0,
            }

    result = assemble_video(
        script, timeline, Path(args.assets_dir), Path(args.output),
        fps=args.fps, bitrate=args.bitrate,
    )
    print(f"\n✅ Video assembled: {result}")
