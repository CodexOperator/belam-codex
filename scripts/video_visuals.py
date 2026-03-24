#!/usr/bin/env python3
"""D3: Visualization Generator — matplotlib charts, animated charts, and title cards.

V1: matplotlib + Pillow only (no Manim per Q1 — deferred to V2).
Per FLAG-5: skips visuals that already exist.

Three visual types:
  - title_card: Static image with title text (Pillow)
  - chart: Static data chart (matplotlib)
  - animated_chart: Animated chart exported as MP4 (matplotlib.animation)
"""

import re
from pathlib import Path
from typing import Optional

# ── Color palette (from design spec Section 4) ───────────────────────────────
COLORS = {
    'bg': '#1a1a2e',
    'bg_chart': '#16213e',
    'text': '#ffffff',
    'accent': '#e6b800',
    'positive': '#4ade80',
    'negative': '#f87171',
    'grid': '#2a2a4e',
    'muted': '#8888aa',
}


def _setup_matplotlib_style():
    """Configure matplotlib for dark theme consistent with brand."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    plt.rcParams.update({
        'figure.facecolor': COLORS['bg'],
        'axes.facecolor': COLORS['bg_chart'],
        'axes.edgecolor': COLORS['grid'],
        'axes.labelcolor': COLORS['text'],
        'text.color': COLORS['text'],
        'xtick.color': COLORS['muted'],
        'ytick.color': COLORS['muted'],
        'grid.color': COLORS['grid'],
        'grid.alpha': 0.3,
        'font.size': 14,
        'axes.titlesize': 18,
        'figure.dpi': 100,
    })


def render_title_card(
    heading: str,
    subtitle: str = '',
    output_path: Path = None,
    width: int = 1920,
    height: int = 1080,
) -> Path:
    """Render a title card as a PNG image using Pillow."""
    from PIL import Image, ImageDraw, ImageFont

    img = Image.new('RGB', (width, height), color=COLORS['bg'])
    draw = ImageDraw.Draw(img)

    # Try to load a reasonable font, fall back to default
    font_title = None
    font_subtitle = None
    _font_pairs = [
        ('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
         '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'),
        ('/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf',
         '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf'),
    ]
    for bold_path, regular_path in _font_pairs:
        if Path(bold_path).exists():
            font_title = ImageFont.truetype(bold_path, 56)
            reg = regular_path if Path(regular_path).exists() else bold_path
            font_subtitle = ImageFont.truetype(reg, 32)
            break

    if font_title is None:
        font_title = ImageFont.load_default()
        font_subtitle = font_title

    # Wrap title text
    max_chars = 40
    words = heading.split()
    lines = []
    current_line = []
    for word in words:
        test = ' '.join(current_line + [word])
        if len(test) > max_chars and current_line:
            lines.append(' '.join(current_line))
            current_line = [word]
        else:
            current_line.append(word)
    if current_line:
        lines.append(' '.join(current_line))

    # Center vertically
    line_height = 70
    total_height = len(lines) * line_height + (50 if subtitle else 0)
    y_start = (height - total_height) // 2

    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font_title)
        text_width = bbox[2] - bbox[0]
        x = (width - text_width) // 2
        draw.text((x, y_start + i * line_height), line, fill=COLORS['text'], font=font_title)

    if subtitle:
        bbox = draw.textbbox((0, 0), subtitle, font=font_subtitle)
        text_width = bbox[2] - bbox[0]
        x = (width - text_width) // 2
        y = y_start + len(lines) * line_height + 20
        draw.text((x, y), subtitle, fill=COLORS['accent'], font=font_subtitle)

    # Accent line under title
    line_y = y_start + len(lines) * line_height + 5
    draw.rectangle([width // 4, line_y, 3 * width // 4, line_y + 3], fill=COLORS['accent'])

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(str(output_path))

    return output_path


def render_chart(
    heading: str,
    output_path: Path,
    duration: float = 5.0,
    width: int = 1920,
    height: int = 1080,
) -> Path:
    """Render a static chart as PNG.

    Creates a placeholder chart with the section heading.
    Real data integration deferred to V2 when data_source paths are wired.
    """
    _setup_matplotlib_style()
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(width / 100, height / 100))

    # Placeholder: informational chart
    ax.text(0.5, 0.5, heading, transform=ax.transAxes,
            ha='center', va='center', fontsize=28, color=COLORS['accent'],
            fontweight='bold')
    ax.text(0.5, 0.35, '(Visualization placeholder — V2 will use real data)',
            transform=ax.transAxes, ha='center', va='center',
            fontsize=16, color=COLORS['muted'])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis('off')

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(str(output_path), bbox_inches='tight', pad_inches=0.1)
    plt.close(fig)
    return output_path


def render_animated_chart(
    heading: str,
    output_path: Path,
    duration: float = 5.0,
    fps: int = 30,
    width: int = 1920,
    height: int = 1080,
) -> Path:
    """Render an animated chart as MP4 using matplotlib.animation.

    V1: Creates a simple build-up bar animation as placeholder.
    V2: Will wire to real data sources from results JSON.
    """
    _setup_matplotlib_style()
    import matplotlib.pyplot as plt
    import matplotlib.animation as animation
    import numpy as np

    fig, ax = plt.subplots(figsize=(width / 100, height / 100))

    # Sample data — represents a generic bar build-up
    n_bars = 6
    labels = [f'Item {i+1}' for i in range(n_bars)]
    final_values = np.random.uniform(0.3, 1.0, n_bars)
    final_values = np.sort(final_values)[::-1]

    n_frames = int(duration * fps)

    bars = ax.bar(labels, [0] * n_bars,
                  color=[COLORS['positive'] if v > 0.5 else COLORS['accent'] for v in final_values],
                  edgecolor=COLORS['grid'])
    ax.set_ylim(0, 1.2)
    ax.set_title(heading, fontsize=22, pad=20, color=COLORS['accent'])
    ax.set_ylabel('Value')

    def animate(frame):
        progress = min(1.0, frame / (n_frames * 0.7))  # build up in first 70%
        for bar, final_val in zip(bars, final_values):
            bar.set_height(final_val * progress)
        return bars

    anim = animation.FuncAnimation(fig, animate, frames=n_frames, blit=False, repeat=False)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    # Use ffmpeg writer for MP4
    writer = animation.FFMpegWriter(fps=fps, bitrate=5000)
    anim.save(str(output_path), writer=writer)
    plt.close(fig)
    return output_path


def generate_visual(scene: dict, output_dir: Path, resolution: str = '1920x1080') -> Path:
    """Generate a visual asset for a single scene.

    Args:
        scene: Scene dict from script with 'id', 'visual', 'heading', 'duration'.
        output_dir: Directory for visual output.
        resolution: Video resolution string 'WxH'.

    Returns:
        Path to the generated visual file.
    """
    w, h = [int(x) for x in resolution.split('x')]
    visual_type = scene.get('visual', 'title_card')
    heading = scene.get('heading', scene.get('id', 'Scene'))
    duration = scene.get('duration', 10)

    output_dir.mkdir(parents=True, exist_ok=True)

    if visual_type == 'animated_chart':
        out = output_dir / f"{scene['id']}.mp4"
        # FLAG-5: skip if exists
        if out.exists() and out.stat().st_size > 1000:
            return out
        return render_animated_chart(heading, out, duration=min(duration, 10), width=w, height=h)
    elif visual_type == 'chart':
        out = output_dir / f"{scene['id']}.png"
        if out.exists() and out.stat().st_size > 100:
            return out
        return render_chart(heading, out, width=w, height=h)
    else:  # title_card or default
        out = output_dir / f"{scene['id']}.png"
        if out.exists() and out.stat().st_size > 100:
            return out
        return render_title_card(heading, output_path=out, width=w, height=h)


def generate_all_visuals(script: dict, output_dir: Path) -> dict:
    """Generate visuals for all scenes in the script.

    Returns dict mapping scene_id → path.
    """
    resolution = script.get('resolution', '1920x1080')
    results = {}
    for scene in script['scenes']:
        path = generate_visual(scene, output_dir, resolution)
        results[scene['id']] = str(path)
        vtype = scene.get('visual', 'title_card')
        print(f"  🎨 {scene['id']}: {vtype} → {path.name}")
    return results


if __name__ == '__main__':
    import argparse
    import yaml

    parser = argparse.ArgumentParser(description='Generate visuals from video script')
    parser.add_argument('script', help='Path to script.yaml')
    parser.add_argument('--output-dir', '-o', default='video_output/visuals',
                        help='Output directory for visual assets')
    args = parser.parse_args()

    script = yaml.safe_load(Path(args.script).read_text())
    results = generate_all_visuals(script, Path(args.output_dir))
    print(f"\n✅ Generated {len(results)} visual assets")
