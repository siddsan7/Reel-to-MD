"""Explicit, pinned, public model download. Inference itself remains offline."""
from pathlib import Path

from huggingface_hub import snapshot_download

REPOSITORY = "Systran/faster-whisper-small.en"
REVISION = "d1d751a5f8271d482d14ca55d9e2deeebbae577f"

if __name__ == "__main__":
    directory = Path(__file__).resolve().parents[1] / "models" / "whisper-small.en"
    snapshot_download(
        REPOSITORY,
        revision=REVISION,
        local_dir=directory,
        cache_dir=directory.parent / "hf-cache",
        allow_patterns=["config.json", "model.bin", "tokenizer.json", "vocabulary.txt"],
        max_workers=2,
    )
    print(f"Whisper small.en revision {REVISION}: {directory}")
