#!/usr/bin/env python3
"""D6: Thumbnail Generator — generate 1280x720 YouTube thumbnail."""

from pathlib import Path


# Reuse color palette from video_visuals
COLORS = {
    'bg': '#1a1a2e',
    'text': '#ffffff',
    'accent': '#e6b800',
}


def generate_thumbnail(
    title: str,
    subtitle: str = '',
    output_path: Path = None,
    width: int = 1280,
    height: int = 720,
) -> Path:
    """Generate a YouTube thumbnail image.

    Args:
        title: Main title text.
        subtitle: Optional subtitle text.
        output_path: Path for the PNG output.
        width: Thumbnail width (default 1280 for YouTube).
        height: Thumbnail height (default 720 for YouTube).

    Returns:
        Path to the generated thumbnail.
    """
    from PIL import Image, ImageDraw, ImageFont

    img = Image.new('RGB', (width, height), color=COLORS['bg'])
    draw = ImageDraw.Draw(img)

    # Load fonts
    font_title = None
    font_sub = None
    _font_pairs = [
        ('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
         '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'),
        ('/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf',
         '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf'),
    ]
    for bold_path, regular_path in _font_pairs:
        if Path(bold_path).exists():
            font_title = ImageFont.truetype(bold_path, 48)
            reg = regular_path if Path(regular_path).exists() else bold_path
            font_sub = ImageFont.truetype(reg, 28)
            break

    if font_title is None:
        font_title = ImageFont.load_default()
        font_sub = font_title

    # Wrap title
    max_chars = 30
    words = title.split()
    lines = []
    current = []
    for word in words:
        test = ' '.join(current + [word])
        if len(test) > max_chars and current:
            lines.append(' '.join(current))
            current = [word]
        else:
            current.append(word)
    if current:
        lines.append(' '.join(current))

    # Center text block
    line_height = 60
    total_h = len(lines) * line_height + (40 if subtitle else 0)
    y_start = (height - total_h) // 2

    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font_title)
        tw = bbox[2] - bbox[0]
        x = (width - tw) // 2
        draw.text((x, y_start + i * line_height), line, fill=COLORS['text'], font=font_title)

    # Accent line
    accent_y = y_start + len(lines) * line_height + 5
    draw.rectangle([width // 4, accent_y, 3 * width // 4, accent_y + 3], fill=COLORS['accent'])

    if subtitle:
        bbox = draw.textbbox((0, 0), subtitle, font=font_sub)
        tw = bbox[2] - bbox[0]
        x = (width - tw) // 2
        draw.text((x, accent_y + 15), subtitle, fill=COLORS['accent'], font=font_sub)

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(str(output_path))

    return output_path


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Generate YouTube thumbnail')
    parser.add_argument('title', help='Video title')
    parser.add_argument('--subtitle', '-s', default='', help='Subtitle text')
    parser.add_argument('--output', '-o', default='video_output/thumbnail.png',
                        help='Output PNG path')
    args = parser.parse_args()

    result = generate_thumbnail(args.title, args.subtitle, Path(args.output))
    print(f"✅ Thumbnail: {result}")
