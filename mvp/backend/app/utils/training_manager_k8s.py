"""
Training Manager with Kubernetes Support.

Extended TrainingManager that supports both:
1. Training Service API (subprocess-based, original method)
2. Kubernetes Jobs (container-based, new method)
"""

import os
from typing import Optional
from sqlalchemy.orm import Session

from app.db import models
from app.services.vm_controller import VMController, TrainingJobConfig


class TrainingManagerK8s:
    """
    Training manager with dual execution support.

    Supports both subprocess-based (via Training Service API) and
    Kubernetes Job-based execution.
    """

    def __init__(self, db: Session, default_executor: str = "subprocess"):
        """
        Initialize training manager.

        Args:
            db: Database session
            default_executor: Default executor ("subprocess" or "kubernetes")
        """
        self.db = db
        self.default_executor = default_executor

        # Initialize VMController (lazy initialization)
        self._vm_controller = None

        # Check if K8s is available
        self.k8s_available = self._check_k8s_available()

        if self.default_executor == "kubernetes":
            if not self.k8s_available:
                print("[TrainingManager] WARNING: Kubernetes not available, falling back to subprocess")
                self.default_executor = "subprocess"
            else:
                print("[TrainingManager] Using Kubernetes Job executor (default)")
        else:
            print("[TrainingManager] Using Training Service API executor (default)")

    def _check_k8s_available(self) -> bool:
        """Check if Kubernetes client is available"""
        try:
            from kubernetes import client, config
            # Try to load config
            try:
                config.load_incluster_config()
                return True
            except:
                try:
                    config.load_kube_config()
                    return True
                except:
                    return False
        except ImportError:
            return False

    @property
    def vm_controller(self) -> VMController:
        """Lazy initialization of VMController"""
        if self._vm_controller is None:
            namespace = os.getenv("K8S_TRAINING_NAMESPACE", "training")
            self._vm_controller = VMController(namespace=namespace)
        return self._vm_controller

    def start_training(
        self,
        job_id: int,
        checkpoint_path: Optional[str] = None,
        resume: bool = False,
        executor: Optional[str] = None,
    ) -> bool:
        """
        Start training job.

        Args:
            job_id: Training job ID
            checkpoint_path: Optional checkpoint path
            resume: If True, resume from checkpoint
            executor: Override executor ("subprocess" or "kubernetes")

        Returns:
            True if training started successfully
        """
        # Get job from database
        job = self.db.query(models.TrainingJob).filter(models.TrainingJob.id == job_id).first()
        if not job:
            print(f"[TrainingManager] Job {job_id} not found")
            return False

        # Determine executor
        selected_executor = executor or job.executor_type or self.default_executor

        print(f"[TrainingManager] Starting job {job_id} with executor: {selected_executor}")

        # Route to appropriate executor
        if selected_executor == "kubernetes":
            if not self.k8s_available:
                print("[TrainingManager] Kubernetes not available, falling back to subprocess")
                return self._start_training_subprocess(job_id, checkpoint_path, resume)
            return self._start_training_k8s(job_id, checkpoint_path, resume)
        else:
            return self._start_training_subprocess(job_id, checkpoint_path, resume)

    def _start_training_k8s(
        self,
        job_id: int,
        checkpoint_path: Optional[str] = None,
        resume: bool = False,
    ) -> bool:
        """
        Start training via Kubernetes Job.

        Args:
            job_id: Training job ID
            checkpoint_path: Optional checkpoint path
            resume: If True, resume from checkpoint

        Returns:
            True if job created successfully
        """
        # Get job from database
        job = self.db.query(models.TrainingJob).filter(models.TrainingJob.id == job_id).first()
        if not job:
            print(f"[TrainingManager] Job {job_id} not found")
            return False

        try:
            # Build job configuration
            job_config = TrainingJobConfig(
                job_id=job.id,
                framework=job.framework,
                task_type=job.task_type,
                model_name=job.model_name,
                dataset_path=job.dataset_path or job.dataset_id,  # Use dataset_id if path not set
                dataset_format=job.dataset_format,
                num_classes=job.num_classes,
                epochs=job.epochs,
                batch_size=job.batch_size,
                learning_rate=job.learning_rate,
                optimizer="adam",  # TODO: Get from advanced_config
                project_id=job.project_id,
                image_size=None,  # Will be auto-determined by train.py
                pretrained=True,
                advanced_config=job.advanced_config,
                resources={
                    "gpu": 1,
                    "memory": "16Gi",
                    "cpu": 4,
                    "memory_request": "8Gi",
                    "cpu_request": 2,
                },
            )

            # Create Kubernetes Job
            k8s_job_name = self.vm_controller.create_training_job(job_config)

            # Update job in database
            job.status = "pending"
            job.executor_type = "kubernetes"
            job.execution_id = k8s_job_name
            self.db.commit()

            print(f"[TrainingManager] ✓ Kubernetes Job created: {k8s_job_name}")
            return True

        except Exception as e:
            print(f"[TrainingManager] ✗ Failed to create Kubernetes Job: {e}")
            import traceback
            traceback.print_exc()

            # Update job status to failed
            job.status = "failed"
            job.error_message = str(e)
            self.db.commit()

            return False

    def _start_training_subprocess(
        self,
        job_id: int,
        checkpoint_path: Optional[str] = None,
        resume: bool = False,
    ) -> bool:
        """
        Start training via Training Service API (subprocess-based).

        Args:
            job_id: Training job ID
            checkpoint_path: Optional checkpoint path
            resume: If True, resume from checkpoint

        Returns:
            True if training started successfully
        """
        from app.utils.training_client import TrainingServiceClient

        # Get job from database
        job = self.db.query(models.TrainingJob).filter(models.TrainingJob.id == job_id).first()
        if not job:
            print(f"[TrainingManager] Job {job_id} not found")
            return False

        try:
            # Initialize Training Service client
            client = TrainingServiceClient(framework=job.framework)

            # Build job configuration
            job_config = {
                "job_id": job.id,
                "framework": job.framework,
                "model_name": job.model_name,
                "task_type": job.task_type,
                "dataset_path": job.dataset_path or job.dataset_id,
                "dataset_format": job.dataset_format,
                "num_classes": job.num_classes,
                "epochs": job.epochs,
                "batch_size": job.batch_size,
                "learning_rate": job.learning_rate,
                "project_id": job.project_id,
                "advanced_config": job.advanced_config,
            }

            # Add checkpoint parameters if provided
            if checkpoint_path:
                job_config["checkpoint_path"] = checkpoint_path
                job_config["resume"] = resume

            # Start training via API
            success = client.start_training(job_config)

            if success:
                # Update job status
                job.status = "running"
                job.executor_type = "subprocess"
                self.db.commit()
                print(f"[TrainingManager] ✓ Training started via API for job {job_id}")
                return True
            else:
                print(f"[TrainingManager] ✗ Failed to start training via API")
                job.status = "failed"
                self.db.commit()
                return False

        except Exception as e:
            print(f"[TrainingManager] ✗ Error starting training: {e}")
            import traceback
            traceback.print_exc()

            job.status = "failed"
            job.error_message = str(e)
            self.db.commit()
            return False

    def stop_training(self, job_id: int) -> bool:
        """
        Stop a running training job.

        Args:
            job_id: Training job ID

        Returns:
            True if stopped successfully
        """
        # Get job from database
        job = self.db.query(models.TrainingJob).filter(models.TrainingJob.id == job_id).first()
        if not job:
            print(f"[TrainingManager] Job {job_id} not found")
            return False

        executor = job.executor_type or "subprocess"

        if executor == "kubernetes":
            return self._stop_training_k8s(job_id)
        else:
            return self._stop_training_subprocess(job_id)

    def _stop_training_k8s(self, job_id: int) -> bool:
        """Stop Kubernetes Job"""
        job = self.db.query(models.TrainingJob).filter(models.TrainingJob.id == job_id).first()
        if not job or not job.execution_id:
            return False

        try:
            # Delete Kubernetes Job
            self.vm_controller.delete_job(job.execution_id)

            # Update database
            job.status = "cancelled"
            self.db.commit()

            print(f"[TrainingManager] ✓ Stopped Kubernetes Job: {job.execution_id}")
            return True

        except Exception as e:
            print(f"[TrainingManager] ✗ Failed to stop Kubernetes Job: {e}")
            return False

    def _stop_training_subprocess(self, job_id: int) -> bool:
        """Stop subprocess-based training"""
        from app.utils.training_client import TrainingServiceClient

        job = self.db.query(models.TrainingJob).filter(models.TrainingJob.id == job_id).first()
        if not job:
            return False

        try:
            client = TrainingServiceClient(framework=job.framework)
            success = client.stop_training(job_id)

            if success:
                job.status = "cancelled"
                self.db.commit()
                return True
            return False

        except Exception as e:
            print(f"[TrainingManager] Error stopping training: {e}")
            return False

    def get_training_status(self, job_id: int) -> Optional[str]:
        """
        Get training job status.

        Args:
            job_id: Training job ID

        Returns:
            Job status or None if not found
        """
        job = self.db.query(models.TrainingJob).filter(models.TrainingJob.id == job_id).first()
        if not job:
            return None

        # For Kubernetes jobs, query K8s API
        if job.executor_type == "kubernetes" and job.execution_id:
            try:
                k8s_status = self.vm_controller.get_job_status(job.execution_id)

                # Update database if status changed
                if k8s_status != job.status:
                    job.status = k8s_status
                    self.db.commit()

                return k8s_status
            except Exception as e:
                print(f"[TrainingManager] Error getting K8s status: {e}")
                return job.status

        return job.status

    def get_training_logs(self, job_id: int, tail_lines: int = 100) -> str:
        """
        Get training logs.

        Args:
            job_id: Training job ID
            tail_lines: Number of lines to return

        Returns:
            Logs as string
        """
        job = self.db.query(models.TrainingJob).filter(models.TrainingJob.id == job_id).first()
        if not job:
            return ""

        # For Kubernetes jobs, get logs from pod
        if job.executor_type == "kubernetes" and job.execution_id:
            try:
                return self.vm_controller.get_job_logs(job.execution_id, tail_lines)
            except Exception as e:
                print(f"[TrainingManager] Error getting K8s logs: {e}")
                return f"Error getting logs: {e}"

        # For subprocess jobs, logs are in file or Training Service
        return "Subprocess logs not yet implemented via this method"
