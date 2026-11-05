from pathlib import Path
import subprocess

from PIL import Image, ImageDraw, ImageFont
import pytest

from reel_to_md import media


def test_current_user_install_found_without_path(tmp_path, monkeypatch):
    binary = tmp_path / "Programs/Tesseract-OCR/tesseract.exe"
    binary.parent.mkdir(parents=True)
    binary.write_bytes(b"fixture")
    monkeypatch.delenv("TESSERACT_CMD", raising=False)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    monkeypatch.setattr(media.shutil, "which", lambda name: None)
    assert media.tesseract_command() == str(binary)


def test_explicit_ocr_override(monkeypatch):
    monkeypatch.setenv("TESSERACT_CMD", "custom-ocr")
    assert media.tesseract_command() == "custom-ocr"


def test_installed_english_ocr_reads_exact_command(tmp_path):
    executable = media.tesseract_command()
    try:
        probe = subprocess.run([executable, "--list-langs"], capture_output=True, timeout=10)
    except FileNotFoundError:
        pytest.skip("Tesseract is not installed")
    assert probe.returncode == 0 and "eng" in (probe.stdout + probe.stderr).decode()
    assert media.tool_version("tesseract").startswith("tesseract ")
    candidates = [Path("C:/Windows/Fonts/consola.ttf"), Path("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf")]
    font_path = next((p for p in candidates if p.exists()), None)
    font = ImageFont.truetype(str(font_path), 38) if font_path else ImageFont.load_default(size=38)
    image = Image.new("RGB", (800, 200), "white")
    ImageDraw.Draw(image).text((30, 60), "python agent.py", font=font, fill="black")
    image.save(tmp_path / "frame.png")
    evidence = media.ocr([{"file": "frame.png", "seconds": 2.5}], tmp_path)
    assert evidence[0]["text"] == "python agent.py"
    assert evidence[0]["start_seconds"] == evidence[0]["end_seconds"] == 2.5


@pytest.mark.parametrize("size, expected", [((960, 540), (1920, 1080)), ((3840, 2160), (3840, 2160))])
def test_ocr_preprocessing_preserves_source_and_literal_spaces(tmp_path, monkeypatch, size, expected):
    source = tmp_path / "frame.png"
    Image.new("RGB", size, "white").save(source)
    original = source.read_bytes()
    prepared_paths = []

    def recognize(args, timeout):
        prepared = Path(args[1])
        prepared_paths.append(prepared)
        with Image.open(prepared) as image:
            assert image.size == expected
        return b"page_num\tblock_num\tpar_num\tline_num\tconf\ttext\n1\t1\t1\t1\t90\tpython\n1\t1\t1\t1\t90\tagent.\n1\t1\t1\t1\t90\tpy\n"

    monkeypatch.setattr(media, "command", recognize)
    evidence = media.ocr([{"file": "frame.png", "seconds": 2.5}], tmp_path)
    assert evidence[0]["text"] == "python agent. py"
    assert source.read_bytes() == original
    assert all(not path.exists() for path in prepared_paths)
