import shutil
import uuid
from pathlib import Path

from app.core.config import get_settings


class StorageError(Exception):
    """Exception raised for storage-related failures."""

    pass


class LocalStorageService:
    """Service to handle storing generated artifacts on the local filesystem.

    This abstracts away the filesystem so it can be replaced with S3 or
    other object storage backends in the future without changing business logic.
    """

    def __init__(self, storage_dir: str | Path | None = None):
        settings = get_settings()
        self.storage_dir = Path(storage_dir) if storage_dir else Path(settings.STORAGE_DIR)

        # Ensure the directory exists
        try:
            self.storage_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            raise StorageError(f"Failed to create storage directory: {e}")

    def save_artifact(self, temp_file_path: str | Path) -> str:
        """
        Saves an artifact from a temporary location to the final storage.

        Args:
            temp_file_path: Path to the local temporary file.

        Returns:
            The relative path/identifier of the stored file (e.g., '123e4567-e89b-12d3.pdf').
        """
        temp_file = Path(temp_file_path)
        if not temp_file.exists():
            raise StorageError(f"Temporary file {temp_file} does not exist.")

        # Generate a safe, unique filename using UUID to prevent path traversal
        # and avoid exposing PII in the filesystem structure.
        file_id = str(uuid.uuid4())
        ext = temp_file.suffix
        final_filename = f"{file_id}{ext}"
        final_path = self.storage_dir / final_filename

        try:
            # Move the file atomically (or copy and remove across filesystems)
            shutil.move(str(temp_file), str(final_path))
        except OSError as e:
            raise StorageError(f"Failed to save artifact to {final_path}: {e}")

        # Return just the relative identifier, NOT the absolute machine path
        return final_filename
