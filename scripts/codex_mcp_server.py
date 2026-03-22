#!/usr/bin/env python3
"""
codex_mcp_server.py — MCP-native Codex Server (V3).

Serves codex primitives over Model Context Protocol (MCP) via stdio
JSON-RPC transport. External clients (Cursor, Claude Desktop, etc.) can
request primitives, render supermaps, and execute engine operations.

Transport: stdio (JSON-RPC 2.0 over stdin/stdout)

Configuration (for MCP clients):
{
  "mcpServers": {
    "codex": {
      "command": "python3",
      "args": ["/home/ubuntu/.openclaw/workspace/scripts/codex_mcp_server.py"],
      "env": {
        "BELAM_WORKSPACE": "/home/ubuntu/.openclaw/workspace"
      }
    }
  }
}
"""

import io
import json
import os
import re
import sys
from pathlib import Path

# ── Lazy imports from codex_engine and codex_codec ──────────────────────────────

_engine = None
_codec = None


def _get_engine():
    """Lazy import codex_engine."""
    global _engine
    if _engine is None:
        sys.path.insert(0, str(Path(__file__).parent))
        import codex_engine
        _engine = codex_engine
    return _engine


def _get_codec():
    """Lazy import codex_codec."""
    global _codec
    if _codec is None:
        sys.path.insert(0, str(Path(__file__).parent))
        import codex_codec
        _codec = codex_codec
    return _codec


# ── JSON-RPC I/O ───────────────────────────────────────────────────────────────

def read_jsonrpc(stream):
    """Read a JSON-RPC message from stdin.

    Supports two modes:
    - Content-Length framing (LSP-style): headers followed by content
    - Line-delimited JSON: one JSON object per line
    """
    # Try to read a line
    line = stream.readline()
    if not line:
        return None

    line = line.strip()
    if not line:
        return None

    # Check for Content-Length header (LSP-style)
    if line.lower().startswith('content-length:'):
        content_length = int(line.split(':', 1)[1].strip())
        # Read until empty line (end of headers)
        while True:
            header = stream.readline().strip()
            if not header:
                break
        # Read exact content bytes
        content = stream.read(content_length)
        return json.loads(content)

    # Otherwise treat as line-delimited JSON
    try:
        return json.loads(line)
    except json.JSONDecodeError:
        return None


def write_jsonrpc(stream, response):
    """Write a JSON-RPC response to stdout with Content-Length framing."""
    body = json.dumps(response, ensure_ascii=False, default=str)
    header = f"Content-Length: {len(body.encode('utf-8'))}\r\n\r\n"
    stream.write(header)
    stream.write(body)
    stream.flush()


def _jsonrpc_error(req_id, code, message):
    """Build a JSON-RPC error response."""
    return {
        'jsonrpc': '2.0',
        'id': req_id,
        'error': {'code': code, 'message': message},
    }


def _jsonrpc_result(req_id, result):
    """Build a JSON-RPC success response."""
    return {
        'jsonrpc': '2.0',
        'id': req_id,
        'result': result,
    }


# ── MCP Server ─────────────────────────────────────────────────────────────────

class CodexMCPServer:
    """MCP server serving codex primitives and engine operations."""

    MCP_PROTOCOL_VERSION = '2024-11-05'

    def __init__(self, workspace):
        self.workspace = Path(workspace)
        self._engine = None
        self._codec = None
        # Per-session R-label tracking for diff capability
        self._tracker = None
        self._read_coords = {}  # coord → last hash for diff tracking

    @property
    def engine(self):
        if self._engine is None:
            self._engine = _get_engine()
        return self._engine

    @property
    def codec(self):
        if self._codec is None:
            self._codec = _get_codec()
        return self._codec

    @property
    def tracker(self):
        if self._tracker is None:
            self._tracker = self.engine.RenderTracker(
                state_file=self.workspace / 'state' / 'mcp_render_state.json'
            )
        return self._tracker

    def handle_initialize(self, params):
        """Handle MCP initialize request."""
        return {
            'protocolVersion': self.MCP_PROTOCOL_VERSION,
            'capabilities': {
                'resources': {
                    'subscribe': False,
                    'listChanged': False,
                },
                'tools': {},
            },
            'serverInfo': {
                'name': 'codex',
                'version': '3.0.0',
            },
        }

    def handle_resources_list(self):
        """List all primitives as MCP resources."""
        resources = []
        for prefix in self.engine.SHOW_ORDER:
            if prefix not in self.engine.NAMESPACE:
                continue
            type_label = self.engine.NAMESPACE[prefix][0]
            try:
                prims = self.engine.get_primitives(prefix, active_only=True)
            except Exception:
                continue

            for i, (slug, fp) in enumerate(prims, 1):
                coord = f"{prefix}{i}"
                uri = f"codex://workspace/{coord}"
                resources.append({
                    'uri': uri,
                    'name': f"{coord} — {slug}",
                    'description': f"{type_label}: {slug}",
                    'mimeType': 'application/x-codex',
                })

        # Add supermap as a special resource
        resources.append({
            'uri': 'codex://workspace/supermap',
            'name': 'Supermap',
            'description': 'Full workspace supermap view',
            'mimeType': 'text/plain',
        })

        # Add memory as a special resource
        resources.append({
            'uri': 'codex://workspace/m',
            'name': 'Memory (today)',
            'description': "Today's memory entries",
            'mimeType': 'text/plain',
        })

        return {'resources': resources}

    def handle_resources_read(self, uri):
        """Read a primitive by URI, return codex-formatted content."""
        coord = self._parse_uri(uri)
        if coord is None:
            raise ValueError(f"Invalid URI: {uri}")

        # Special: supermap
        if coord == 'supermap':
            content = self.engine.render_supermap()
            return {
                'contents': [{
                    'uri': uri,
                    'mimeType': 'text/plain',
                    'text': content,
                }]
            }

        # Resolve coordinate
        try:
            resolved, _ = self.engine.resolve_coords([coord])
        except Exception as e:
            raise ValueError(f"Cannot resolve coordinate '{coord}': {e}")

        if not resolved:
            raise ValueError(f"Coordinate '{coord}' not found")

        contents = []
        for r in resolved:
            prim = self.engine.load_primitive(r['filepath'], r['type'])
            if prim:
                # Build dict for codec
                prim_dict = {'primitive': r['type']}
                for idx, fi in prim['fields'].items():
                    prim_dict[fi['key']] = fi['value']
                if prim.get('body'):
                    prim_dict['body'] = '\n'.join(prim['body'])

                codex_text = self.codec.to_codex(prim_dict)
                contents.append({
                    'uri': uri,
                    'mimeType': 'application/x-codex',
                    'text': codex_text,
                })

        return {'contents': contents}

    def handle_tools_list(self):
        """List available codex tools."""
        return {'tools': [
            {
                'name': 'codex_navigate',
                'description': 'Resolve and render any coordinate (e.g., t1, p3, d5)',
                'inputSchema': {
                    'type': 'object',
                    'properties': {
                        'coord': {'type': 'string', 'description': 'Coordinate to navigate to'},
                    },
                    'required': ['coord'],
                },
            },
            {
                'name': 'codex_edit',
                'description': 'Edit a primitive field (e1 equivalent)',
                'inputSchema': {
                    'type': 'object',
                    'properties': {
                        'coord': {'type': 'string', 'description': 'Coordinate to edit (e.g., t1)'},
                        'field': {'type': 'integer', 'description': 'Field number to edit'},
                        'value': {'type': 'string', 'description': 'New field value'},
                    },
                    'required': ['coord', 'field', 'value'],
                },
            },
            {
                'name': 'codex_create',
                'description': 'Create a new primitive (e2 equivalent)',
                'inputSchema': {
                    'type': 'object',
                    'properties': {
                        'type': {'type': 'string', 'description': 'Primitive type prefix (t, d, l, etc.)'},
                        'title': {'type': 'string', 'description': 'Title for the new primitive'},
                    },
                    'required': ['type', 'title'],
                },
            },
            {
                'name': 'codex_graph',
                'description': 'Render dependency graph for a coordinate',
                'inputSchema': {
                    'type': 'object',
                    'properties': {
                        'coord': {'type': 'string', 'description': 'Coordinate to graph'},
                        'depth': {'type': 'integer', 'description': 'Graph depth (default 1)', 'default': 1},
                    },
                    'required': ['coord'],
                },
            },
            {
                'name': 'codex_supermap',
                'description': 'Render the full workspace supermap',
                'inputSchema': {
                    'type': 'object',
                    'properties': {
                        'persona': {'type': 'string', 'description': 'Optional persona filter (architect, builder, critic)'},
                        'tag': {'type': 'string', 'description': 'Optional tag filter'},
                    },
                    'required': [],
                },
            },
        ]}

    def handle_tools_call(self, name, arguments):
        """Execute a codex tool and return result."""
        if name == 'codex_navigate':
            coord = arguments.get('coord', '')
            output = self.engine.render_zoom([coord])
            return {
                'content': [{'type': 'text', 'text': output}],
            }

        elif name == 'codex_edit':
            coord = arguments.get('coord', '')
            field = arguments.get('field', 1)
            value = arguments.get('value', '')
            # Capture stdout from execute_edit
            old_stdout = sys.stdout
            sys.stdout = io.StringIO()
            try:
                rc = self.engine.execute_edit([coord, str(field), value])
                output = sys.stdout.getvalue()
            finally:
                sys.stdout = old_stdout
            return {
                'content': [{'type': 'text', 'text': output.strip()}],
                'isError': rc != 0,
            }

        elif name == 'codex_create':
            ptype = arguments.get('type', '')
            title = arguments.get('title', '')
            old_stdout = sys.stdout
            sys.stdout = io.StringIO()
            try:
                rc = self.engine.execute_create([ptype, title])
                output = sys.stdout.getvalue()
            finally:
                sys.stdout = old_stdout
            return {
                'content': [{'type': 'text', 'text': output.strip()}],
                'isError': rc != 0,
            }

        elif name == 'codex_graph':
            coord = arguments.get('coord', '')
            depth = arguments.get('depth', 1)
            graph_args = [coord]
            if depth and depth > 1:
                graph_args.extend(['--depth', str(depth)])
            output = self.engine.render_graph(graph_args)
            return {
                'content': [{'type': 'text', 'text': output}],
            }

        elif name == 'codex_supermap':
            persona = arguments.get('persona')
            tag = arguments.get('tag')
            output = self.engine.render_supermap(persona=persona, tag_filter=tag)
            return {
                'content': [{'type': 'text', 'text': output}],
            }

        else:
            return {
                'content': [{'type': 'text', 'text': f'Unknown tool: {name}'}],
                'isError': True,
            }

    def _parse_uri(self, uri):
        """Parse codex:// URI to coordinate string."""
        # codex://workspace/t1 → t1
        # codex://workspace/supermap → supermap
        m = re.match(r'^codex://workspace/(.+)$', uri)
        if m:
            return m.group(1)
        return None

    def _coord_to_uri(self, prefix, index, slug=None):
        """Build codex:// URI from coordinate parts."""
        return f"codex://workspace/{prefix}{index}"

    def dispatch(self, message):
        """Dispatch a JSON-RPC message and return response."""
        method = message.get('method', '')
        params = message.get('params', {})
        req_id = message.get('id')

        try:
            # MCP lifecycle
            if method == 'initialize':
                result = self.handle_initialize(params)
                return _jsonrpc_result(req_id, result)

            elif method == 'initialized':
                # Client acknowledgment — no response needed (notification)
                return None

            elif method == 'ping':
                return _jsonrpc_result(req_id, {})

            # Resources
            elif method == 'resources/list':
                result = self.handle_resources_list()
                return _jsonrpc_result(req_id, result)

            elif method == 'resources/read':
                uri = params.get('uri', '')
                result = self.handle_resources_read(uri)
                return _jsonrpc_result(req_id, result)

            # Tools
            elif method == 'tools/list':
                result = self.handle_tools_list()
                return _jsonrpc_result(req_id, result)

            elif method == 'tools/call':
                tool_name = params.get('name', '')
                arguments = params.get('arguments', {})
                result = self.handle_tools_call(tool_name, arguments)
                return _jsonrpc_result(req_id, result)

            else:
                return _jsonrpc_error(req_id, -32601, f'Method not found: {method}')

        except ValueError as e:
            return _jsonrpc_error(req_id, -32602, str(e))
        except Exception as e:
            return _jsonrpc_error(req_id, -32603, f'Internal error: {e}')


# ── Main loop ──────────────────────────────────────────────────────────────────

def main():
    """stdio transport loop — read JSON-RPC from stdin, write to stdout."""
    workspace = Path(os.environ.get('BELAM_WORKSPACE', Path.home() / '.openclaw' / 'workspace'))
    server = CodexMCPServer(workspace)

    # Redirect stderr for debug logging (don't pollute stdout)
    log_file = workspace / 'state' / 'mcp_server.log'
    log_file.parent.mkdir(parents=True, exist_ok=True)

    while True:
        try:
            message = read_jsonrpc(sys.stdin)
            if message is None:
                break  # EOF or empty — client disconnected

            response = server.dispatch(message)
            if response is not None:
                write_jsonrpc(sys.stdout, response)

        except KeyboardInterrupt:
            break
        except Exception as e:
            # Log errors but don't crash the server
            try:
                with open(log_file, 'a') as f:
                    f.write(f"Error: {e}\n")
            except Exception:
                pass


if __name__ == '__main__':
    main()
