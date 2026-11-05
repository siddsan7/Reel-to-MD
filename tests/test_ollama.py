import json

import pytest

from reel_to_md.pipeline import Config
from reel_to_md.providers import OllamaModel

DIGEST = "a" * 64


class Response:
    def __init__(self, value):
        self.value = value
    def __enter__(self):
        return self
    def __exit__(self, *args):
        pass
    def read(self, size):
        return json.dumps(self.value).encode()[:size]


def server(monkeypatch, digest=DIGEST, size=2_000_000, remote=False):
    calls = []
    class Opener:
        def open(self, request, timeout):
            calls.append(request)
            if request.full_url.endswith("/api/tags"):
                return Response({"models": [{"name": "local:4b", "digest": digest, "size": size, "remote_host": "external" if remote else None}]})
            return Response({"message": {"role": "assistant", "content": '{"text":"source only"}'}, "done": True, "done_reason": "stop", "prompt_eval_count": 100, "eval_count": 8})
    monkeypatch.setattr("reel_to_md.providers.build_opener", lambda *args: Opener())
    return calls


@pytest.mark.parametrize("endpoint", ["http://127.0.0.1:11434", "http://127.0.0.1:11434/", "http://127.0.0.1:11434/v1", "http://[::1]:11434/v1/"])
def test_native_endpoint_normalization(endpoint, tmp_path):
    model = OllamaModel(endpoint, "local:4b", DIGEST, tmp_path)
    assert model.url.endswith(":11434/api/chat")


@pytest.mark.parametrize("revision", [DIGEST, "sha256:" + DIGEST])
def test_native_schema_images_usage_and_unload(monkeypatch, tmp_path, revision):
    calls = server(monkeypatch)
    model = OllamaModel("http://127.0.0.1:11434/v1", "local:4b", revision, tmp_path)
    schema = {"type": "object", "properties": {"text": {"type": "string"}}}
    text, usage = model.complete([{"role": "user", "content": [{"type": "text", "text": "Describe"}, {"type": "image_url", "image_url": {"url": "data:image/png;base64,YWJj"}}]}], "call", structured=schema)
    body = json.loads(calls[-1].data)
    assert body["format"] == schema and body["messages"][0]["images"] == ["YWJj"]
    assert body["keep_alive"] == 0 and body["think"] is False and "tools" not in body
    assert body["truncate"] is False and body["shift"] is False
    assert body["options"]["num_ctx"] == 8192
    assert usage["input_tokens"] == 100 and json.loads(text)["text"] == "source only"
    model.complete([], "call")
    assert len(calls) == 2  # inventory + inference; cache hit needs neither


@pytest.mark.parametrize("options", [{"digest": "b" * 64}, {"size": 0}, {"remote": True}])
def test_changed_or_remote_model_rejected_before_dispatch(monkeypatch, tmp_path, options):
    calls = server(monkeypatch, **options)
    model = OllamaModel("http://127.0.0.1:11434/v1", "local:4b", DIGEST, tmp_path)
    with pytest.raises(ValueError, match="missing_changed_or_remote"):
        model.complete([], "call")
    assert len(calls) == 1 and not (tmp_path / "call.pending").exists()


def test_unpinned_cloud_model_and_remote_images_blocked(tmp_path):
    with pytest.raises(ValueError):
        OllamaModel("http://127.0.0.1:11434", "local:4b", "mutable-tag", tmp_path)
    with pytest.raises(ValueError):
        OllamaModel("http://127.0.0.1:11434", "local:4b-cloud", DIGEST, tmp_path)
    model = OllamaModel("http://127.0.0.1:11434", "local:4b", DIGEST, tmp_path)
    with pytest.raises(ValueError):
        model._payload([{"role": "user", "content": [{"type": "image_url", "image_url": {"url": "https://outside/image.png"}}]}], False)


@pytest.mark.parametrize("kwargs", [{"model_backend": "unknown"}, {"context_tokens": 1}, {"output_tokens": 50000}, {"model_timeout_seconds": 0}, {"input_kind": "audit_reference"}])
def test_config_limits(kwargs):
    with pytest.raises(ValueError):
        Config(**kwargs).validate()


def test_ollama_runtime_version_changes_identity(monkeypatch):
    from reel_to_md.pipeline import versions
    from reel_to_md.storage import digest
    monkeypatch.setattr("reel_to_md.pipeline.media.tool_version", lambda name: "test")
    monkeypatch.setattr("reel_to_md.pipeline.ollama_runtime_version", lambda endpoint: "0.40.3")
    first = versions(Config(model_backend="ollama", endpoint="http://127.0.0.1:11434"))
    monkeypatch.setattr("reel_to_md.pipeline.ollama_runtime_version", lambda endpoint: "0.40.4")
    second = versions(Config(model_backend="ollama", endpoint="http://127.0.0.1:11434"))
    assert first["ollama"] == "0.40.3" and digest(first) != digest(second)


@pytest.mark.parametrize("threads", [0, 65, True, 1.5, "8"])
def test_invalid_thread_limits_rejected(tmp_path, threads):
    with pytest.raises(ValueError, match="threads_invalid"):
        Config(model_backend="ollama", ollama_threads=threads).validate()
    with pytest.raises(ValueError, match="threads_invalid"):
        OllamaModel("http://127.0.0.1:11434", "local:4b", DIGEST, tmp_path, threads=threads)


def test_explicit_thread_limit_reaches_inference(monkeypatch, tmp_path):
    calls = server(monkeypatch)
    model = OllamaModel("http://127.0.0.1:11434", "local:4b", DIGEST, tmp_path, threads=8)
    model.complete([], "thread-limited")
    assert json.loads(calls[-1].data)["options"]["num_thread"] == 8
    Config(model_backend="ollama", ollama_threads=8).validate()
    with pytest.raises(ValueError, match="threads_invalid"):
        Config(ollama_threads=8).validate()


def test_explicit_long_cpu_deadline_is_bounded_and_reaches_request(monkeypatch, tmp_path):
    requests = []
    class Opener:
        def open(self, request, timeout):
            if request.full_url.endswith('/api/tags'):
                return Response({'models':[{'name':'local:4b','digest':DIGEST,'size':2_000_000}]})
            requests.append(timeout)
            return Response({'message':{'content':'draft'},'done':True,'done_reason':'stop','prompt_eval_count':1,'eval_count':1})
    monkeypatch.setattr('reel_to_md.providers.build_opener',lambda *args:Opener())
    Config(model_backend='ollama',model_timeout_seconds=1200).validate()
    model=OllamaModel('http://127.0.0.1:11434','local:4b',DIGEST,tmp_path,timeout_seconds=1200)
    model.complete([], 'long-cpu')
    assert requests==[1200]
    assert Config().model_timeout_seconds==300
    assert OllamaModel('http://127.0.0.1:11434','local:4b',DIGEST,tmp_path).timeout_seconds==300
    for invalid in (0,1201):
        with pytest.raises(ValueError):
            Config(model_timeout_seconds=invalid).validate()
        with pytest.raises(ValueError):
            OllamaModel('http://127.0.0.1:11434','local:4b',DIGEST,tmp_path,timeout_seconds=invalid)
