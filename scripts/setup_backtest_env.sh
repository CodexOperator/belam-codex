#!/bin/bash
set -euo pipefail
# D4: S1 Environment Setup — VectorBT + NautilusTrader backtesting stack
# ARM64 (aarch64) compatible. Uses --break-system-packages for consistency
# with existing torch/snntorch/scipy system-wide install.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WORKSPACE_DIR="$(dirname "$SCRIPT_DIR")"

echo "=== S1: Backtesting Environment Setup ==="
echo "  Python: $(python3 --version)"
echo "  Arch:   $(uname -m)"
echo ""

# ── Step 1: Install lightweight deps first ──
echo "1. Installing core dependencies (polars, duckdb, fracdiff, arch, skfolio)..."
for pkg in polars duckdb fracdiff arch skfolio; do
    echo -n "   $pkg... "
    if pip3 install "$pkg" --break-system-packages --quiet 2>/dev/null; then
        echo "OK"
    else
        echo "FAILED"
    fi
done

# ── Step 2: NautilusTrader (may need Rust toolchain on ARM64) ──
echo ""
echo "2. Installing NautilusTrader..."
if pip3 install nautilus-trader --break-system-packages --quiet 2>/dev/null; then
    echo "   nautilus_trader... OK (pip wheel)"
else
    echo "   pip wheel not available. Attempting source build with Rust..."
    if ! command -v rustc &>/dev/null; then
        echo "   Installing Rust toolchain..."
        curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
        # shellcheck disable=SC1091
        source "$HOME/.cargo/env"
    fi
    if pip3 install nautilus-trader --break-system-packages --no-binary nautilus-trader 2>&1 | tail -3; then
        echo "   nautilus_trader... OK (source build)"
    else
        echo "   ⚠️  NautilusTrader installation failed. May need manual intervention."
    fi
fi

# ── Step 3: VectorBT (PRO if available, OSS fallback) ──
echo ""
echo "3. Installing VectorBT..."
if pip3 install vectorbtpro --break-system-packages --quiet 2>/dev/null; then
    echo "   vectorbtpro... OK"
else
    echo "   VectorBT PRO not available (license required). Installing OSS fallback..."
    if pip3 install vectorbt --break-system-packages --quiet 2>/dev/null; then
        echo "   vectorbt (OSS)... OK"
    else
        echo "   ⚠️  vectorbt installation failed."
    fi
fi

# ── Step 4: Create directory structure ──
echo ""
echo "4. Creating directory structure..."
BASE="$WORKSPACE_DIR/machinelearning/snn_applied_finance/backtesting"
for dir in "" data strategies validation costs utils; do
    mkdir -p "$BASE/$dir"
    touch "$BASE/$dir/__init__.py"
done
echo "   backtesting/ tree created"

# ── Step 5: Write pinned requirements from actual installed versions ──
echo ""
echo "5. Recording installed versions..."
python3 -c "
import sys
pkgs = ['vectorbt', 'nautilus_trader', 'polars', 'duckdb', 'fracdiff', 'arch', 'skfolio', 'numba']
for name in pkgs:
    try:
        mod = __import__(name)
        ver = getattr(mod, '__version__', 'unknown')
        print(f'  {name}=={ver}')
    except ImportError:
        print(f'  {name}: NOT INSTALLED', file=sys.stderr)
"

# ── Step 6: Run smoke tests ──
echo ""
echo "6. Running smoke tests..."
cd "$WORKSPACE_DIR"
if python3 -m pytest tests/test_backtest_env.py -v --tb=short 2>&1; then
    echo ""
    echo "✅ S1 Environment Setup Complete"
else
    echo ""
    echo "⚠️  Some smoke tests failed. Review output above."
    exit 1
fi
