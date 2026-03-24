#!/usr/bin/env python3
"""D7: Report-to-Video Orchestrator CLI.

Coordinates the full pipeline: report → script → TTS → visuals → video.
Each stage is independently runnable for iteration.

Usage:
  python3 scripts/report_to_video.py report.md                      # Full pipeline
  python3 scripts/report_to_video.py report.md --script-only         # Generate script for review
  python3 scripts/report_to_video.py report.md --from-script out/script.yaml  # Resume from edited script
  python3 scripts/report_to_video.py report.md --assets-only         # Generate audio + visuals only
  python3 scripts/report_to_video.py report.md --preview             # First scene only (fast iteration)
"""

import argparse
import asyncio
import sys
import yaml
from pathlib import Path

# Add scripts dir to path
sys.path.insert(0, str(Path(__file__).parent))

from video_script_generator import generate_script
from video_tts import generate_voiceover
from video_visuals import generate_all_visuals
from video_assembler import assemble_video
from video_subtitles import generate_srt
from video_thumbnail import generate_thumbnail


def main():
    parser = argparse.ArgumentParser(
        description='Report → YouTube Video Pipeline',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s machinelearning/.../validate-scheme-b_analysis_report.md
  %(prog)s report.md --script-only --output-dir ./my_video
  %(prog)s report.md --from-script ./my_video/script.yaml
  %(prog)s report.md --preview --voice en-US-AriaNeural
        """,
    )
    parser.add_argument('report', help='Path to report (markdown)')
    parser.add_argument('--script-only', action='store_true',
                        help='Generate script.yaml only (for review)')
    parser.add_argument('--from-script', metavar='YAML',
                        help='Resume from an existing/edited script.yaml')
    parser.add_argument('--assets-only', action='store_true',
                        help='Generate audio + visuals but skip final assembly')
    parser.add_argument('--preview', action='store_true',
                        help='Process only the first scene (fast iteration)')
    parser.add_argument('--output-dir', '-o', default='video_output',
                        help='Output directory (default: video_output/)')
    parser.add_argument('--voice', default='en-US-GuyNeural',
                        help='Edge TTS voice (default: en-US-GuyNeural)')
    parser.add_argument('--title', help='Override video title')
    parser.add_argument('--resolution', default='1920x1080',
                        help='Video resolution (default: 1920x1080)')
    parser.add_argument('--fps', type=int, default=30, help='Video FPS (default: 30)')
    parser.add_argument('--bitrate', default='8000k', help='Video bitrate (default: 8000k)')
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # ── Stage 1: Script ──────────────────────────────────────────────────────
    if args.from_script:
        print(f"📋 Loading script from {args.from_script}")
        script = yaml.safe_load(Path(args.from_script).read_text())
    else:
        print(f"📋 Generating script from {args.report}")
        script = generate_script(
            args.report,
            output_dir=str(output_dir),
            voice=args.voice,
            title=args.title,
            resolution=args.resolution,
        )
        print(f"   {len(script['scenes'])} scenes, ~{script['duration_target']}s target")

        if args.script_only:
            script_path = output_dir / 'script.yaml'
            print(f"\n✅ Script saved: {script_path}")
            print("   Review and edit, then re-run with --from-script")
            return

    # Preview mode: trim to first scene
    if args.preview:
        script['scenes'] = script['scenes'][:1]
        print(f"   🔍 Preview mode: processing only '{script['scenes'][0]['id']}'")

    # ── Stage 2: TTS Audio ───────────────────────────────────────────────────
    print(f"\n🔊 Generating voiceover ({args.voice})...")
    audio_dir = output_dir / 'audio'
    timeline = asyncio.run(generate_voiceover(script, audio_dir))

    # ── Stage 3: Visuals ─────────────────────────────────────────────────────
    print(f"\n🎨 Generating visuals...")
    visuals_dir = output_dir / 'visuals'
    generate_all_visuals(script, visuals_dir)

    if args.assets_only:
        print(f"\n✅ Assets generated in {output_dir}/")
        print("   audio/ — voiceover MP3 files")
        print("   visuals/ — charts, animations, title cards")
        return

    # ── Stage 4: Assemble Video ──────────────────────────────────────────────
    print(f"\n🎬 Assembling video...")
    video_path = output_dir / 'final.mp4'
    assemble_video(
        script, timeline, output_dir, video_path,
        fps=args.fps, bitrate=args.bitrate,
    )

    # ── Stage 5: Subtitles ───────────────────────────────────────────────────
    print(f"\n📝 Generating subtitles...")
    srt_path = output_dir / 'subtitles.srt'
    generate_srt(script, timeline, srt_path)

    # ── Stage 6: Thumbnail ───────────────────────────────────────────────────
    print(f"\n🖼️  Generating thumbnail...")
    thumb_path = output_dir / 'thumbnail.png'
    generate_thumbnail(script['title'], '', thumb_path)

    # ── Summary ──────────────────────────────────────────────────────────────
    total_duration = sum(v['duration'] for v in timeline.values())
    print(f"\n{'='*60}")
    print(f"✅ Video pipeline complete!")
    print(f"   📺 Video:      {video_path}")
    print(f"   📝 Subtitles:  {srt_path}")
    print(f"   🖼️  Thumbnail:  {thumb_path}")
    print(f"   📋 Script:     {output_dir / 'script.yaml'}")
    print(f"   ⏱️  Duration:   {total_duration:.0f}s ({total_duration/60:.1f}min)")
    print(f"   🎬 Scenes:     {len(script['scenes'])}")
    print(f"{'='*60}")


if __name__ == '__main__':
    main()
