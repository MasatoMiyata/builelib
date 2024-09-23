#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

INPUT_FILENAME="input_zebopt.json"
OUTPUT_FILENAME_BASE="zebopt"

python3 "$SCRIPT_DIR/generate_input_zebopt.py" "$INPUT_FILENAME"
echo "Generated file: $INPUT_FILENAME"

python3 "$SCRIPT_DIR/../builelib_zebopt_run.py" "$INPUT_FILENAME" "$OUTPUT_FILENAME_BASE"

echo "Successfully ran builelib_zebopt_run.py with $INPUT_FILENAME" "$OUTPUT_FILENAME_BASE"
