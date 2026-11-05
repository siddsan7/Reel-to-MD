"""Live negative test: oversized synthetic evidence must fail, never be truncated."""
import json
from pathlib import Path
import time
from urllib.error import HTTPError
from urllib.request import ProxyHandler, Request, build_opener
import uuid

from reel_to_md.providers import OllamaModel, ollama_root
from reel_to_md.storage import read_json, write_json

ROOT = Path(__file__).resolve().parents[1]

if __name__ == "__main__":
    config = read_json(ROOT / "data/private/local-config.json")
    directory = ROOT / "outputs/context-overflow" / uuid.uuid4().hex
    model = OllamaModel(config["endpoint"], config["text_model"], config["text_revision"], directory, context_tokens=2048, output_tokens=128)
    started = time.monotonic()
    result = {"synthetic": True, "passed": False}
    try:
        model.complete([{"role": "user", "content": "This is synthetic evidence. " * 3000}], "oversized")
    except HTTPError as exc:
        body = exc.read(4096).decode(errors="replace")
        result.update({"status": exc.code, "error": body, "passed": "context" in body.lower() and exc.code in {400, 413, 500}})
    finally:
        # A rejected prompt may leave the weights loaded. Release this test's model.
        opener = build_opener(ProxyHandler({}))
        request = Request(ollama_root(config["endpoint"]) + "/api/generate", data=json.dumps({"model": config["text_model"], "keep_alive": 0}).encode(), headers={"Content-Type": "application/json"})
        with opener.open(request, timeout=30) as response:
            response.read()
        result["seconds"] = round(time.monotonic() - started, 3)
        write_json(ROOT / "outputs/context-overflow-check.json", result)
        print(json.dumps(result))
    if not result["passed"]:
        raise SystemExit(1)
