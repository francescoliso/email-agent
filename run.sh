#!/bin/bash
cd "$(dirname "$0")"
PYTHONWARNINGS="ignore" python3 -u main.py 2>/dev/null
