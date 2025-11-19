"""
PDF Migration Script - Upload Local PDFs to Azure Blob Storage

This script uploads all contract PDF files from the local static/contracts/pdfs directory
to Azure Blob Storage in the configured container and folder path.

Usage:
    python migrate_pdfs_to_blob.py [--dry-run] [--force]

Arguments:
    --dry-run   : Preview what would be uploaded without actually uploading
    --force     : Upload all files even if they already exist in blob storage
    --verify    : Verify uploads by checking file existence after upload

Requirements:
    - Environment variables configured (see AZURE_BLOB_STORAGE_SETUP.md)
    - azure-storage-blob package installed
    - PDFs present in static/contracts/pdfs directory

Author: Claude Code
Date: 2025
"""

import os
import sys
import logging
from pathlib import Path
from typing import List, Tuple
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.services.blob_storage_service import BlobStorageService
from src.services.config_service import ConfigService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('pdf_migration.log')
    ]
)
logger = logging.getLogger(__name__)


class PDFMigrator:
    """Handles migration of PDF files from local disk to Azure Blob Storage"""

    def __init__(self, dry_run: bool = False, force: bool = False, verify: bool = True):
        """
        Initialize the PDF migrator.

        Args:
            dry_run: If True, only preview what would be uploaded without actually uploading
            force: If True, upload files even if they already exist in blob storage
            verify: If True, verify uploads by checking file existence after upload
        """
        self.dry_run = dry_run
        self.force = force
        self.verify = verify

        # Get configuration
        config = ConfigService()
        conn_str = config.azure_storage_connection_string()

        if not conn_str:
            raise ValueError(
                "Azure Storage connection string not configured. "
                "Please set CAIG_AZURE_STORAGE_CONNECTION_STRING environment variable."
            )

        # Initialize blob storage service
        self.blob_service = BlobStorageService(
            connection_string=conn_str,
            container_name=config.azure_storage_container(),
            folder_prefix=config.azure_storage_folder_prefix()
        )

        # Define source directory
        self.source_dir = Path(__file__).parent / "static" / "contracts" / "pdfs"

        if not self.source_dir.exists():
            raise ValueError(f"Source directory not found: {self.source_dir}")

        logger.info(f"PDFMigrator initialized:")
        logger.info(f"  Source directory: {self.source_dir}")
        logger.info(f"  Container: {config.azure_storage_container()}")
        logger.info(f"  Folder: {config.azure_storage_folder_prefix()}")
        logger.info(f"  Dry run: {self.dry_run}")
        logger.info(f"  Force upload: {self.force}")
        logger.info(f"  Verify uploads: {self.verify}")

    def get_local_pdfs(self) -> List[Path]:
        """
        Get list of all PDF files in the source directory.

        Returns:
            List of Path objects for PDF files
        """
        pdf_files = list(self.source_dir.glob("*.pdf"))
        logger.info(f"Found {len(pdf_files)} PDF files in source directory")
        return pdf_files

    def upload_pdf(self, pdf_path: Path) -> bool:
        """
        Upload a single PDF file to blob storage.

        Args:
            pdf_path: Path to the local PDF file

        Returns:
            True if upload successful, False otherwise
        """
        filename = pdf_path.name

        try:
            # Check if file already exists (unless force mode)
            if not self.force and self.blob_service.file_exists(filename):
                logger.info(f"⏭️  SKIP: {filename} (already exists in blob storage)")
                return True

            # Upload the file
            if self.dry_run:
                logger.info(f"🔍 DRY RUN: Would upload {filename}")
                return True
            else:
                blob_url = self.blob_service.upload_file(str(pdf_path), blob_name=filename)
                logger.info(f"✅ UPLOADED: {filename}")

                # Verify upload if requested
                if self.verify:
                    if self.blob_service.file_exists(filename):
                        logger.info(f"✓ VERIFIED: {filename}")
                    else:
                        logger.error(f"❌ VERIFY FAILED: {filename} not found after upload")
                        return False

                return True

        except Exception as e:
            logger.error(f"❌ FAILED: {filename} - {str(e)}")
            return False

    def migrate_all(self) -> Tuple[int, int, int]:
        """
        Migrate all PDF files from local directory to blob storage.

        Returns:
            Tuple of (total_files, successful_uploads, failed_uploads)
        """
        logger.info("\n" + "=" * 80)
        logger.info("Starting PDF Migration to Azure Blob Storage")
        logger.info("=" * 80 + "\n")

        pdf_files = self.get_local_pdfs()
        total_files = len(pdf_files)
        successful = 0
        failed = 0

        if total_files == 0:
            logger.warning("No PDF files found to migrate")
            return (0, 0, 0)

        for idx, pdf_path in enumerate(pdf_files, 1):
            logger.info(f"\n[{idx}/{total_files}] Processing: {pdf_path.name}")
            logger.info(f"  Size: {pdf_path.stat().st_size / 1024:.2f} KB")

            if self.upload_pdf(pdf_path):
                successful += 1
            else:
                failed += 1

        logger.info("\n" + "=" * 80)
        logger.info("Migration Complete")
        logger.info("=" * 80)
        logger.info(f"Total files: {total_files}")
        logger.info(f"Successful: {successful}")
        logger.info(f"Failed: {failed}")
        logger.info(f"Success rate: {(successful / total_files * 100):.1f}%")

        if self.dry_run:
            logger.info("\n⚠️  DRY RUN MODE - No files were actually uploaded")

        logger.info("\nMigration log saved to: pdf_migration.log")

        return (total_files, successful, failed)

    def list_blob_pdfs(self) -> List[str]:
        """
        List all PDF files currently in blob storage.

        Returns:
            List of PDF filenames in blob storage
        """
        return self.blob_service.list_files()

    def verify_migration(self) -> Tuple[int, int]:
        """
        Verify that all local PDFs exist in blob storage.

        Returns:
            Tuple of (total_checked, missing_count)
        """
        logger.info("\n" + "=" * 80)
        logger.info("Verifying Migration")
        logger.info("=" * 80 + "\n")

        local_pdfs = self.get_local_pdfs()
        blob_pdfs = set(self.list_blob_pdfs())

        total_checked = len(local_pdfs)
        missing = []

        for pdf_path in local_pdfs:
            filename = pdf_path.name
            if filename in blob_pdfs:
                logger.info(f"✅ FOUND: {filename}")
            else:
                logger.warning(f"❌ MISSING: {filename}")
                missing.append(filename)

        logger.info("\n" + "=" * 80)
        logger.info("Verification Complete")
        logger.info("=" * 80)
        logger.info(f"Total files checked: {total_checked}")
        logger.info(f"Found in blob storage: {total_checked - len(missing)}")
        logger.info(f"Missing from blob storage: {len(missing)}")

        if missing:
            logger.warning(f"\nMissing files: {', '.join(missing)}")

        return (total_checked, len(missing))


def main():
    """Main entry point for the migration script"""

    # Parse command line arguments
    dry_run = "--dry-run" in sys.argv
    force = "--force" in sys.argv
    verify_only = "--verify" in sys.argv

    print("\n" + "=" * 80)
    print("PDF Migration to Azure Blob Storage")
    print("=" * 80 + "\n")

    try:
        # Initialize migrator
        migrator = PDFMigrator(dry_run=dry_run, force=force, verify=not dry_run)

        # Verify-only mode
        if verify_only:
            total, missing = migrator.verify_migration()
            return 0 if missing == 0 else 1

        # Migration mode
        total, successful, failed = migrator.migrate_all()

        # Return exit code based on results
        if failed > 0:
            return 1  # Exit with error if any uploads failed
        elif total == 0:
            return 1  # Exit with error if no files found
        else:
            return 0  # Success

    except Exception as e:
        logger.error(f"\n❌ Migration failed with error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return 1


if __name__ == "__main__":
    # Show usage if --help flag provided
    if "--help" in sys.argv or "-h" in sys.argv:
        print(__doc__)
        sys.exit(0)

    exit_code = main()
    sys.exit(exit_code)
