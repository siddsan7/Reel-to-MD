import json
from pathlib import Path

import pytest

from reel_to_md.contracts import redact_text
from reel_to_md.media import ocr
from reel_to_md.providers import LocalModel, NoRedirect


class Response:
    def __init__(self, result):
        self.result = json.dumps(result).encode()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def read(self, size):
        return self.result[:size]


def fake_server(monkeypatch, content, finish="stop"):
    requests = []

    class Opener:
        def open(self, request, timeout):
            requests.append(json.loads(request.data))
            return Response({"choices": [{"message": {"content": content}, "finish_reason": finish}], "usage": {"prompt_tokens": 12, "completion_tokens": 6}})

    monkeypatch.setattr("reel_to_md.providers.build_opener", lambda *args: Opener())
    return requests


def test_structured_response_redaction_keeps_valid_json(tmp_path, monkeypatch):
    requests = fake_server(monkeypatch, json.dumps({"text": 'password="private-example"'}))
    measured = []
    model = LocalModel("http://127.0.0.1:8080/v1", "test", "v1", tmp_path, on_usage=measured.append)
    text, usage = model.complete([{"role": "user", "content": "data"}], "call", structured=True)
    assert "private-example" not in json.loads(text)["text"]
    assert usage["input_tokens"] == 12
    assert measured == [usage]
    assert "tools" not in requests[0]
    assert requests[0]["response_format"] == {"type": "json_object"}
    model.complete([], "call", structured=True)
    assert len(requests) == 1 and measured[-1]["cache_hit"]


def test_invalid_json_response_preserved_without_retry(tmp_path, monkeypatch):
    requests = fake_server(monkeypatch, 'bad JSON password="private-example"')
    measured = []
    model = LocalModel("http://127.0.0.1:8080/v1", "test", "v1", tmp_path, on_usage=measured.append)
    with pytest.raises(ValueError):
        model.complete([], "call", structured=True)
    assert len(measured) == 1
    assert "private-example" not in (tmp_path / "call.first-response.txt").read_text()
    with pytest.raises(FileExistsError):
        model.complete([], "call", structured=True)
    assert len(requests) == 1


def test_truncated_model_response_not_exported(tmp_path, monkeypatch):
    fake_server(monkeypatch, "incomplete", finish="length")
    model = LocalModel("http://127.0.0.1:8080/v1", "test", "v1", tmp_path)
    with pytest.raises(ValueError, match="incomplete"):
        model.complete([], "call")
    assert not (tmp_path / "call.json").exists()


def test_redirects_blocked():
    with pytest.raises(ValueError, match="redirect"):
        NoRedirect().redirect_request(None, None, None, None, None, None)


def test_http_failure_records_bounded_redacted_diagnostics_without_retry(tmp_path, monkeypatch):
    import io
    from urllib.error import HTTPError
    from reel_to_md.storage import read_json
    calls = []
    class Rejected:
        def open(self, request, timeout):
            calls.append(request)
            raise HTTPError(request.full_url, 400, 'Rejected', {}, io.BytesIO(b'api_key=private-example\ncontext exceeded\n' + b'x' * 20000))
    monkeypatch.setattr("reel_to_md.providers.build_opener", lambda *args: Rejected())
    measured = []
    model = LocalModel("http://127.0.0.1:8080/v1", "test", "v1", tmp_path, on_usage=measured.append)
    with pytest.raises(HTTPError):
        model.complete([], "call")
    error = read_json(tmp_path / 'call.error.json')
    assert error['http_status'] == 400 and error['body_truncated']
    assert 'context exceeded' in error['body'] and 'private-example' not in error['body']
    assert len(error['body']) <= 16384
    assert (tmp_path / 'call.pending').exists() and not (tmp_path / 'call.json').exists()
    assert measured[0]['input_tokens'] is None
    with pytest.raises(FileExistsError):
        model.complete([], "call")
    assert len(calls) == len(measured) == 1


def test_later_dispatch_failure_makes_total_usage_unknown(tmp_path, monkeypatch):
    from reel_to_md.pipeline import _usage

    class Job:
        record = {"input_tokens": 20, "output_tokens": 10, "model_calls": [{"cache_hit": False}]}

    class FailedOpener:
        def open(self, *args, **kwargs):
            raise TimeoutError("ambiguous dispatch")

    monkeypatch.setattr("reel_to_md.providers.build_opener", lambda *args: FailedOpener())
    job = Job()
    model = LocalModel("http://127.0.0.1:8080/v1", "test", "v1", tmp_path, on_usage=lambda usage: _usage(job, usage))
    with pytest.raises(TimeoutError):
        model.complete([], "call")
    assert job.record["input_tokens"] is None and job.record["output_tokens"] is None
    assert len(job.record["model_calls"]) == 2
    with pytest.raises(FileExistsError):
        model.complete([], "call")
    assert len(job.record["model_calls"]) == 2  # marker check did not dispatch again


@pytest.mark.parametrize("name", ["AWS_SECRET_ACCESS_KEY", "client_secret", "api_key"])
def test_conventional_credentials_redacted(name):
    assert "private-example" not in redact_text(name + "=private-example")


def test_ocr_preserves_command_lines(monkeypatch, tmp_path):
    from PIL import Image
    Image.new("RGB", (100, 100), "white").save(tmp_path / "frame.png")
    tsv = "page_num\tblock_num\tpar_num\tline_num\tconf\ttext\n1\t1\t1\t1\t90\tRun\n1\t1\t1\t2\t90\tpython\n1\t1\t1\t2\t90\tagent.py\n"
    monkeypatch.setattr("reel_to_md.media.command", lambda *args: tsv.encode())
    rows = ocr([{"file": "frame.png", "seconds": 0}], tmp_path)
    assert rows[0]["text"] == "Run\npython agent.py"
