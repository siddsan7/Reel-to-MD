"""Subprocess entry point: no model downloads, CPU only, parent enforces timeout."""
import json
import sys

from .media import transcribe

if __name__ == "__main__":
    print(json.dumps(transcribe(sys.argv[1], sys.argv[2]), allow_nan=False))
