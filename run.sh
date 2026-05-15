#!/bin/sh
# Make sure we're in the right directory
cd "$(dirname "$0")"
exec venv/bin/python3 chatbot/main.py "$@"
