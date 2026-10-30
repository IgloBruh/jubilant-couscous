#!/bin/sh
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHONPATH="$SCRIPT_DIR/src" exec python3 -m depviz "$@"
