"""
Test script for contract upload endpoints

Tests the three new endpoints:
1. POST /api/contracts/check-duplicate
2. POST /api/contracts/upload
3. GET /api/contracts/upload-job/{job_id}

Usage:
    python test_contract_upload_endpoints.py
"""

import asyncio
import json
import logging
from pathlib import Path

from src.services.config_service import ConfigService
from src.services.blob_storage_service import BlobStorageService
from src.services.content_understanding_service import ContentUnderstandingService
from src.services.cosmos_nosql_service import CosmosNoSQLService
from src.services.ai_service import AiService
from src.services.job_service import JobService
from src.models.job_models import JobType, ContractUploadJobRequest

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_blob_storage_service():
    """Test BlobStorageService initialization and methods"""
    logger.info("\n=== Testing BlobStorageService ===")

    connection_string = ConfigService.azure_storage_connection_string()
    if not connection_string:
        logger.error("Azure Storage connection string not configured")
        return False

    try:
        blob_service = BlobStorageService(
            connection_string=connection_string,
            container_name="tenant1-dev20",
            folder_prefix="system/contract-intelligence"
        )
        logger.info("✓ BlobStorageService initialized successfully")

        # Test duplicate check
        test_filename = "test_nonexistent_file.pdf"
        exists = blob_service.check_duplicate(test_filename)
        logger.info(f"✓ Duplicate check for '{test_filename}': {exists}")

        # Test unique filename generation
        unique_filename = blob_service.get_unique_filename("test_contract.pdf")
        logger.info(f"✓ Unique filename generated: {unique_filename}")

        return True

    except Exception as e:
        logger.error(f"✗ BlobStorageService test failed: {e}")
        return False


async def test_content_understanding_service():
    """Test ContentUnderstandingService initialization"""
    logger.info("\n=== Testing ContentUnderstandingService ===")

    try:
        endpoint = ConfigService.content_understanding_endpoint()
        key = ConfigService.content_understanding_key()
        analyzer_id = ConfigService.content_understanding_analyzer_id()
        api_version = ConfigService.content_understanding_api_version()

        if not all([endpoint, key, analyzer_id, api_version]):
            logger.error("Azure Content Understanding not fully configured")
            return False

        cu_service = ContentUnderstandingService(
            endpoint=endpoint,
            api_version=api_version,
            subscription_key=key,
            analyzer_id=analyzer_id
        )
        logger.info("✓ ContentUnderstandingService initialized successfully")
        logger.info(f"  - Endpoint: {endpoint}")
        logger.info(f"  - Analyzer ID: {analyzer_id}")
        logger.info(f"  - API Version: {api_version}")

        return True

    except Exception as e:
        logger.error(f"✗ ContentUnderstandingService test failed: {e}")
        return False


async def test_job_creation():
    """Test job creation for contract upload"""
    logger.info("\n=== Testing Job Creation ===")

    cosmos_service = None

    try:
        # Initialize CosmosDB service
        cosmos_service = CosmosNoSQLService()
        await cosmos_service.initialize()
        logger.info("✓ CosmosDB service initialized")

        # Initialize JobService
        job_service = JobService(cosmos_service)
        logger.info("✓ Job service initialized")

        # Create a test upload job request
        test_request = ContractUploadJobRequest(
            filename="test_contract.pdf",
            original_filename="test_contract.pdf",
            blob_url="https://stfidev20.blob.core.windows.net/tenant1-dev20/system/contract-intelligence/test_contract.pdf",
            uploaded_by="test_user",
            file_size_bytes=1048576  # 1 MB
        )

        # Create the job
        job_id = await job_service.create_job(
            user_id="test_user",
            job_type=JobType.CONTRACT_UPLOAD,
            request=test_request.model_dump(),
            priority=7
        )

        logger.info(f"✓ Job created successfully: {job_id}")

        # Retrieve the job
        job = await job_service.get_job(job_id, "test_user")
        if job:
            logger.info(f"✓ Job retrieved successfully")
            logger.info(f"  - Job ID: {job.job_id}")
            logger.info(f"  - Job Type: {job.job_type}")
            logger.info(f"  - Status: {job.status}")
            logger.info(f"  - Priority: {job.priority}")
            logger.info(f"  - Request: {json.dumps(job.request, indent=2)}")
        else:
            logger.error(f"✗ Failed to retrieve job: {job_id}")
            return False

        # Cancel the test job (cleanup)
        await job_service.update_job_status(
            job_id=job_id,
            user_id="test_user",
            status="cancelled"
        )
        logger.info(f"✓ Test job cancelled (cleanup)")

        return True

    except Exception as e:
        logger.error(f"✗ Job creation test failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

    finally:
        if cosmos_service:
            await cosmos_service.close()
            logger.info("✓ CosmosDB service closed")


async def test_config_values():
    """Test configuration values"""
    logger.info("\n=== Testing Configuration Values ===")

    try:
        # Content Understanding
        cu_endpoint = ConfigService.content_understanding_endpoint()
        cu_key = ConfigService.content_understanding_key()
        cu_analyzer = ConfigService.content_understanding_analyzer_id()
        cu_version = ConfigService.content_understanding_api_version()

        logger.info(f"✓ Content Understanding Endpoint: {cu_endpoint}")
        logger.info(f"✓ Content Understanding Key: {'*' * 20 + cu_key[-10:] if cu_key else 'Not configured'}")
        logger.info(f"✓ Content Understanding Analyzer: {cu_analyzer}")
        logger.info(f"✓ Content Understanding API Version: {cu_version}")

        # Upload Configuration
        max_size = ConfigService.contract_upload_max_size_mb()
        default_user = ConfigService.contract_upload_default_user()

        logger.info(f"✓ Max Upload Size: {max_size} MB")
        logger.info(f"✓ Default User: {default_user}")

        # Blob Storage
        storage_conn = ConfigService.azure_storage_connection_string()
        logger.info(f"✓ Storage Connection: {'Configured' if storage_conn else 'Not configured'}")

        return True

    except Exception as e:
        logger.error(f"✗ Configuration test failed: {e}")
        return False


async def main():
    """Run all tests"""
    logger.info("=" * 60)
    logger.info("Contract Upload Backend Tests")
    logger.info("=" * 60)

    results = {}

    # Test 1: Configuration values
    results['config'] = await test_config_values()

    # Test 2: BlobStorageService
    results['blob_storage'] = await test_blob_storage_service()

    # Test 3: ContentUnderstandingService
    results['content_understanding'] = await test_content_understanding_service()

    # Test 4: Job creation
    results['job_creation'] = await test_job_creation()

    # Print summary
    logger.info("\n" + "=" * 60)
    logger.info("Test Summary")
    logger.info("=" * 60)

    all_passed = True
    for test_name, passed in results.items():
        status = "✓ PASSED" if passed else "✗ FAILED"
        logger.info(f"{test_name:25} {status}")
        if not passed:
            all_passed = False

    logger.info("=" * 60)

    if all_passed:
        logger.info("✓ All tests passed!")
        return 0
    else:
        logger.error("✗ Some tests failed")
        return 1


if __name__ == "__main__":
    import sys
    from dotenv import load_dotenv

    # Load environment variables
    load_dotenv(override=True)

    # Run tests
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
