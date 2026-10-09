import pytest

from app.services.storage import LocalStorageService, StorageError


def test_storage_dir_creation(tmp_path):
    """Test that the storage service creates the directory if it's missing."""
    storage_dir = tmp_path / "certs"

    # Pre-condition: doesn't exist
    assert not storage_dir.exists()

    # Initialize service
    LocalStorageService(storage_dir=storage_dir)

    # Post-condition: exists
    assert storage_dir.exists()
    assert storage_dir.is_dir()


def test_save_artifact_success(tmp_path):
    """Test saving a file from a temp location to the storage directory."""
    storage_dir = tmp_path / "storage"
    service = LocalStorageService(storage_dir=storage_dir)

    # Create a dummy temp file
    temp_file = tmp_path / "temp_cert.pdf"
    temp_file.write_text("dummy pdf content")

    # Save the artifact
    relative_path = service.save_artifact(temp_file)

    # Assertions
    assert relative_path.endswith(".pdf")

    final_path = storage_dir / relative_path
    assert final_path.exists()
    assert final_path.read_text() == "dummy pdf content"

    # Assert temp file was moved/cleaned up
    assert not temp_file.exists()


def test_save_artifact_missing_temp_file(tmp_path):
    """Test saving a file that doesn't exist raises an error."""
    storage_dir = tmp_path / "storage"
    service = LocalStorageService(storage_dir=storage_dir)

    missing_temp = tmp_path / "does_not_exist.pdf"

    with pytest.raises(StorageError, match="does not exist"):
        service.save_artifact(missing_temp)


def test_path_traversal_prevention(tmp_path):
    """Test that the returned identifier cannot contain path separators by design."""
    storage_dir = tmp_path / "storage"
    service = LocalStorageService(storage_dir=storage_dir)

    temp_file = tmp_path / "temp_cert.pdf"
    temp_file.write_text("data")

    # Save the artifact
    relative_path = service.save_artifact(temp_file)

    # Assert the relative path is a safe identifier without slashes
    assert "/" not in relative_path
    assert "\\" not in relative_path

    # The file should be precisely inside storage_dir, not escaping it
    final_path = storage_dir / relative_path
    assert final_path.parent == storage_dir
