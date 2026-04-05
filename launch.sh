#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════
# launch.sh — Quick launch script for the YakSperm Analyzer HMI
# ═══════════════════════════════════════════════════════════════════════════
# Usage:
#   ./launch.sh              # Normal mode   (Jetson Nano + ESP32 UART)
#   ./launch.sh --mock       # Mock mode     (no hardware required)
#   ./launch.sh --pc         # PC mode       (real HW, auto-detect serial)
#   ./launch.sh --fullscreen # Fullscreen    (Jetson kiosk mode)
#   ./launch.sh --pc -v      # PC + verbose logging
# ═══════════════════════════════════════════════════════════════════════════

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Activate virtual environment if present
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
    echo "✓ Virtual environment activated"
fi

# Check Python version
PYTHON=${PYTHON:-python3}
if ! command -v "$PYTHON" &> /dev/null; then
    echo "❌ Python3 not found. Install Python 3.10+"
    exit 1
fi

echo "═══════════════════════════════════════════"
echo "  🔬 YakSperm Analyzer HMI v3.0"
echo "  Python: $($PYTHON --version)"
echo "  Args:   $*"
echo "═══════════════════════════════════════════"

# Set Qt platform if running headless / on Jetson
export QT_QPA_PLATFORM="${QT_QPA_PLATFORM:-xcb}"

exec "$PYTHON" main.py "$@"
