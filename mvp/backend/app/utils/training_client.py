"""
Training Service HTTP Client

Communicates with separate Training Service for executing training jobs.
"""

import os
import requests
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class TrainingServiceClient:
    """Client for Training Service API."""

    def __init__(self, training_service_url: Optional[str] = None):
        """
        Initialize Training Service client.

        Args:
            training_service_url: URL of Training Service (from env if not provided)
        """
        self.base_url = training_service_url or os.getenv(
            "TRAINING_SERVICE_URL",
            "http://localhost:8001"  # Default for local development
        )
        logger.info(f"[TrainingClient] Using Training Service URL: {self.base_url}")

    def start_training(self, job_config: Dict[str, Any]) -> bool:
        """
        Start training job on Training Service.

        Args:
            job_config: Training configuration dict

        Returns:
            True if training started successfully

        Raises:
            requests.exceptions.RequestException: If API call fails
        """
        try:
            url = f"{self.base_url}/training/start"
            logger.info(f"[TrainingClient] Sending training request to {url}")
            logger.debug(f"[TrainingClient] Job config: {job_config}")

            response = requests.post(
                url,
                json=job_config,
                timeout=30
            )

            response.raise_for_status()
            result = response.json()

            logger.info(f"[TrainingClient] Training started: {result}")
            return True

        except requests.exceptions.RequestException as e:
            logger.error(f"[TrainingClient] Failed to start training: {e}")
            raise

    def get_job_status(self, job_id: int) -> Dict[str, Any]:
        """
        Get training job status from Training Service.

        Args:
            job_id: Job ID

        Returns:
            Job status dict

        Raises:
            requests.exceptions.RequestException: If API call fails
        """
        try:
            url = f"{self.base_url}/training/status/{job_id}"
            response = requests.get(url, timeout=10)
            response.raise_for_status()

            return response.json()

        except requests.exceptions.RequestException as e:
            logger.error(f"[TrainingClient] Failed to get job status: {e}")
            raise

    def health_check(self) -> bool:
        """
        Check if Training Service is healthy.

        Returns:
            True if service is healthy
        """
        try:
            url = f"{self.base_url}/health"
            response = requests.get(url, timeout=5)
            response.raise_for_status()

            result = response.json()
            return result.get("status") == "healthy"

        except requests.exceptions.RequestException:
            return False
