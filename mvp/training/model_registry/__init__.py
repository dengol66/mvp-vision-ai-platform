"""Model registry for all supported models."""

from .timm_models import TIMM_MODEL_REGISTRY, get_timm_model_info
from .ultralytics_models import ULTRALYTICS_MODEL_REGISTRY, get_ultralytics_model_info
from .huggingface_models import HUGGINGFACE_MODEL_REGISTRY, get_huggingface_model

__all__ = [
    "TIMM_MODEL_REGISTRY",
    "ULTRALYTICS_MODEL_REGISTRY",
    "HUGGINGFACE_MODEL_REGISTRY",
    "get_timm_model_info",
    "get_ultralytics_model_info",
    "get_huggingface_model",
    "get_all_models",
    "get_model_info",
    "get_model_display_name",  # 🆕 Phase 1
    "get_task_display_name",   # 🆕 Phase 1
]


def get_all_models():
    """Get all models from all registries."""
    all_models = []

    # Add timm models
    for model_name, info in TIMM_MODEL_REGISTRY.items():
        all_models.append({
            "framework": "timm",
            "model_name": model_name,
            **info
        })

    # Add ultralytics models
    for model_name, info in ULTRALYTICS_MODEL_REGISTRY.items():
        all_models.append({
            "framework": "ultralytics",
            "model_name": model_name,
            **info
        })

    # Add huggingface models
    for model_name, info in HUGGINGFACE_MODEL_REGISTRY.items():
        all_models.append({
            "framework": "huggingface",
            "model_name": model_name,
            **info
        })

    return all_models


def get_model_info(framework: str, model_name: str):
    """Get model info by framework and model name."""
    if framework == "timm":
        return get_timm_model_info(model_name)
    elif framework == "ultralytics":
        return get_ultralytics_model_info(model_name)
    elif framework == "huggingface":
        return get_huggingface_model(model_name)
    else:
        return None


# 🆕 Phase 1: Helper functions for display names

def get_model_display_name(framework: str, model_name: str) -> str:
    """
    Get user-friendly display name for a model.

    Args:
        framework: Framework name (timm, ultralytics, huggingface)
        model_name: Model ID (e.g., "resnet50", "google/vit-base-patch16-224")

    Returns:
        Display name (e.g., "ResNet-50", "Vision Transformer (ViT) Base")
        Falls back to model_name if not found.
    """
    model_info = get_model_info(framework, model_name)
    if model_info and "display_name" in model_info:
        return model_info["display_name"]
    return model_name  # Fallback


def get_task_display_name(task_type: str) -> str:
    """
    Get user-friendly display name for a task type.

    Args:
        task_type: Task type (e.g., "image_classification", "object_detection")

    Returns:
        Korean display name (e.g., "이미지 분류", "객체 탐지")
    """
    TASK_DISPLAY_NAMES = {
        "image_classification": "이미지 분류",
        "object_detection": "객체 탐지",
        "instance_segmentation": "인스턴스 분할",
        "semantic_segmentation": "시맨틱 분할",
        "pose_estimation": "자세 추정",
        "super_resolution": "초해상화",
        "segmentation": "분할",  # Unified segmentation
    }
    return TASK_DISPLAY_NAMES.get(task_type, task_type)
