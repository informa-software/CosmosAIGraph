"""
Azure Content Understanding Service

Handles contract extraction using Azure Content Understanding API.
Based on Azure sample code for contract_extraction analyzer.

Chris Joakim, Microsoft, 2025
"""

import logging
import time
from typing import Any, Dict

import requests

logger = logging.getLogger(__name__)


class ContentUnderstandingService:
    """Service for Azure Content Understanding API interactions"""

    def __init__(self, endpoint: str, api_version: str, subscription_key: str, analyzer_id: str):
        """
        Initialize Content Understanding Service

        Args:
            endpoint: Azure CU endpoint URL
            api_version: API version to use
            subscription_key: Subscription key for authentication
            analyzer_id: Analyzer ID (e.g., "contract_extraction")
        """
        if not subscription_key:
            raise ValueError("Subscription key must be provided")
        if not endpoint:
            raise ValueError("Endpoint must be provided")
        if not api_version:
            raise ValueError("API version must be provided")
        if not analyzer_id:
            raise ValueError("Analyzer ID must be provided")

        self.endpoint = endpoint.rstrip("/")
        self.api_version = api_version
        self.analyzer_id = analyzer_id
        self.headers = {
            "Ocp-Apim-Subscription-Key": subscription_key,
            "x-ms-useragent": "contract-intelligence-workbench"
        }

        logger.info(f"ContentUnderstandingService initialized with analyzer: {analyzer_id}")

    def analyze_document_from_bytes(self, file_bytes: bytes, filename: str) -> Dict[str, Any]:
        """
        Analyze a contract document from bytes

        Args:
            file_bytes: PDF file content as bytes
            filename: Original filename (for logging)

        Returns:
            Analysis result as JSON dict

        Raises:
            requests.HTTPError: If API request fails
            TimeoutError: If polling times out
            RuntimeError: If analysis fails
        """
        logger.info(f"Starting contract analysis for: {filename}")

        # Start analysis
        response = self._begin_analyze(file_bytes)

        # Poll for results
        result = self._poll_result(response, timeout_seconds=300, polling_interval_seconds=2)

        logger.info(f"Contract analysis completed successfully for: {filename}")
        return result

    def _begin_analyze(self, file_bytes: bytes) -> requests.Response:
        """
        Begin analysis of file bytes

        Args:
            file_bytes: PDF file content

        Returns:
            Response object with operation-location header

        Raises:
            requests.HTTPError: If API request fails
        """
        url = f"{self.endpoint}/contentunderstanding/analyzers/{self.analyzer_id}:analyze"
        params = {
            "api-version": self.api_version,
            "stringEncoding": "utf16"
        }
        headers = {
            **self.headers,
            "Content-Type": "application/octet-stream"
        }

        logger.debug(f"Calling Azure CU endpoint: {url}")
        response = requests.post(url, params=params, headers=headers, data=file_bytes)
        response.raise_for_status()

        logger.info(f"Analysis started successfully, operation location: {response.headers.get('operation-location', 'N/A')}")
        return response

    def _poll_result(
        self,
        response: requests.Response,
        timeout_seconds: int = 300,
        polling_interval_seconds: int = 2
    ) -> Dict[str, Any]:
        """
        Poll for analysis results until complete or timeout

        Args:
            response: Initial response with operation-location
            timeout_seconds: Maximum wait time (default: 300s = 5 min)
            polling_interval_seconds: Time between polls (default: 2s)

        Returns:
            Analysis result JSON

        Raises:
            ValueError: If operation-location not found
            TimeoutError: If operation times out
            RuntimeError: If operation fails
        """
        operation_location = response.headers.get("operation-location", "")
        if not operation_location:
            raise ValueError("Operation location not found in response headers")

        start_time = time.time()
        poll_count = 0

        while True:
            elapsed_time = time.time() - start_time
            poll_count += 1

            if elapsed_time > timeout_seconds:
                raise TimeoutError(f"Analysis timed out after {timeout_seconds} seconds")

            # Poll for status
            poll_response = requests.get(operation_location, headers=self.headers)
            poll_response.raise_for_status()
            result = poll_response.json()

            status = result.get("status", "").lower()

            if status == "succeeded":
                logger.info(f"Analysis completed after {elapsed_time:.2f} seconds ({poll_count} polls)")
                return result
            elif status == "failed":
                error_info = result.get("error", {})
                error_msg = error_info.get("message", "Unknown error")
                error_code = error_info.get("code", "N/A")
                logger.error(f"Analysis failed - Code: {error_code}, Message: {error_msg}")
                raise RuntimeError(f"Analysis failed: {error_msg}")
            else:
                # Still running (status is typically "running" or "notStarted")
                if poll_count % 10 == 0:  # Log every 10 polls
                    logger.info(f"Analysis in progress (status: {status})... ({elapsed_time:.0f}s elapsed)")
                time.sleep(polling_interval_seconds)
