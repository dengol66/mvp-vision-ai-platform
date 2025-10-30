"""Training adapters for different frameworks."""

from platform_sdk import (
    TrainingAdapter,
    TaskType,
    DatasetFormat,
    ModelConfig,
    DatasetConfig,
    TrainingConfig,
    MetricsResult,
)

from .timm_adapter import TimmAdapter
from .ultralytics_adapter import UltralyticsAdapter

# Adapter registry
ADAPTER_REGISTRY = {
    'timm': TimmAdapter,
    'ultralytics': UltralyticsAdapter,
}

__all__ = [
    "TrainingAdapter",
    "TaskType",
    "DatasetFormat",
    "ModelConfig",
    "DatasetConfig",
    "TrainingConfig",
    "MetricsResult",
    "TimmAdapter",
    "UltralyticsAdapter",
    "ADAPTER_REGISTRY",
]
