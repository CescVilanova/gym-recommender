#!/bin/bash
# Dependencies are installed at runtime by the routine.
# This script intentionally exits successfully.
pip install reportlab --break-system-packages -q 2>/dev/null || true
