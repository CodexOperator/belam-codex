"""
codex_codec.py — Bidirectional parser between .codex format and JSON.

.codex format:
  ---
  key: value
  list_key: [a, b, c]
  nested.child: value
  ---
  Markdown body text here.

Rules:
  - YAML frontmatter between --- delimiters
  - Body is markdown text after the closing ---
  - Body stored under 'body' key in the JSON dict
  - Nested objects flatten with dot notation in frontmatter
  - Empty body → no 'body' key in result
"""

from __future__ import annotations

import json
import sys
import yaml
from typing import Iterator, TextIO


# ---------------------------------------------------------------------------
# Custom YAML dumper: keeps multiline strings inline (double-quoted)
# so round-trips don't gain trailing newlines from literal block style.
# ---------------------------------------------------------------------------

class _CompactDumper(yaml.Dumper):
    """YAML Dumper that serializes strings with \n as double-quoted scalars."""


def _str_representer(dumper: yaml.Dumper, data: str) -> yaml.ScalarNode:
    if "\n" in data:
        # Use explicit double-quote style so \n is preserved literally, not as
        # a literal-block scalar that adds a trailing newline on parse.
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style='"')
    return dumper.represent_scalar("tag:yaml.org,2002:str", data)


_CompactDumper.add_representer(str, _str_representer)


# ---------------------------------------------------------------------------
# Flatten / unflatten helpers for dot-notation nesting
# ---------------------------------------------------------------------------

def _flatten(obj: dict, prefix: str = "") -> dict:
    """Recursively flatten nested dict to dot-notation keys."""
    out: dict = {}
    for k, v in obj.items():
        key = f"{prefix}.{k}" if prefix else str(k)
        if isinstance(v, dict):
            out.update(_flatten(v, key))
        else:
            out[key] = v
    return out


def _unflatten(flat: dict) -> dict:
    """Reconstruct nested dict from dot-notation flat dict."""
    out: dict = {}
    for dotkey, val in flat.items():
        parts = str(dotkey).split(".")
        node = out
        for part in parts[:-1]:
            if not isinstance(node.get(part), dict):
                node[part] = {}
            node = node[part]
        node[parts[-1]] = val
    return out


# ---------------------------------------------------------------------------
# Core codec functions
# ---------------------------------------------------------------------------

def to_codex(json_dict: dict) -> str:
    """Convert a JSON dictionary to .codex format (YAML frontmatter + markdown body).

    Keys are serialized as YAML scalars/lists.
    Nested dicts are flattened with dot notation.
    The 'body' key is written as markdown after the closing ---.
    """
    d = dict(json_dict)
    body: str = d.pop("body", "") or ""

    if d:
        flat = _flatten(d)
        frontmatter = yaml.dump(
            flat,
            Dumper=_CompactDumper,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
            width=float("inf"),
        ).rstrip("\n")
        # result ends with \n so body can follow directly
        result = f"---\n{frontmatter}\n---\n"
    else:
        result = ""

    if body:
        # Append body directly; result already ends with \n (or is empty)
        result = result + body if result else body

    return result


def from_codex(codex_str: str) -> dict:
    """Parse a .codex string back to a JSON dictionary.

    If frontmatter is present it is loaded via yaml.safe_load and unflattened.
    Everything after the closing --- becomes the 'body' value (stripped of one
    leading newline that acts as separator).
    """
    s = codex_str

    if not s.startswith("---"):
        # No frontmatter — entire content is body
        return {"body": s} if s else {}

    # Strip the opening ---\n
    after_open = s[3:]
    if after_open.startswith("\n"):
        after_open = after_open[1:]

    # Find closing --- fence
    close_idx = after_open.find("\n---")
    if close_idx == -1:
        # Malformed — treat whole thing as body
        return {"body": s}

    fm_raw = after_open[:close_idx]
    rest = after_open[close_idx + 4:]   # skip the \n---

    # Strip the single separator newline between fence and body
    if rest.startswith("\n"):
        rest = rest[1:]

    flat = yaml.safe_load(fm_raw) or {}
    if not isinstance(flat, dict):
        flat = {}

    result = _unflatten(flat)

    if rest:
        result["body"] = rest

    return result


# ---------------------------------------------------------------------------
# Streaming functions
# ---------------------------------------------------------------------------

def _split_codex_stream(content: str) -> list[str]:
    """Split a stream of concatenated .codex documents into individual strings.

    Document boundaries are detected by counting --- fences:
      fence 1 = open frontmatter
      fence 2 = close frontmatter
      fence 3 = document separator (triggers new document)

    Documents without frontmatter (0 fences) are delimited only at the end
    or by a separator --- encountered while in body context (fence_count >= 2).
    """
    docs: list[str] = []
    buf: list[str] = []
    fence_count = 0
    in_body = False  # True after we've seen at least one closing ---

    lines = content.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]
        if line == "---":
            fence_count += 1
            if fence_count == 1:
                # Opening frontmatter fence OR separator for body-only doc
                if in_body:
                    # We were in body; this starts a new doc
                    docs.append("\n".join(buf))
                    buf = ["---"]
                    fence_count = 1
                    in_body = False
                else:
                    buf.append(line)
            elif fence_count == 2:
                # Closing frontmatter fence
                buf.append(line)
                in_body = True
            else:
                # fence_count >= 3: doc separator (body followed by ---)
                docs.append("\n".join(buf))
                buf = []
                fence_count = 0
                in_body = False
        else:
            if not buf and line == "":
                # Skip leading blank lines between docs
                i += 1
                continue
            if fence_count >= 2 or (fence_count == 0 and buf):
                in_body = True
            buf.append(line)
        i += 1

    if buf and "\n".join(buf).strip():
        docs.append("\n".join(buf))

    return docs


def codex_to_json_stream(codex_stream: TextIO) -> Iterator[dict]:
    """Streaming parser for multiple .codex documents.

    Documents are separated by a standalone --- line that follows body content
    (i.e., the third --- fence encountered triggers a new document).
    """
    content = codex_stream.read()
    for doc in _split_codex_stream(content):
        if doc.strip():
            yield from_codex(doc)


def json_to_codex_stream(json_iter: Iterator[dict]) -> Iterator[str]:
    """Streaming serializer: yields .codex strings for each dict."""
    for d in json_iter:
        yield to_codex(d)


# ---------------------------------------------------------------------------
# MCP codec registration
# ---------------------------------------------------------------------------

def register_codec() -> dict:
    """Return a dict suitable for MCP server integration."""
    return {
        "content_type": "application/x-codex",
        "encode": to_codex,
        "decode": from_codex,
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def _run_tests() -> bool:
    import io
    import os

    passed = 0
    failed = 0

    def check(name: str, condition: bool, detail: str = "") -> None:
        nonlocal passed, failed
        if condition:
            print(f"  ✓ {name}")
            passed += 1
        else:
            print(f"  ✗ {name}" + (f": {detail}" if detail else ""))
            failed += 1

    def norm(d: dict) -> dict:
        """Remove body key if empty string."""
        nd = dict(d)
        if nd.get("body") == "" or nd.get("body") is None:
            nd.pop("body", None)
        return nd

    # ------------------------------------------------------------------ #
    print("\n=== Round-trip tests ===")

    cases = [
        # Basic with body
        {"primitive": "task", "status": "active", "tags": ["a", "b"], "body": "# Hello\nWorld"},
        # Empty body (no key)
        {"primitive": "decision", "status": "accepted"},
        # Unicode
        {"title": "Ünïcödé tëst", "note": "こんにちは", "body": "emoji 🔥"},
        # Nested object (dot notation)
        {"parent": {"child": "value", "other": 42}, "body": "nested test"},
        # Multiline body with trailing newline
        {"status": "ok", "body": "line1\nline2\nline3\n"},
        # Lists
        {"tags": ["x", "y", "z"], "upstream": ["a/b", "c/d"]},
        # Empty dict
        {},
        # Body only (no frontmatter)
        {"body": "just body text\nno frontmatter"},
        # Multiline frontmatter value
        {"notes": "first\nsecond\nthird", "body": "body here"},
        # Special chars
        {"title": 'say "hello" & <escape>', "val": "a: b"},
        # Integer / bool values
        {"count": 42, "active": True, "ratio": 3.14},
    ]

    for i, d in enumerate(cases):
        try:
            encoded = to_codex(d)
            decoded = from_codex(encoded)
            expected = norm(d)
            got = norm(decoded)
            check(
                f"round-trip case {i + 1}",
                got == expected,
                f"\n    encoded:  {repr(encoded)}\n    expected: {expected}\n    got:      {got}",
            )
        except Exception as e:
            check(f"round-trip case {i + 1}", False, str(e))

    # ------------------------------------------------------------------ #
    print("\n=== Workspace primitive tests ===")

    ws = "/home/ubuntu/.openclaw/workspace"
    test_files: list[str] = []
    for subdir in ("tasks", "decisions", "lessons"):
        path = os.path.join(ws, subdir)
        if os.path.isdir(path):
            for fname in sorted(os.listdir(path))[:2]:
                if fname.endswith(".md"):
                    test_files.append(os.path.join(path, fname))

    for fpath in test_files:
        rel = os.path.relpath(fpath, ws)
        try:
            with open(fpath, encoding="utf-8") as f:
                raw = f.read()
            parsed = from_codex(raw)
            roundtrip = from_codex(to_codex(parsed))
            body_ok = parsed.get("body", "") == roundtrip.get("body", "")
            fm_parsed = {k: v for k, v in parsed.items() if k != "body"}
            fm_rt = {k: v for k, v in roundtrip.items() if k != "body"}
            check(f"parse {rel}", body_ok and fm_parsed == fm_rt,
                  "body or frontmatter mismatch on round-trip")
        except Exception as e:
            check(f"parse {rel}", False, str(e))

    # ------------------------------------------------------------------ #
    print("\n=== Edge case tests ===")

    # Empty body key not injected
    d = {"status": "ok"}
    dec = norm(from_codex(to_codex(d)))
    check("empty body not injected", dec == d)

    # No frontmatter
    no_fm = "just plain text\nno YAML here"
    check("no frontmatter → body key", from_codex(no_fm) == {"body": no_fm})

    # Empty string
    check("empty string → empty dict", from_codex("") == {})

    # Streaming round-trip
    stream_docs = [
        {"id": 1, "body": "doc one"},
        {"id": 2, "tags": ["a", "b"]},
        {"id": 3, "body": "doc three\nwith newline"},
    ]
    codex_blob = "\n---\n".join(to_codex(d) for d in stream_docs)
    recovered = list(codex_to_json_stream(io.StringIO(codex_blob)))
    norm_expected = [norm(d) for d in stream_docs]
    norm_got = [norm(d) for d in recovered]
    check(
        "streaming round-trip",
        norm_expected == norm_got,
        f"\n  expected: {norm_expected}\n  got:      {norm_got}",
    )

    # json_to_codex_stream
    codex_strs = list(json_to_codex_stream(iter(stream_docs)))
    check("json_to_codex_stream yields correct count", len(codex_strs) == 3)

    # register_codec
    codec = register_codec()
    check("register_codec keys", set(codec.keys()) == {"content_type", "encode", "decode"})
    check("register_codec content_type", codec["content_type"] == "application/x-codex")
    check("register_codec encode/decode", codec["decode"](codec["encode"]({"x": 1})) == {"x": 1})

    # ------------------------------------------------------------------ #
    print(f"\n{'=' * 40}")
    print(f"Results: {passed} passed, {failed} failed")
    return failed == 0


# ---------------------------------------------------------------------------
# CLI entrypoint
# ---------------------------------------------------------------------------

def _cli() -> None:
    if len(sys.argv) < 2:
        print("Usage:", file=sys.stderr)
        print("  python3 codex_codec.py encode < input.json", file=sys.stderr)
        print("  python3 codex_codec.py decode < input.codex", file=sys.stderr)
        print("  python3 codex_codec.py test", file=sys.stderr)
        sys.exit(1)

    cmd = sys.argv[1].lower()

    if cmd == "encode":
        data = json.load(sys.stdin)
        if isinstance(data, list):
            first = True
            for item in data:
                if not first:
                    sys.stdout.write("\n---\n")
                sys.stdout.write(to_codex(item))
                first = False
        else:
            sys.stdout.write(to_codex(data))

    elif cmd == "decode":
        import io
        raw = sys.stdin.read()
        docs = list(codex_to_json_stream(io.StringIO(raw)))
        if len(docs) == 1:
            json.dump(docs[0], sys.stdout, ensure_ascii=False, indent=2)
        else:
            json.dump(docs, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")

    elif cmd == "test":
        ok = _run_tests()
        sys.exit(0 if ok else 1)

    else:
        print(f"Unknown command: {cmd}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    _cli()
