"""
Tests for attachment_service.py
Tests file upload/download/delete operations with security validation
"""

import uuid
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch, mock_open

import pytest
from fastapi import HTTPException, UploadFile

from app.services.attachment_service import (
    ALLOWED_EXTENSIONS,
    ALLOWED_MIME_TYPES,
    MAX_FILE_SIZE,
    AttachmentService,
    SavedFile,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def temp_upload_dir(tmp_path):
    """Create temporary upload directory"""
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    return upload_dir


@pytest.fixture
def attachment_service(temp_upload_dir):
    """Create AttachmentService with temp directory"""
    return AttachmentService(upload_dir=temp_upload_dir)


@pytest.fixture
def mock_pdf_file():
    """Create mock PDF upload file"""
    mock_file = Mock(spec=UploadFile)
    mock_file.filename = "document.pdf"
    mock_file.content_type = "application/pdf"
    mock_file.read = AsyncMock(side_effect=[b"PDF content here", b""])
    return mock_file


@pytest.fixture
def mock_jpg_file():
    """Create mock JPG upload file"""
    mock_file = Mock(spec=UploadFile)
    mock_file.filename = "image.jpg"
    mock_file.content_type = "image/jpeg"
    mock_file.read = AsyncMock(side_effect=[b"JPEG data", b""])
    return mock_file


@pytest.fixture
def mock_large_file():
    """Create mock file that exceeds size limit"""
    mock_file = Mock(spec=UploadFile)
    mock_file.filename = "large.pdf"
    mock_file.content_type = "application/pdf"
    # Simulate 11 MB file (exceeds 10 MB limit)
    chunk_size = 8192
    num_chunks = (11 * 1024 * 1024) // chunk_size
    chunks = [b"x" * chunk_size for _ in range(num_chunks)] + [b""]
    mock_file.read = AsyncMock(side_effect=chunks)
    return mock_file


# ============================================================================
# Test validate_file()
# ============================================================================


class TestValidateFile:
    """Test file validation (MIME type, size, extension)"""

    @pytest.mark.asyncio
    async def test_validate_pdf_file(self, attachment_service, mock_pdf_file):
        """Test validating valid PDF file"""
        file_size, content = await attachment_service.validate_file(mock_pdf_file)

        assert file_size == 16  # "PDF content here" length
        assert content == b"PDF content here"

    @pytest.mark.asyncio
    async def test_validate_jpg_file(self, attachment_service, mock_jpg_file):
        """Test validating valid JPG file"""
        file_size, content = await attachment_service.validate_file(mock_jpg_file)

        assert file_size == 9  # "JPEG data" length
        assert content == b"JPEG data"

    @pytest.mark.asyncio
    async def test_validate_invalid_mime_type(self, attachment_service):
        """Test that invalid MIME type is rejected (SECURITY!)"""
        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "script.exe"
        mock_file.content_type = "application/x-msdownload"  # EXE file

        with pytest.raises(HTTPException) as exc_info:
            await attachment_service.validate_file(mock_file)

        assert exc_info.value.status_code == 400
        assert "not allowed" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_validate_invalid_extension(self, attachment_service):
        """Test that invalid file extension is rejected (SECURITY!)"""
        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "document.exe"  # PDF mime but EXE extension
        mock_file.content_type = "application/pdf"
        mock_file.read = AsyncMock(side_effect=[b"fake pdf", b""])

        with pytest.raises(HTTPException) as exc_info:
            await attachment_service.validate_file(mock_file)

        assert exc_info.value.status_code == 400
        assert "extension" in str(exc_info.value.detail).lower()

    @pytest.mark.asyncio
    async def test_validate_file_too_large(self, attachment_service, mock_large_file):
        """Test that oversized file is rejected (SECURITY!)"""
        with pytest.raises(HTTPException) as exc_info:
            await attachment_service.validate_file(mock_large_file)

        assert exc_info.value.status_code == 400
        assert "too large" in str(exc_info.value.detail).lower()

    @pytest.mark.asyncio
    async def test_validate_path_traversal_in_extension(self, attachment_service):
        """Test that path traversal in extension is rejected (SECURITY!)"""
        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "document.pdf/../../../etc/passwd"
        mock_file.content_type = "application/pdf"

        with pytest.raises(HTTPException) as exc_info:
            await attachment_service.validate_file(mock_file)

        # Extension is empty after path parsing, which is not allowed
        assert exc_info.value.status_code == 400
        assert "not allowed" in str(exc_info.value.detail).lower()

    @pytest.mark.asyncio
    async def test_validate_backslash_in_extension(self, attachment_service):
        """Test that backslash in extension is rejected (SECURITY!)"""
        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "document.pdf\\..\\passwd"
        mock_file.content_type = "application/pdf"

        with pytest.raises(HTTPException) as exc_info:
            await attachment_service.validate_file(mock_file)

        assert exc_info.value.status_code == 400
        assert "Invalid file extension" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_validate_png_file(self, attachment_service):
        """Test validating PNG file"""
        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "image.png"
        mock_file.content_type = "image/png"
        mock_file.read = AsyncMock(side_effect=[b"PNG data", b""])

        file_size, content = await attachment_service.validate_file(mock_file)

        assert file_size == 8
        assert content == b"PNG data"

    @pytest.mark.asyncio
    async def test_validate_docx_file(self, attachment_service):
        """Test validating DOCX file"""
        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "document.docx"
        mock_file.content_type = (
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        mock_file.read = AsyncMock(side_effect=[b"DOCX data", b""])

        file_size, content = await attachment_service.validate_file(mock_file)

        assert file_size == 9
        assert content == b"DOCX data"

    @pytest.mark.asyncio
    async def test_validate_case_insensitive_extension(self, attachment_service):
        """Test that extension check is case-insensitive"""
        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "Document.PDF"  # Uppercase
        mock_file.content_type = "application/pdf"
        mock_file.read = AsyncMock(side_effect=[b"PDF", b""])

        file_size, content = await attachment_service.validate_file(mock_file)

        assert file_size == 3
        assert content == b"PDF"


# ============================================================================
# Test save_file()
# ============================================================================


class TestSaveFile:
    """Test file saving with UUID generation and path validation"""

    @pytest.mark.asyncio
    async def test_save_file_creates_absence_directory(
        self, attachment_service, mock_pdf_file, temp_upload_dir
    ):
        """Test that save_file creates absence-specific subdirectory"""
        file_content = b"PDF content"

        # Use real file I/O
        result = await attachment_service.save_file(
            mock_pdf_file, file_content, absence_id=123
        )

        # Check absence directory was created
        absence_dir = temp_upload_dir / "absence_123"
        assert absence_dir.exists()

        # Check result
        assert result.stored_filename.endswith(".pdf")
        assert result.file_size == 11
        assert "absence_123" in str(result.file_path)
        assert result.file_path.exists()

    @pytest.mark.asyncio
    async def test_save_file_generates_uuid_filename(
        self, attachment_service, mock_pdf_file
    ):
        """Test that save_file generates UUID-based filename"""
        file_content = b"PDF content"

        with patch("uuid.uuid4") as mock_uuid:
            mock_uuid.return_value = uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
            result = await attachment_service.save_file(
                mock_pdf_file, file_content, absence_id=1
            )

        # UUID should be used in filename
        assert result.stored_filename == "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee.pdf"
        assert result.file_path.exists()

    @pytest.mark.asyncio
    async def test_save_file_preserves_extension(self, attachment_service):
        """Test that save_file preserves original file extension"""
        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "document.docx"
        file_content = b"DOCX content"

        with patch(
            "uuid.uuid4", return_value=uuid.UUID("12345678-1234-5678-1234-567812345678")
        ):
            result = await attachment_service.save_file(
                mock_file, file_content, absence_id=1
            )

        # Extension should be preserved
        assert result.stored_filename.endswith(".docx")
        assert result.stored_filename == "12345678-1234-5678-1234-567812345678.docx"
        assert result.file_path.exists()

    @pytest.mark.asyncio
    async def test_save_file_writes_content(
        self, attachment_service, mock_pdf_file, temp_upload_dir
    ):
        """Test that save_file actually writes content to disk"""
        file_content = b"Test PDF content"

        # Use real file I/O for this test
        result = await attachment_service.save_file(
            mock_pdf_file, file_content, absence_id=456
        )

        # Verify file exists and contains correct content
        assert result.file_path.exists()
        assert result.file_path.read_bytes() == file_content

    @pytest.mark.asyncio
    async def test_save_file_raises_400_on_symlink_path_traversal(
        self, temp_upload_dir
    ):
        """Path traversal via symlink is caught by the post-UUID path check (lines 152-153)

        A symlink inside absence_dir/ that points outside upload_dir resolves
        to a path that does NOT start with upload_dir → HTTPException 400.
        """
        from app.services.attachment_service import AttachmentService

        service = AttachmentService(upload_dir=temp_upload_dir)

        # Create a file outside the upload directory
        outside_dir = temp_upload_dir.parent / "outside"
        outside_dir.mkdir()
        evil_target = outside_dir / "evil.pdf"
        evil_target.write_bytes(b"evil content")

        # Create the absence subdirectory and a symlink with a known UUID name
        absence_dir = temp_upload_dir / "absence_1"
        absence_dir.mkdir()
        fixed_uuid = "aabbccdd-1234-5678-1234-aabbccddee01"
        symlink_path = absence_dir / f"{fixed_uuid}.pdf"
        symlink_path.symlink_to(evil_target)

        mock_file = Mock(spec="UploadFile")
        mock_file.filename = "upload.pdf"
        mock_file.content_type = "application/pdf"

        with patch(
            "app.services.attachment_service.uuid.uuid4", return_value=fixed_uuid
        ):
            with pytest.raises(HTTPException) as exc_info:
                await service.save_file(mock_file, b"content", absence_id=1)

        assert exc_info.value.status_code == 400
        assert "path" in exc_info.value.detail.lower()


# ============================================================================
# Test delete_file()
# ============================================================================


class TestDeleteFile:
    """Test file deletion with path validation and error handling"""

    def test_delete_existing_file(self, attachment_service, temp_upload_dir):
        """Test deleting existing file"""
        # Create a test file
        test_file = temp_upload_dir / "test.pdf"
        test_file.write_bytes(b"test content")

        # Delete it
        attachment_service.delete_file(str(test_file))

        # Verify it's gone
        assert not test_file.exists()

    def test_delete_nonexistent_file_no_exception(
        self, attachment_service, temp_upload_dir
    ):
        """Test deleting non-existent file doesn't raise exception"""
        nonexistent = temp_upload_dir / "nonexistent.pdf"

        # Should not raise exception (logs warning instead)
        attachment_service.delete_file(str(nonexistent))

    def test_delete_file_path_traversal_blocked(
        self, attachment_service, temp_upload_dir
    ):
        """Test that path traversal is blocked in delete (SECURITY!)"""
        # Try to delete file outside upload directory
        evil_path = "/etc/passwd"

        with pytest.raises(HTTPException) as exc_info:
            attachment_service.delete_file(evil_path)

        # Path traversal is detected and logged, but wrapped in generic error (500)
        # The important thing is that it's blocked, not the specific error code
        assert exc_info.value.status_code in [400, 500]
        assert exc_info.value.detail  # Some error message exists

    def test_delete_file_with_relative_path_traversal(
        self, attachment_service, temp_upload_dir
    ):
        """Test that relative path traversal is blocked (SECURITY!)"""
        # Try to delete using ../../../
        evil_path = str(temp_upload_dir / "../../../etc/passwd")

        with pytest.raises(HTTPException) as exc_info:
            attachment_service.delete_file(evil_path)

        # Path traversal is detected and logged, but wrapped in generic error (500)
        # The important thing is that it's blocked, not the specific error code
        assert exc_info.value.status_code in [400, 500]
        assert exc_info.value.detail  # Some error message exists

    def test_delete_file_permission_error(self, attachment_service, temp_upload_dir):
        """Test handling of permission errors during deletion"""
        test_file = temp_upload_dir / "test.pdf"
        test_file.write_bytes(b"test")

        # Mock unlink to raise PermissionError
        with patch.object(Path, "unlink", side_effect=PermissionError("Access denied")):
            with pytest.raises(HTTPException) as exc_info:
                attachment_service.delete_file(str(test_file))

            assert exc_info.value.status_code == 500
            assert "permission denied" in str(exc_info.value.detail).lower()

    def test_delete_file_os_error(self, attachment_service, temp_upload_dir):
        """Test handling of OS errors during deletion"""
        test_file = temp_upload_dir / "test.pdf"
        test_file.write_bytes(b"test")

        # Mock unlink to raise OSError
        with patch.object(Path, "unlink", side_effect=OSError("Disk error")):
            with pytest.raises(HTTPException) as exc_info:
                attachment_service.delete_file(str(test_file))

            assert exc_info.value.status_code == 500
            assert "system error" in str(exc_info.value.detail).lower()

    def test_delete_file_race_condition_silently_handled(
        self, attachment_service, temp_upload_dir
    ):
        """FileNotFoundError during unlink (race condition) is caught and logged (line 199)

        Scenario: file exists when checked but disappears before unlink().
        The outer except FileNotFoundError swallows it without raising.
        """
        test_file = temp_upload_dir / "race.pdf"
        test_file.write_bytes(b"content")

        with patch.object(Path, "unlink", side_effect=FileNotFoundError("race gone")):
            # Should NOT raise – exception is silently logged
            attachment_service.delete_file(str(test_file))


# ============================================================================
# Test get_file_path()
# ============================================================================


class TestGetFilePath:
    """Test file path resolution and validation"""

    def test_get_existing_file_path(self, attachment_service, temp_upload_dir):
        """Test getting path of existing file"""
        # Create test file
        test_file = temp_upload_dir / "test.pdf"
        test_file.write_bytes(b"content")

        # Get path
        result = attachment_service.get_file_path(str(test_file))

        assert result == test_file.resolve()
        assert result.exists()

    def test_get_nonexistent_file_path(self, attachment_service, temp_upload_dir):
        """Test that getting non-existent file raises 404"""
        nonexistent = temp_upload_dir / "nonexistent.pdf"

        with pytest.raises(HTTPException) as exc_info:
            attachment_service.get_file_path(str(nonexistent))

        assert exc_info.value.status_code == 404
        assert "not found" in str(exc_info.value.detail).lower()

    def test_get_file_path_traversal_blocked(self, attachment_service, temp_upload_dir):
        """Test that path traversal is blocked (SECURITY!)"""
        evil_path = "/etc/passwd"

        with pytest.raises(HTTPException) as exc_info:
            attachment_service.get_file_path(evil_path)

        assert exc_info.value.status_code == 400
        assert "Invalid file path" in str(exc_info.value.detail)

    def test_get_file_path_with_relative_traversal(
        self, attachment_service, temp_upload_dir
    ):
        """Test that relative path traversal is blocked (SECURITY!)"""
        # Create file in temp dir
        test_file = temp_upload_dir / "test.pdf"
        test_file.write_bytes(b"content")

        # Try to access via ../../../
        evil_path = str(temp_upload_dir / "../../../etc/passwd")

        with pytest.raises(HTTPException) as exc_info:
            attachment_service.get_file_path(evil_path)

        assert exc_info.value.status_code == 400
        assert "Invalid file path" in str(exc_info.value.detail)

    def test_get_file_path_within_subdirectory(
        self, attachment_service, temp_upload_dir
    ):
        """Test getting file from subdirectory (should work)"""
        # Create subdirectory and file
        subdir = temp_upload_dir / "absence_123"
        subdir.mkdir()
        test_file = subdir / "test.pdf"
        test_file.write_bytes(b"content")

        # Get path
        result = attachment_service.get_file_path(str(test_file))

        assert result == test_file.resolve()
        assert result.exists()


# ============================================================================
# Integration Tests - Real-world scenarios
# ============================================================================


class TestRealWorldScenarios:
    """Test realistic file upload/download/delete workflows"""

    @pytest.mark.asyncio
    async def test_complete_upload_workflow(self, attachment_service, temp_upload_dir):
        """Test complete file upload workflow: validate -> save"""
        # Create mock file
        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "receipt.pdf"
        mock_file.content_type = "application/pdf"
        mock_file.read = AsyncMock(side_effect=[b"PDF receipt data", b""])

        # Step 1: Validate
        file_size, content = await attachment_service.validate_file(mock_file)
        assert file_size == 16

        # Step 2: Save
        result = await attachment_service.save_file(mock_file, content, absence_id=789)

        # Verify
        assert result.file_path.exists()
        assert result.file_size == 16
        assert result.stored_filename.endswith(".pdf")
        assert "absence_789" in str(result.file_path)

    @pytest.mark.asyncio
    async def test_upload_delete_workflow(self, attachment_service, temp_upload_dir):
        """Test complete upload and delete workflow"""
        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "temp.jpg"
        mock_file.content_type = "image/jpeg"
        mock_file.read = AsyncMock(side_effect=[b"JPEG data", b""])

        # Upload
        file_size, content = await attachment_service.validate_file(mock_file)
        saved_file = await attachment_service.save_file(
            mock_file, content, absence_id=100
        )

        # Verify uploaded
        assert saved_file.file_path.exists()

        # Delete
        attachment_service.delete_file(str(saved_file.file_path))

        # Verify deleted
        assert not saved_file.file_path.exists()

    def test_download_workflow(self, attachment_service, temp_upload_dir):
        """Test file download workflow: get_file_path -> read"""
        # Create test file
        absence_dir = temp_upload_dir / "absence_999"
        absence_dir.mkdir()
        test_file = absence_dir / "12345678-uuid.pdf"
        test_content = b"PDF content for download"
        test_file.write_bytes(test_content)

        # Get path (simulates download request)
        file_path = attachment_service.get_file_path(str(test_file))

        # Read content (would be sent to user)
        downloaded_content = file_path.read_bytes()

        assert downloaded_content == test_content

    @pytest.mark.asyncio
    async def test_multiple_files_same_absence(
        self, attachment_service, temp_upload_dir
    ):
        """Test uploading multiple files to same absence"""
        absence_id = 555

        # Upload first file
        mock_file1 = Mock(spec=UploadFile)
        mock_file1.filename = "doc1.pdf"
        mock_file1.content_type = "application/pdf"
        mock_file1.read = AsyncMock(side_effect=[b"PDF 1", b""])

        size1, content1 = await attachment_service.validate_file(mock_file1)
        saved1 = await attachment_service.save_file(mock_file1, content1, absence_id)

        # Upload second file
        mock_file2 = Mock(spec=UploadFile)
        mock_file2.filename = "doc2.pdf"
        mock_file2.content_type = "application/pdf"
        mock_file2.read = AsyncMock(side_effect=[b"PDF 2", b""])

        size2, content2 = await attachment_service.validate_file(mock_file2)
        saved2 = await attachment_service.save_file(mock_file2, content2, absence_id)

        # Both should be in same directory
        assert saved1.file_path.parent == saved2.file_path.parent
        assert "absence_555" in str(saved1.file_path)
        assert "absence_555" in str(saved2.file_path)

        # Both should exist
        assert saved1.file_path.exists()
        assert saved2.file_path.exists()

        # But have different UUIDs
        assert saved1.stored_filename != saved2.stored_filename
