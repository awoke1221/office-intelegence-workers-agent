from io import BytesIO

import pytest
from fastapi import HTTPException

import backend_api


class MemoryResponse(BytesIO):
    def __init__(self, content: bytes):
        super().__init__(content)
        self.headers = {"Content-Length": str(len(content))}


def test_download_supabase_file_streams_to_temporary_path(monkeypatch, tmp_path):
    monkeypatch.setattr(backend_api, "UPLOAD_DIR", tmp_path)
    monkeypatch.setenv("SUPABASE_URL", "https://unit.supabase.co")
    response = MemoryResponse(b"account,total\n001,50\n")
    monkeypatch.setattr(backend_api, "urlopen", lambda request, timeout: response)

    result = backend_api._download_supabase_file(
        "https://unit.supabase.co/storage/v1/object/sign/office-intelligence-uploads/user/file.csv?token=one-time",
        "report.csv",
    )

    assert result.is_absolute()
    assert result.suffix == ".csv"
    assert result.read_bytes() == b"account,total\n001,50\n"


def test_download_supabase_file_rejects_other_hosts(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://unit.supabase.co")
    monkeypatch.setattr(backend_api, "urlopen", lambda *args, **kwargs: pytest.fail("unexpected request"))

    with pytest.raises(HTTPException) as error:
        backend_api._download_supabase_file(
            "https://attacker.example/storage/v1/object/sign/office-intelligence-uploads/user/file.csv?token=x",
            "report.csv",
        )

    assert error.value.status_code == 403


def test_download_supabase_file_enforces_configured_size(monkeypatch, tmp_path):
    monkeypatch.setattr(backend_api, "UPLOAD_DIR", tmp_path)
    monkeypatch.setenv("SUPABASE_URL", "https://unit.supabase.co")
    monkeypatch.setenv("MAX_UPLOAD_BYTES", "4")
    response = MemoryResponse(b"12345")
    monkeypatch.setattr(backend_api, "urlopen", lambda request, timeout: response)

    with pytest.raises(HTTPException) as error:
        backend_api._download_supabase_file(
            "https://unit.supabase.co/storage/v1/object/sign/office-intelligence-uploads/user/file.csv?token=one-time",
            "report.csv",
        )

    assert error.value.status_code == 413
    assert list(tmp_path.iterdir()) == []