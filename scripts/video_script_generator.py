#!/usr/bin/env python3
"""D1: Script Generator — markdown report → structured video script (YAML).

Parses markdown reports by splitting on ## headings, assigns visual types
via a section-name mapping dict, and estimates durations at 150 wpm.

V1: markdown only (no PDF parsing). Per FLAG-2 from critic review.
"""

import re
import yaml
from pathlib import Path
from typing import Optional


# ── Section name → visual type mapping ────────────────────────────────────────
# Default mapping used when no explicit override is provided.
# Keys are lowercased substrings matched against section headings.
SECTION_VISUAL_MAP = {
    'executive summary': 'title_card',
    'summary': 'title_card',
    'introduction': 'title_card',
    'methodology': 'chart',
    'method': 'chart',
    'validation': 'chart',
    'result': 'animated_chart',
    'performance': 'animated_chart',
    'accuracy': 'animated_chart',
    'sharpe': 'animated_chart',
    'turnover': 'animated_chart',
    'phase 1': 'animated_chart',
    'phase 2': 'animated_chart',
    'experiment': 'animated_chart',
    'control': 'chart',
    'baseline': 'chart',
    'architecture': 'title_card',
    'insight': 'title_card',
    'conclusion': 'title_card',
    'recommendation': 'title_card',
    'limitation': 'title_card',
    'appendix': 'title_card',
    'additional': 'title_card',
    'script': 'title_card',
}

# Default visual type for sections that don't match any key
DEFAULT_VISUAL = 'title_card'

# Words per minute for duration estimation
WPM = 150

# Minimum / maximum scene duration (seconds)
MIN_SCENE_DURATION = 10
MAX_SCENE_DURATION = 180


def parse_markdown_sections(text: str) -> list[dict]:
    """Split markdown on ## headings into sections.

    Returns list of {heading, body, level} dicts.
    Level 1 = # heading, Level 2 = ## heading, etc.
    We primarily use ## (level 2) as scene boundaries.
    """
    lines = text.split('\n')
    sections = []
    current = None

    for line in lines:
        m = re.match(r'^(#{1,4})\s+(.+)$', line)
        if m:
            if current:
                sections.append(current)
            level = len(m.group(1))
            current = {
                'heading': m.group(2).strip(),
                'body': '',
                'level': level,
            }
        elif current:
            current['body'] += line + '\n'

    if current:
        sections.append(current)

    return sections


def heading_to_id(heading: str) -> str:
    """Convert heading text to a safe scene id."""
    clean = re.sub(r'[^a-z0-9\s]', '', heading.lower())
    parts = clean.split()[:4]  # max 4 words
    return '_'.join(parts) if parts else 'scene'


def map_visual_type(heading: str) -> str:
    """Map a section heading to a visual type using the mapping dict."""
    h_lower = heading.lower()
    for key, vtype in SECTION_VISUAL_MAP.items():
        if key in h_lower:
            return vtype
    return DEFAULT_VISUAL


def extract_narration(body: str, max_words: int = 300) -> str:
    """Extract narration text from section body.

    Strips markdown formatting, tables, code blocks, and trims to max_words.
    Converts to spoken-word friendly text.
    """
    # Remove code blocks
    text = re.sub(r'```[\s\S]*?```', '', body)
    # Remove inline code
    text = re.sub(r'`[^`]+`', '', text)
    # Remove markdown tables (lines starting with |)
    text = re.sub(r'^\|.*\|$', '', text, flags=re.MULTILINE)
    # Remove table separator lines
    text = re.sub(r'^\s*[-|:]+\s*$', '', text, flags=re.MULTILINE)
    # Remove markdown images
    text = re.sub(r'!\[.*?\]\(.*?\)', '', text)
    # Remove markdown links but keep text
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
    # Remove bold/italic markers
    text = re.sub(r'\*{1,3}([^*]+)\*{1,3}', r'\1', text)
    # Remove HTML-like tags
    text = re.sub(r'<[^>]+>', '', text)
    # Collapse whitespace
    text = re.sub(r'\n{2,}', '\n', text)
    text = re.sub(r'[ \t]+', ' ', text)
    text = text.strip()

    # Trim to max words
    words = text.split()
    if len(words) > max_words:
        words = words[:max_words]
        text = ' '.join(words) + '...'
    else:
        text = ' '.join(words)

    # Light spoken-word cleanup
    # Expand common abbreviations
    text = text.replace('vs.', 'versus')
    text = text.replace('vs ', 'versus ')
    text = text.replace('e.g.', 'for example')
    text = text.replace('i.e.', 'that is')
    text = text.replace('etc.', 'and so on')
    # Remove leftover markdown artifacts
    text = re.sub(r'#+\s*', '', text)

    return text


def estimate_duration(text: str) -> float:
    """Estimate speaking duration in seconds at WPM rate."""
    word_count = len(text.split())
    duration = (word_count / WPM) * 60
    return max(MIN_SCENE_DURATION, min(MAX_SCENE_DURATION, duration))


def generate_script(
    report_path: str,
    output_dir: Optional[str] = None,
    voice: str = 'en-US-GuyNeural',
    title: Optional[str] = None,
    resolution: str = '1920x1080',
) -> dict:
    """Generate a video script from a markdown report.

    Args:
        report_path: Path to the markdown report file.
        output_dir: Optional directory to write script.yaml.
        voice: Edge TTS voice name.
        title: Override title (default: extracted from report).
        resolution: Video resolution string.

    Returns:
        dict: The video script structure.
    """
    report = Path(report_path)
    text = report.read_text(encoding='utf-8')

    sections = parse_markdown_sections(text)
    if not sections:
        raise ValueError(f"No sections found in {report_path}")

    # Extract title from first # heading or use override
    if title is None:
        h1_sections = [s for s in sections if s['level'] == 1]
        if h1_sections:
            title = h1_sections[0]['heading']
        else:
            title = sections[0]['heading']

    # Build scenes from ## (level 2) sections
    scenes = []
    seen_ids = set()

    for section in sections:
        if section['level'] > 2:
            continue  # Skip ### and deeper — they're sub-content
        if section['level'] == 1 and len(sections) > 1:
            continue  # Skip the H1 title — it becomes the video title

        narration = extract_narration(section['body'])
        if not narration or len(narration.split()) < 5:
            continue  # Skip empty or trivially short sections

        scene_id = heading_to_id(section['heading'])
        # Deduplicate ids
        if scene_id in seen_ids:
            scene_id = f"{scene_id}_{len(scenes)}"
        seen_ids.add(scene_id)

        duration = estimate_duration(narration)
        visual = map_visual_type(section['heading'])

        scenes.append({
            'id': scene_id,
            'heading': section['heading'],
            'duration': round(duration, 1),
            'narration': narration,
            'visual': visual,
            'visual_config': {
                'type': visual,
                'heading': section['heading'],
            },
        })

    total_duration = sum(s['duration'] for s in scenes)

    script = {
        'title': title,
        'duration_target': round(total_duration),
        'voice': voice,
        'resolution': resolution,
        'style': 'educational',
        'scenes': scenes,
    }

    if output_dir:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        script_path = out / 'script.yaml'
        script_path.write_text(yaml.dump(script, default_flow_style=False, sort_keys=False))

    return script


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Generate video script from markdown report')
    parser.add_argument('report', help='Path to markdown report')
    parser.add_argument('--output-dir', '-o', help='Output directory for script.yaml')
    parser.add_argument('--voice', default='en-US-GuyNeural', help='Edge TTS voice')
    parser.add_argument('--title', help='Override video title')
    args = parser.parse_args()

    script = generate_script(args.report, args.output_dir, args.voice, args.title)
    if not args.output_dir:
        print(yaml.dump(script, default_flow_style=False, sort_keys=False))
    else:
        print(f"✅ Script saved to {Path(args.output_dir) / 'script.yaml'}")
        print(f"   {len(script['scenes'])} scenes, ~{script['duration_target']}s total")
