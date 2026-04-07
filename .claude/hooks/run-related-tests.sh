#!/usr/bin/env bash
# run-related-tests.sh — Claude Code PostToolUse hook (async)
# Corre los tests relacionados al archivo editado

LOG=".claude/hooks/tests.log"

# Leer JSON desde stdin
INPUT=$(cat)

# Extraer file_path
FILE_PATH=$(python3 -c "
import json, sys
try:
    d = json.loads(sys.stdin.read())
    print(d.get('tool_input', {}).get('file_path', ''))
except:
    print('')
" <<< "$INPUT" 2>/dev/null)

if [ -z "$FILE_PATH" ]; then
    exit 0
fi

# Determinar qué test correr según el directorio del archivo
TEST_FILE=""

case "$FILE_PATH" in
    */tests/*)
        # Se está editando un test directamente — correrlo
        TEST_FILE="$FILE_PATH"
        ;;
    */agents/*)
        TEST_FILE="tests/test_agents.py"
        ;;
    */models.py)
        TEST_FILE="tests/test_models.py"
        ;;
    */image_parser.py)
        TEST_FILE="tests/test_image_parser.py"
        ;;
    */main.py|*/api.py)
        TEST_FILE="tests/"
        ;;
    *)
        # No hay tests mapeados para este archivo
        exit 0
        ;;
esac

# Verificar que el test existe
if [ ! -e "$TEST_FILE" ]; then
    exit 0
fi

# Correr pytest — silencioso en stdout, log del resultado
TS=$(date -u '+%Y-%m-%dT%H:%M:%SZ')
if python3 -m pytest "$TEST_FILE" -q >/dev/null 2>&1; then
    echo "${TS} PASS: ${TEST_FILE} (trigger: ${FILE_PATH})" >> "$LOG" 2>/dev/null
else
    echo "${TS} FAIL: ${TEST_FILE} (trigger: ${FILE_PATH})" >> "$LOG" 2>/dev/null
fi

exit 0
