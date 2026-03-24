#!/usr/bin/env python3
"""D5: Demo Tic-Tac-Toe — proves the full WorldState loop.

Two simulated agents play tic-tac-toe via shared world state.
Demonstrates: init → read diff → write move → check win → advance turn.

Self-contained: runs both "agents" in a loop, printing the board after each move.
No real agent sessions needed — just proves the API loop.

Usage:
    python3 scripts/demo_tictactoe.py              # Run a demo game
    python3 scripts/demo_tictactoe.py --db /tmp/test.db  # Use custom DB
"""

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from world_api import WorldState


NAMESPACE = 'game:tictactoe'
PLAYER_X = 'player_x'
PLAYER_O = 'player_o'


def setup_game(ws: WorldState) -> None:
    """Initialize a tic-tac-toe board in world state."""
    empty_board = json.dumps([['', '', ''], ['', '', ''], ['', '', '']])
    ws.set('board', 'cells', empty_board, agent_id='system')
    ws.set('game', 'turn', 'X', agent_id='system')
    ws.set('game', 'status', 'in_progress', agent_id='system')
    ws.set('game', 'move_count', '0', agent_id='system')


def get_board(ws: WorldState) -> list[list[str]]:
    """Get current board state."""
    cells = ws.get('board', 'cells')
    return json.loads(cells) if cells else [['', '', ''], ['', '', ''], ['', '', '']]


def check_winner(board: list[list[str]]) -> str:
    """Check for winner. Returns 'X', 'O', or ''."""
    # Rows
    for row in board:
        if row[0] and row[0] == row[1] == row[2]:
            return row[0]
    # Columns
    for c in range(3):
        if board[0][c] and board[0][c] == board[1][c] == board[2][c]:
            return board[0][c]
    # Diagonals
    if board[0][0] and board[0][0] == board[1][1] == board[2][2]:
        return board[0][0]
    if board[0][2] and board[0][2] == board[1][1] == board[2][0]:
        return board[0][2]
    return ''


def make_move(ws: WorldState, agent_id: str, row: int, col: int) -> str:
    """Agent makes a move. Validates turn and board state.

    Returns a status message.
    """
    turn = ws.get('game', 'turn')
    status = ws.get('game', 'status')

    if status != 'in_progress':
        return f"Game is over: {status}"

    symbol = 'X' if agent_id == PLAYER_X else 'O'
    if turn != symbol:
        return f"Not your turn (current: {turn})"

    board = get_board(ws)
    if board[row][col]:
        return f"Cell ({row},{col}) already occupied by {board[row][col]}"

    board[row][col] = symbol
    ws.set('board', 'cells', json.dumps(board), agent_id=agent_id)

    move_count = int(ws.get('game', 'move_count') or '0') + 1
    ws.set('game', 'move_count', str(move_count), agent_id='system')

    # Check win/draw
    winner = check_winner(board)
    if winner:
        ws.set('game', 'status', f'won:{winner}', agent_id='system')
        return f"🏆 {winner} wins!"
    elif move_count >= 9:
        ws.set('game', 'status', 'draw', agent_id='system')
        return "🤝 Draw!"
    else:
        next_turn = 'O' if symbol == 'X' else 'X'
        ws.set('game', 'turn', next_turn, agent_id='system')
        return f"Placed {symbol} at ({row},{col})"


def render_board(board: list[list[str]]) -> str:
    """Render board as ASCII art."""
    lines = []
    for i, row in enumerate(board):
        cells = [c if c else '.' for c in row]
        lines.append(f"  {cells[0]} | {cells[1]} | {cells[2]}")
        if i < 2:
            lines.append('  --+---+--')
    return '\n'.join(lines)


def run_demo(db_path: Path = None):
    """Run a demo game with scripted moves."""
    if db_path is None:
        db_path = Path(tempfile.mktemp(suffix='.db'))
        cleanup = True
    else:
        cleanup = False

    ws = WorldState(db_path=db_path, namespace=NAMESPACE)
    ws.initialize()

    print("🎮 Tic-Tac-Toe Demo — World State API")
    print("=" * 40)

    setup_game(ws)
    print("\nBoard initialized:")
    print(render_board(get_board(ws)))

    # Scripted moves that result in X winning
    moves = [
        (PLAYER_X, 1, 1),  # X center
        (PLAYER_O, 0, 0),  # O top-left
        (PLAYER_X, 0, 2),  # X top-right
        (PLAYER_O, 2, 0),  # O bottom-left
        (PLAYER_X, 2, 2),  # X bottom-right (threatens diagonal)
        (PLAYER_O, 0, 1),  # O top-middle
        (PLAYER_X, 1, 0),  # X middle-left (threatens row)
        # At this point X should have won via diagonal if moves were different
        # Let's adjust: X goes for the 0,0-1,1-2,2 diagonal
    ]

    # Actually use a cleaner sequence: X wins via middle row
    moves = [
        (PLAYER_X, 1, 0),  # X
        (PLAYER_O, 0, 0),  # O
        (PLAYER_X, 1, 1),  # X
        (PLAYER_O, 0, 1),  # O
        (PLAYER_X, 1, 2),  # X wins (middle row)
    ]

    for i, (agent, row, col) in enumerate(moves):
        symbol = 'X' if agent == PLAYER_X else 'O'
        print(f"\n--- Move {i+1}: {symbol} plays ({row},{col}) ---")

        # Show diff for this agent (what they'd see)
        diff = ws.get_diff(agent)
        if diff:
            print(f"  [Diff] {diff.split(chr(10))[0]}")  # First line only
        ws.advance_cursor(agent)

        result = make_move(ws, agent, row, col)
        print(f"  Result: {result}")
        print(render_board(get_board(ws)))

    # Final state
    print(f"\n{'=' * 40}")
    print(f"Game status: {ws.get('game', 'status')}")
    events = ws.get_events_since('spectator')
    print(f"Total events: {len(events)}")

    ws.close()
    if cleanup:
        db_path.unlink(missing_ok=True)

    return True


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Tic-Tac-Toe Demo — WorldState API')
    parser.add_argument('--db', type=Path, help='Custom DB path')
    args = parser.parse_args()

    run_demo(args.db)
