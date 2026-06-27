#!/bin/bash
cd "$(dirname "$0")"
PYTHONWARNINGS="ignore" python3 main.py 2>/dev/null
