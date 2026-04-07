#!/usr/bin/env bash
# format.sh — Claude Code PostToolUse hook
# Auto-formats Python files after Write/Edit/MultiEdit tool calls

LOG=".claude/hooks/format.log"

# Read full JSON from stdin
INPUT=$(cat)

# Extract tool_name
TOOL_NAME=$(python3 -c "
import json, sys
try:
    d = json.loads(sys.stdin.read())
    print(d.get('tool_name', ''))
except:
    print('')
" <<< "$INPUT" 2>/dev/null)

# Only act on Write, Edit, MultiEdit
if [[ "$TOOL_NAME" != "Write" && "$TOOL_NAME" != "Edit" && "$TOOL_NAME" != "MultiEdit" ]]; then
    exit 0
fi

# Extract file_path
FILE_PATH=$(python3 -c "
import json, sys
try:
    d = json.loads(sys.stdin.read())
    print(d.get('tool_input', {}).get('file_path', ''))
except:
    print('')
" <<< "$INPUT" 2>/dev/null)

# Nothing to format
if [[ -z "$FILE_PATH" || ! -f "$FILE_PATH" ]]; then
    exit 0
fi

# Determine extension
EXT="${FILE_PATH##*.}"

# Only format supported extensions
case "$EXT" in
    py)
        ;;
    *)
        exit 0
        ;;
esac

# Check if ruff is available
if ! command -v ruff >/dev/null 2>&1; then
    exit 0
fi

# Run ruff format — silent on stdout, log result
if ruff format "$FILE_PATH" >/dev/null 2>&1; then
    TS=$(date -u '+%Y-%m-%dT%H:%M:%SZ')
    echo "${TS} formatted: ${FILE_PATH}" >> "$LOG" 2>/dev/null
fi

# Run ruff check with autofix
ruff check --fix "$FILE_PATH" >/dev/null 2>&1

# Always exit 0 — formatting is best-effort, never block
exit 0
