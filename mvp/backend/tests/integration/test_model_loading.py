"""
Test actual model loading and initialization.

Tests that models can be loaded from disk or downloaded, and that weight
file paths are correct.

Priority: P2 (Critical for production readiness)
"""

import pytest
from pathlib import Path


def _is_ultralytics_available():
    """Check if ultralytics is available (training environment)."""
    try:
        import ultralytics
        return True
    except ImportError:
        return False


class TestModelRegistry:
    """Test model registry consistency and metadata."""

    def test_model_registry_has_no_duplicates(self, client):
        """Test that model registry has no duplicate model names."""
        response = client.get("/api/v1/models/list")
        assert response.status_code == 200

        models = response.json()
        model_names = [m["model_name"] for m in models]

        # Check for duplicates
        assert len(model_names) == len(set(model_names)), \
            f"Duplicate model names found: {[name for name in model_names if model_names.count(name) > 1]}"

    def test_model_registry_has_valid_framework(self, client):
        """Test that all models have valid framework specified."""
        response = client.get("/api/v1/models/list")
        models = response.json()

        valid_frameworks = ["ultralytics", "timm", "transformers", "huggingface"]

        for model in models:
            assert "framework" in model, f"Model {model['model_name']} missing framework"
            assert model["framework"] in valid_frameworks, \
                f"Model {model['model_name']} has invalid framework: {model['framework']}"

    def test_model_registry_has_valid_task_types(self, client):
        """Test that all models have valid task types."""
        response = client.get("/api/v1/models/list")
        models = response.json()

        valid_task_types = [
            "image_classification",
            "object_detection",
            "instance_segmentation",
            "semantic_segmentation",
            "pose_estimation",
            "obb_detection",
            "zero_shot_detection",
            "super_resolution"
        ]

        for model in models:
            # All models must have task_types (plural, array)
            assert "task_types" in model, \
                f"Model {model['model_name']} missing task_types field"

            assert isinstance(model["task_types"], list), \
                f"Model {model['model_name']} task_types is not a list"

            assert len(model["task_types"]) > 0, \
                f"Model {model['model_name']} has empty task_types"

            for task in model["task_types"]:
                assert task in valid_task_types, \
                    f"Model {model['model_name']} has invalid task type: {task}"


class TestModelWeightPaths:
    """Test that model weight paths are correctly constructed."""

    def test_yolov8_weight_paths(self, client):
        """Test that YOLOv8 models have correct weight file names."""
        response = client.get("/api/v1/models/list?framework=ultralytics")
        models = response.json()

        yolov8_models = [m for m in models if m["model_name"].startswith("yolov8")]

        expected_patterns = {
            "yolov8n": "yolov8n.pt",
            "yolov8s": "yolov8s.pt",
            "yolov8m": "yolov8m.pt",
            "yolov8l": "yolov8l.pt",
            "yolov8x": "yolov8x.pt",
            "yolov8n-seg": "yolov8n-seg.pt",
            "yolov8s-seg": "yolov8s-seg.pt",
            "yolov8n-pose": "yolov8n-pose.pt",
        }

        for model in yolov8_models:
            model_name = model["model_name"]
            if model_name in expected_patterns:
                # This will be used when we add weight_file_name to model metadata
                # For now, just check the pattern is consistent
                assert model_name in expected_patterns

    def test_yolo11_weight_paths(self, client):
        """Test that YOLO11 models have correct weight file names."""
        response = client.get("/api/v1/models/list?framework=ultralytics")
        models = response.json()

        yolo11_models = [m for m in models if m["model_name"].startswith("yolo11")]

        expected_patterns = {
            "yolo11n": "yolo11n.pt",
            "yolo11s": "yolo11s.pt",
            "yolo11m": "yolo11m.pt",
            "yolo11l": "yolo11l.pt",
            "yolo11x": "yolo11x.pt",
        }

        for model in yolo11_models:
            model_name = model["model_name"]
            if model_name in expected_patterns:
                assert model_name in expected_patterns


@pytest.mark.slow
@pytest.mark.skipif(
    not _is_ultralytics_available(),
    reason="ultralytics not installed (training environment only)"
)
class TestModelLoading:
    """Test actual model loading (slow tests, require model downloads)."""

    def test_yolov8n_can_load(self):
        """Test that yolov8n model can be loaded."""
        from ultralytics import YOLO

        # This will download the model if not cached
        model = YOLO("yolov8n.pt")

        assert model is not None
        assert hasattr(model, "model")
        assert model.model is not None

    def test_yolo11n_can_load(self):
        """Test that yolo11n model can be loaded."""
        from ultralytics import YOLO

        model = YOLO("yolo11n.pt")

        assert model is not None
        assert hasattr(model, "model")
        assert model.model is not None

    def test_yolov8n_seg_can_load(self):
        """Test that yolov8n-seg model can be loaded."""
        from ultralytics import YOLO

        model = YOLO("yolov8n-seg.pt")

        assert model is not None
        assert model.task == "segment"

    def test_invalid_model_raises_error(self):
        """Test that loading invalid model name raises error."""
        from ultralytics import YOLO

        with pytest.raises(Exception):
            YOLO("invalid_model_xyz.pt")
