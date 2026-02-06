"""
Attachment Service
Handles file upload/download/delete operations with security validation
"""
import logging
import os
import uuid
from pathlib import Path
from typing import Optional, Tuple
from dataclasses import dataclass

import aiofiles
from fastapi import UploadFile, HTTPException

logger = logging.getLogger(__name__)

# File upload configuration
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "/var/absenzflow-uploads"))
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
ALLOWED_MIME_TYPES = [
    'application/pdf',
    'image/jpeg',
    'image/png',
    'image/gif',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'text/plain'
]

# Allowed file extensions (whitelist for defense-in-depth)
ALLOWED_EXTENSIONS = {
    '.pdf',      # PDF documents
    '.jpg',      # JPEG images
    '.jpeg',     # JPEG images
    '.png',      # PNG images
    '.gif',      # GIF images
    '.doc',      # Word documents (old format)
    '.docx',     # Word documents (new format)
    '.txt',      # Text files
}


@dataclass
class SavedFile:
    """Result of file save operation"""
    file_path: Path
    stored_filename: str
    file_size: int


class AttachmentService:
    """Service for managing file attachments"""

    def __init__(self, upload_dir: Path = UPLOAD_DIR):
        self.upload_dir = upload_dir

    async def validate_file(
        self,
        file: UploadFile,
        max_size: int = MAX_FILE_SIZE,
        allowed_types: list = ALLOWED_MIME_TYPES,
        allowed_extensions: set = ALLOWED_EXTENSIONS
    ) -> Tuple[int, bytes]:
        """
        Validates file MIME type, size, and extension

        Args:
            file: Uploaded file
            max_size: Maximum file size in bytes
            allowed_types: Allowed MIME types
            allowed_extensions: Allowed file extensions

        Returns:
            Tuple of (file_size, file_content)

        Raises:
            HTTPException: If validation fails
        """
        # Validate MIME type
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=400,
                detail=f"File type {file.content_type} not allowed"
            )

        # Validate file extension (defense-in-depth)
        original_filename = Path(file.filename).name  # Get only filename, no path
        file_ext = Path(original_filename).suffix.lower()

        # Validate file extension doesn't contain path separators
        if '/' in file_ext or '\\' in file_ext or '..' in file_ext:
            logger.error(f"Invalid file extension detected: {file_ext}")
            raise HTTPException(status_code=400, detail="Invalid file extension")

        # Validate file extension is in whitelist
        if file_ext not in allowed_extensions:
            logger.warning(f"File extension not allowed: {file_ext} (filename: {file.filename})")
            raise HTTPException(
                status_code=400,
                detail=f"File extension '{file_ext}' not allowed. Allowed: {', '.join(sorted(allowed_extensions))}"
            )

        # Validate file size (read in chunks to prevent memory issues)
        file_size = 0
        temp_content = []

        while chunk := await file.read(8192):  # 8KB chunks
            file_size += len(chunk)
            if file_size > max_size:
                raise HTTPException(
                    status_code=400,
                    detail=f"File too large (max {max_size / 1024 / 1024} MB)"
                )
            temp_content.append(chunk)

        file_content = b''.join(temp_content)
        return file_size, file_content

    async def save_file(
        self,
        file: UploadFile,
        file_content: bytes,
        absence_id: int
    ) -> SavedFile:
        """
        Saves file to disk with secure filename

        Args:
            file: Uploaded file (for metadata)
            file_content: File content bytes
            absence_id: ID of absence to associate file with

        Returns:
            SavedFile object with path and metadata

        Raises:
            HTTPException: If path traversal detected or save fails
        """
        # Generate secure filename with UUID
        original_filename = Path(file.filename).name
        file_ext = Path(original_filename).suffix.lower()
        stored_filename = f"{uuid.uuid4()}{file_ext}"

        # Create absence-specific subdirectory
        absence_dir = self.upload_dir / f"absence_{absence_id}"
        absence_dir.mkdir(parents=True, exist_ok=True)

        file_path = absence_dir / stored_filename

        # Verify final path is within upload directory (path traversal check)
        if not str(file_path.resolve()).startswith(str(self.upload_dir.resolve())):
            logger.error(f"Path traversal attempt in upload: {file_path}")
            raise HTTPException(status_code=400, detail="Invalid file path")

        # Save file to disk
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(file_content)

        logger.info(f"File uploaded: {file.filename} -> {stored_filename} ({len(file_content)} bytes)")

        return SavedFile(
            file_path=file_path,
            stored_filename=stored_filename,
            file_size=len(file_content)
        )

    def delete_file(self, file_path: str) -> None:
        """
        Deletes file from disk with path traversal check

        Args:
            file_path: Path to file to delete

        Raises:
            HTTPException: If path traversal detected
            FileNotFoundError: If file doesn't exist (logged, not raised)
            PermissionError: If permission denied (logged and raised as HTTPException)
        """
        try:
            upload_path = self.upload_dir.resolve()
            resolved_path = Path(file_path).resolve()

            # Verify path is within upload directory
            if not str(resolved_path).startswith(str(upload_path)):
                logger.error(f"Path traversal attempt detected: {resolved_path} not in {upload_path}")
                raise HTTPException(status_code=400, detail="Invalid file path")

            if resolved_path.exists():
                resolved_path.unlink()
                logger.info(f"Deleted file: {resolved_path}")
            else:
                logger.warning(f"File already deleted or not found: {resolved_path}")
        except FileNotFoundError:
            # Race condition: file was already deleted
            logger.warning(f"File not found (race condition): {file_path}")
        except PermissionError as e:
            logger.error(f"Permission denied deleting file: {file_path}")
            logger.debug(f"Permission error details: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Failed to delete file: permission denied")
        except OSError as e:
            logger.error(f"OS error deleting file {file_path}: {type(e).__name__}")
            logger.debug(f"OS error details: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Failed to delete file: system error")
        except Exception as e:
            logger.error(f"Unexpected error deleting file {file_path}: {type(e).__name__}")
            logger.debug(f"Unexpected error details: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Failed to delete file")

    def get_file_path(self, file_path: str) -> Path:
        """
        Resolves and validates file path

        Args:
            file_path: Path to file

        Returns:
            Resolved Path object

        Raises:
            HTTPException: If path traversal detected or file not found
        """
        upload_path = self.upload_dir.resolve()
        resolved_path = Path(file_path).resolve()

        # Verify path is within upload directory
        if not str(resolved_path).startswith(str(upload_path)):
            logger.error(f"Path traversal attempt detected in download: {resolved_path} not in {upload_path}")
            raise HTTPException(status_code=400, detail="Invalid file path")

        # Check if file exists
        if not resolved_path.exists():
            logger.error(f"File not found on disk: {resolved_path}")
            raise HTTPException(status_code=404, detail="File not found on server")

        return resolved_path


# Singleton instance
attachment_service = AttachmentService()
