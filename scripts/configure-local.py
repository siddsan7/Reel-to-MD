"""Write ignored local config using the installed Ollama manifests, never cloud tags."""
import json
from pathlib import Path
from urllib.request import ProxyHandler, Request, build_opener

ROOT = Path(__file__).resolve().parents[1]
MODELS = {"vision": "qwen3-vl:4b-instruct", "text": "qwen3:4b-instruct-2507-q4_K_M"}

if __name__ == "__main__":
    opener = build_opener(ProxyHandler({}))
    with opener.open(Request("http://127.0.0.1:11434/api/tags"), timeout=10) as response:
        installed = {model["name"]: model for model in json.load(response)["models"]}
    config = {"asr_model": str(ROOT / "models/whisper-small.en"), "endpoint": "http://127.0.0.1:11434/v1", "model_backend": "ollama", "context_tokens": 8192, "output_tokens": 2048, "model_timeout_seconds": 300}
    for channel, name in MODELS.items():
        model = installed[name]
        if model.get("size", 0) < 1_000_000 or model.get("remote_host") or model.get("remote_model"):
            raise ValueError("Only installed local weights are supported")
        config[channel + "_model"] = name
        config[channel + "_revision"] = model["digest"]
    if not (ROOT / "models/whisper-small.en/model.bin").is_file():
        raise ValueError("Run download-whisper.py first")
    from reel_to_md.pipeline import Config
    from reel_to_md.storage import write_json
    Config(**config).validate()
    output = ROOT / "data/private/local-config.json"
    write_json(output, config)
    print(f"Local configuration: {output}")
    print(f"Local UI CPU configuration: {ui_output} (16K context, 8 threads, 1200-second call deadline)")
