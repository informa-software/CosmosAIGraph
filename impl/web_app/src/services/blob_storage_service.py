"""
Azure Blob Storage Service for Contract PDF Management

This service handles all interactions with Azure Blob Storage for storing and
retrieving contract PDF files.

Configuration:
    - Container: tenant1-dev20
    - Folder Structure: system/contract-intelligence/
    - Authentication: Connection String (from environment)
"""

from azure.storage.blob import BlobServiceClient, generate_blob_sas, BlobSasPermissions, ContentSettings
from datetime import datetime, timedelta
from typing import Optional, List, BinaryIO
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)


class BlobStorageService:
    """
    Service for managing contract PDF files in Azure Blob Storage.

    This service provides methods for uploading, downloading, and generating
    secure access URLs for contract PDFs stored in Azure Blob Storage.
    """

    def __init__(
        self,
        connection_string: str,
        container_name: str = "tenant1-dev20",
        folder_prefix: str = "system/contract-intelligence"
    ):
        """
        Initialize the Blob Storage Service.

        Args:
            connection_string: Azure Storage connection string
            container_name: Name of the blob container (default: tenant1-dev20)
            folder_prefix: Folder path within container (default: system/contract-intelligence)
        """
        self.connection_string = connection_string
        self.container_name = container_name
        self.folder_prefix = folder_prefix.rstrip('/')  # Remove trailing slash if present

        # Initialize blob service client
        self.blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        self.container_client = self.blob_service_client.get_container_client(container_name)

        # Extract account name and key for SAS generation
        self.account_name = self._extract_account_name(connection_string)
        self.account_key = self._extract_account_key(connection_string)

        logger.info(
            f"BlobStorageService initialized: container={container_name}, "
            f"folder={folder_prefix}"
        )

    def _extract_account_name(self, connection_string: str) -> str:
        """Extract storage account name from connection string."""
        for part in connection_string.split(';'):
            if part.startswith('AccountName='):
                return part.split('=', 1)[1]
        raise ValueError("AccountName not found in connection string")

    def _extract_account_key(self, connection_string: str) -> str:
        """Extract account key from connection string."""
        for part in connection_string.split(';'):
            if part.startswith('AccountKey='):
                return part.split('=', 1)[1]
        raise ValueError("AccountKey not found in connection string")

    def _get_blob_path(self, filename: str) -> str:
        """
        Construct full blob path with folder prefix.

        Args:
            filename: Base filename (e.g., "contract.pdf")

        Returns:
            Full path: "system/contract-intelligence/contract.pdf"
        """
        return f"{self.folder_prefix}/{filename}"

    def generate_sas_url(
        self,
        filename: str,
        expiry_hours: int = 1,
        include_folder_prefix: bool = True
    ) -> str:
        """
        Generate a time-limited SAS URL for secure file access.

        Args:
            filename: Name of the file (just filename, not full path)
            expiry_hours: Hours until the URL expires (default: 1 hour)
            include_folder_prefix: Whether to include folder prefix in path (default: True)

        Returns:
            Secure SAS URL with read permissions

        Example:
            >>> service.generate_sas_url("contract_123.pdf", expiry_hours=2)
            "https://stfidev20.blob.core.windows.net/tenant1-dev20/system/contract-intelligence/contract_123.pdf?sv=2021-06-08&..."
        """
        try:
            # Construct blob path with folder prefix
            blob_path = self._get_blob_path(filename) if include_folder_prefix else filename
            blob_client = self.container_client.get_blob_client(blob_path)

            # Generate SAS token with read permission and inline content disposition
            sas_token = generate_blob_sas(
                account_name=self.account_name,
                container_name=self.container_name,
                blob_name=blob_path,
                account_key=self.account_key,
                permission=BlobSasPermissions(read=True),
                expiry=datetime.utcnow() + timedelta(hours=expiry_hours),
                content_disposition='inline'  # Display in browser instead of downloading
            )

            sas_url = f"{blob_client.url}?{sas_token}"
            logger.debug(f"Generated SAS URL for {filename} (expires in {expiry_hours}h)")
            return sas_url

        except Exception as e:
            logger.error(f"Failed to generate SAS URL for {filename}: {e}")
            raise

    def upload_file(
        self,
        file_path: str,
        blob_name: Optional[str] = None,
        overwrite: bool = True
    ) -> str:
        """
        Upload a file to blob storage.

        Args:
            file_path: Path to local file to upload
            blob_name: Name for the blob (defaults to filename from path)
            overwrite: Whether to overwrite existing file (default: True)

        Returns:
            Full blob URL (without SAS token)

        Example:
            >>> service.upload_file("local/contract.pdf", "CONTRACT_NAME.pdf")
            "https://stfidev20.blob.core.windows.net/tenant1-dev20/system/contract-intelligence/CONTRACT_NAME.pdf"
        """
        try:
            if blob_name is None:
                blob_name = os.path.basename(file_path)

            blob_path = self._get_blob_path(blob_name)
            blob_client = self.container_client.get_blob_client(blob_path)

            with open(file_path, "rb") as data:
                blob_client.upload_blob(data, overwrite=overwrite)

            logger.info(f"Uploaded {file_path} to {blob_path}")
            return blob_client.url

        except Exception as e:
            logger.error(f"Failed to upload {file_path}: {e}")
            raise

    def upload_file_object(
        self,
        file_object: BinaryIO,
        blob_name: str,
        overwrite: bool = True
    ) -> str:
        """
        Upload a file object (like from FastAPI UploadFile) to blob storage.

        Args:
            file_object: Binary file object to upload
            blob_name: Name for the blob
            overwrite: Whether to overwrite existing file (default: True)

        Returns:
            Full blob URL (without SAS token)
        """
        try:
            blob_path = self._get_blob_path(blob_name)
            blob_client = self.container_client.get_blob_client(blob_path)

            blob_client.upload_blob(file_object, overwrite=overwrite)

            logger.info(f"Uploaded file object to {blob_path}")
            return blob_client.url

        except Exception as e:
            logger.error(f"Failed to upload file object {blob_name}: {e}")
            raise

    def delete_file(self, filename: str) -> bool:
        """
        Delete a file from blob storage.

        Args:
            filename: Name of the file to delete

        Returns:
            True if successful, False otherwise
        """
        try:
            blob_path = self._get_blob_path(filename)
            blob_client = self.container_client.get_blob_client(blob_path)
            blob_client.delete_blob()

            logger.info(f"Deleted {blob_path} from blob storage")
            return True

        except Exception as e:
            logger.error(f"Failed to delete {filename}: {e}")
            return False

    def file_exists(self, filename: str) -> bool:
        """
        Check if a file exists in blob storage.

        Args:
            filename: Name of the file to check

        Returns:
            True if file exists, False otherwise
        """
        try:
            blob_path = self._get_blob_path(filename)
            blob_client = self.container_client.get_blob_client(blob_path)
            return blob_client.exists()

        except Exception as e:
            logger.error(f"Error checking existence of {filename}: {e}")
            return False

    def list_files(self, prefix: Optional[str] = None) -> List[str]:
        """
        List all PDF files in the container folder.

        Args:
            prefix: Optional additional prefix to filter files (appended to folder_prefix)

        Returns:
            List of filenames (without folder prefix)

        Example:
            >>> service.list_files()
            ["CONTRACT_1.pdf", "CONTRACT_2.pdf", ...]
        """
        try:
            # Construct full prefix
            full_prefix = self.folder_prefix
            if prefix:
                full_prefix = f"{self.folder_prefix}/{prefix.lstrip('/')}"

            blobs = self.container_client.list_blobs(name_starts_with=full_prefix)

            # Strip folder prefix from results to return just filenames
            prefix_length = len(self.folder_prefix) + 1  # +1 for the trailing slash
            filenames = []

            for blob in blobs:
                if blob.name.endswith('.pdf'):
                    # Remove folder prefix to get just the filename
                    filename = blob.name[prefix_length:]
                    filenames.append(filename)

            logger.info(f"Listed {len(filenames)} PDF files from {full_prefix}")
            return filenames

        except Exception as e:
            logger.error(f"Failed to list files: {e}")
            return []

    def get_file_metadata(self, filename: str) -> Optional[dict]:
        """
        Get metadata for a specific file.

        Args:
            filename: Name of the file

        Returns:
            Dictionary with file metadata or None if not found
        """
        try:
            blob_path = self._get_blob_path(filename)
            blob_client = self.container_client.get_blob_client(blob_path)

            properties = blob_client.get_blob_properties()

            return {
                'name': filename,
                'size': properties.size,
                'content_type': properties.content_settings.content_type,
                'last_modified': properties.last_modified,
                'created_on': properties.creation_time,
                'etag': properties.etag
            }

        except Exception as e:
            logger.error(f"Failed to get metadata for {filename}: {e}")
            return None

    def download_file(self, filename: str, destination_path: str) -> bool:
        """
        Download a file from blob storage to local disk.

        Args:
            filename: Name of the file in blob storage
            destination_path: Local path where file should be saved

        Returns:
            True if successful, False otherwise
        """
        try:
            blob_path = self._get_blob_path(filename)
            blob_client = self.container_client.get_blob_client(blob_path)

            # Ensure destination directory exists
            os.makedirs(os.path.dirname(destination_path), exist_ok=True)

            with open(destination_path, "wb") as download_file:
                download_file.write(blob_client.download_blob().readall())

            logger.info(f"Downloaded {blob_path} to {destination_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to download {filename}: {e}")
            return False

    def download_file_bytes(self, filename: str) -> bytes:
        """
        Download a file from blob storage as bytes.

        Args:
            filename: Name of the file in blob storage

        Returns:
            File content as bytes

        Raises:
            Exception: If download fails
        """
        try:
            blob_path = self._get_blob_path(filename)
            blob_client = self.container_client.get_blob_client(blob_path)

            file_bytes = blob_client.download_blob().readall()
            logger.info(f"Downloaded {blob_path} as bytes ({len(file_bytes)} bytes)")
            return file_bytes

        except Exception as e:
            logger.error(f"Failed to download {filename} as bytes: {e}")
            raise

    def check_duplicate(self, filename: str) -> bool:
        """
        Check if a file with the same name already exists in blob storage.

        Args:
            filename: Name of file to check

        Returns:
            True if file exists, False otherwise
        """
        return self.file_exists(filename)

    def get_unique_filename(self, original_filename: str) -> str:
        """
        Generate a unique filename by adding numbered suffix if needed.

        If the original filename exists, appends _1, _2, _3, etc. before
        the file extension until a unique name is found.

        Args:
            original_filename: Original filename (e.g., "contract.pdf")

        Returns:
            Unique filename (e.g., "contract_1.pdf" if duplicate)

        Example:
            >>> service.get_unique_filename("contract.pdf")
            "contract_1.pdf"  # if "contract.pdf" already exists
        """
        if not self.check_duplicate(original_filename):
            return original_filename

        # Split filename and extension
        name_parts = original_filename.rsplit('.', 1)
        if len(name_parts) == 2:
            base_name, extension = name_parts
        else:
            base_name = original_filename
            extension = ""

        # Try numbered suffixes
        counter = 1
        while counter < 1000:  # Safety limit to prevent infinite loop
            new_filename = f"{base_name}_{counter}.{extension}" if extension else f"{base_name}_{counter}"
            if not self.check_duplicate(new_filename):
                logger.info(f"Generated unique filename: {new_filename} (original: {original_filename})")
                return new_filename
            counter += 1

        # Fallback: use timestamp if we hit the counter limit
        import time
        timestamp = int(time.time())
        fallback_filename = f"{base_name}_{timestamp}.{extension}" if extension else f"{base_name}_{timestamp}"
        logger.warning(f"Counter limit reached, using timestamp-based filename: {fallback_filename}")
        return fallback_filename

    def upload_from_bytes(
        self,
        file_bytes: bytes,
        filename: str,
        overwrite: bool = False
    ) -> str:
        """
        Upload file from bytes to blob storage.

        Args:
            file_bytes: File content as bytes
            filename: Destination filename
            overwrite: Whether to overwrite if exists (default: False)

        Returns:
            Blob URL (without SAS token)

        Raises:
            Exception: If upload fails

        Example:
            >>> with open("contract.pdf", "rb") as f:
            ...     bytes_data = f.read()
            >>> service.upload_from_bytes(bytes_data, "contract.pdf")
            "https://stfidev20.blob.core.windows.net/tenant1-dev20/system/contract-intelligence/contract.pdf"
        """
        try:
            blob_path = self._get_blob_path(filename)
            blob_client = self.container_client.get_blob_client(blob_path)

            # Determine content type based on file extension
            content_type = 'application/pdf' if filename.lower().endswith('.pdf') else 'application/octet-stream'

            # Upload the file bytes with proper content type for inline viewing
            blob_client.upload_blob(
                file_bytes,
                overwrite=overwrite,
                content_settings=ContentSettings(
                    content_type=content_type,
                    content_disposition='inline'  # Allow inline viewing in browser
                )
            )

            logger.info(f"Uploaded {len(file_bytes)} bytes to blob storage: {blob_path} (content_type: {content_type})")
            return blob_client.url

        except Exception as e:
            logger.error(f"Failed to upload bytes as {filename}: {e}")
            raise
