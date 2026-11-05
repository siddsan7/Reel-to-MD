"""Decode an actual WAV through faster-whisper without requiring model weights."""
import wave

import pytest


def test_locked_pyav_decodes_audio_for_faster_whisper(tmp_path):
    pytest.importorskip("faster_whisper")
    from faster_whisper.audio import decode_audio
    path = tmp_path / "silent.wav"
    with wave.open(str(path), "wb") as stream:
        stream.setnchannels(1)
        stream.setsampwidth(2)
        stream.setframerate(16000)
        stream.writeframes(b"\0\0" * 16000)
    audio = decode_audio(str(path))
    assert len(audio) == 16000 and not audio.any()
