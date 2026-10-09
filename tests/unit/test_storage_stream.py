import pytest

from app.services.storage import LocalStorageService, StorageError


def test_open_artifact_success(tmp_path):
    storage = LocalStorageService(storage_dir=tmp_path)
    file_path = tmp_path / "test.pdf"
    file_path.write_bytes(b"test content")

    stream = storage.open_artifact("test.pdf")
    content = b"".join(stream)
    assert content == b"test content"


def test_open_artifact_not_found(tmp_path):
    storage = LocalStorageService(storage_dir=tmp_path)
    with pytest.raises(StorageError) as exc:
        storage.open_artifact("missing.pdf")
    assert "not found" in str(exc.value)


def test_open_artifact_path_traversal(tmp_path):
    storage = LocalStorageService(storage_dir=tmp_path)
    with pytest.raises(StorageError) as exc:
        storage.open_artifact("../secret.txt")
    assert "traversal" in str(exc.value).lower() or "invalid" in str(exc.value).lower()


def test_open_artifact_absolute_path(tmp_path):
    storage = LocalStorageService(storage_dir=tmp_path)
    with pytest.raises(StorageError) as exc:
        storage.open_artifact("/etc/passwd")
    assert "traversal" in str(exc.value).lower() or "invalid" in str(exc.value).lower()
