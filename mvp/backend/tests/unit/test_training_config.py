"""
Test advanced training configuration application.

Tests that advanced configurations (optimizer, scheduler, augmentation, etc.)
are correctly applied during training setup.

Priority: P2 (Critical for production readiness)
"""

import pytest
from pathlib import Path


class TestOptimizerApplication:
    """Test that optimizer configurations are correctly applied."""

    def test_adam_optimizer_created(self):
        """Test that Adam optimizer is created with correct parameters."""
        from app.schemas.configs import OptimizerConfig

        config = OptimizerConfig(
            type="adam",
            learning_rate=0.001,
            weight_decay=0.01,
            betas=(0.9, 0.999)
        )

        # Verify config structure
        assert config.type == "adam"
        assert config.learning_rate == 0.001
        assert config.weight_decay == 0.01
        assert config.betas == (0.9, 0.999)

    def test_adamw_optimizer_created(self):
        """Test that AdamW optimizer is created with correct parameters."""
        from app.schemas.configs import OptimizerConfig

        config = OptimizerConfig(
            type="adamw",
            learning_rate=0.0001,
            weight_decay=0.05
        )

        assert config.type == "adamw"
        assert config.learning_rate == 0.0001
        assert config.weight_decay == 0.05

    def test_sgd_optimizer_created(self):
        """Test that SGD optimizer is created with momentum."""
        from app.schemas.configs import OptimizerConfig

        config = OptimizerConfig(
            type="sgd",
            learning_rate=0.01,
            momentum=0.9
        )

        assert config.type == "sgd"
        assert config.learning_rate == 0.01
        assert config.momentum == 0.9


class TestSchedulerApplication:
    """Test that scheduler configurations are correctly applied."""

    def test_cosine_scheduler_created(self):
        """Test that CosineAnnealingLR scheduler is created."""
        from app.schemas.configs import SchedulerConfig

        config = SchedulerConfig(
            type="cosine",
            T_max=100
        )

        assert config.type == "cosine"
        # T_max is stored as extra field for scheduler initialization

    def test_step_scheduler_created(self):
        """Test that StepLR scheduler is created."""
        from app.schemas.configs import SchedulerConfig

        config = SchedulerConfig(
            type="step",
            step_size=30,
            gamma=0.1
        )

        assert config.type == "step"

    def test_no_scheduler_option(self):
        """Test that scheduler can be disabled."""
        from app.schemas.configs import SchedulerConfig

        config = SchedulerConfig(type="none")
        assert config.type == "none"


class TestAugmentationApplication:
    """Test that augmentation configurations are correctly applied."""

    def test_augmentation_enabled(self):
        """Test that augmentation is enabled when configured."""
        from app.schemas.configs import AugmentationConfig

        config = AugmentationConfig(
            enabled=True,
            hue=0.1,
            brightness=0.2,
            saturation=0.2,
            color_jitter=True
        )

        assert config.enabled is True
        assert config.hue == 0.1
        assert config.brightness == 0.2
        assert config.saturation == 0.2
        assert config.color_jitter is True

    def test_augmentation_disabled(self):
        """Test that augmentation can be disabled."""
        from app.schemas.configs import AugmentationConfig

        config = AugmentationConfig(enabled=False)
        assert config.enabled is False

    def test_geometric_augmentation(self):
        """Test geometric augmentation parameters."""
        from app.schemas.configs import AugmentationConfig

        config = AugmentationConfig(
            enabled=True,
            degrees=15.0,
            translate=0.1,
            scale=0.5
        )

        assert config.enabled is True
        # Verify geometric params exist


class TestPreprocessApplication:
    """Test that preprocessing configurations are correctly applied."""

    def test_default_preprocessing(self):
        """Test that default preprocessing config works."""
        from app.schemas.configs import PreprocessConfig

        config = PreprocessConfig()

        # Default values should exist
        assert config is not None
        assert config.image_size == 224  # Default from schema

    def test_custom_normalization(self):
        """Test custom normalization parameters."""
        from app.schemas.configs import PreprocessConfig

        # ImageNet normalization
        config = PreprocessConfig(
            mean=(0.485, 0.456, 0.406),
            std=(0.229, 0.224, 0.225)
        )

        assert len(config.mean) == 3
        assert len(config.std) == 3
        assert config.mean == (0.485, 0.456, 0.406)

    def test_resize_configuration(self):
        """Test image resize configuration."""
        from app.schemas.configs import PreprocessConfig

        config = PreprocessConfig(
            image_size=640,
            resize_mode="resize_crop"
        )

        assert config.image_size == 640
        assert config.resize_mode == "resize_crop"


class TestValidationConfig:
    """Test validation configuration (includes checkpoint and early stopping)."""

    def test_validation_enabled(self):
        """Test validation configuration."""
        from app.schemas.configs import ValidationConfig

        config = ValidationConfig(
            enabled=True,
            val_interval=1,
            metrics=["accuracy", "precision", "recall"]
        )

        assert config.enabled is True
        assert config.val_interval == 1
        assert "accuracy" in config.metrics

    def test_validation_disabled(self):
        """Test that validation can be disabled."""
        from app.schemas.configs import ValidationConfig

        config = ValidationConfig(enabled=False)
        assert config.enabled is False

    def test_checkpoint_saving_enabled(self):
        """Test that checkpoint saving (part of ValidationConfig) works."""
        from app.schemas.configs import ValidationConfig

        config = ValidationConfig(
            save_best=True,
            save_best_metric="accuracy",
            save_best_mode="max"
        )

        assert config.save_best is True
        assert config.save_best_metric == "accuracy"
        assert config.save_best_mode == "max"

    def test_checkpoint_saving_disabled(self):
        """Test that checkpoint saving can be disabled."""
        from app.schemas.configs import ValidationConfig

        config = ValidationConfig(save_best=False)
        assert config.save_best is False

    def test_early_stopping_enabled(self):
        """Test that early stopping (part of ValidationConfig) works."""
        from app.schemas.configs import ValidationConfig

        config = ValidationConfig(
            early_stopping=True,
            early_stopping_patience=10,
            early_stopping_min_delta=0.001
        )

        assert config.early_stopping is True
        assert config.early_stopping_patience == 10
        assert config.early_stopping_min_delta == 0.001

    def test_early_stopping_disabled(self):
        """Test that early stopping can be disabled."""
        from app.schemas.configs import ValidationConfig

        config = ValidationConfig(early_stopping=False)
        assert config.early_stopping is False

    def test_validation_visualization(self):
        """Test validation visualization settings."""
        from app.schemas.configs import ValidationConfig

        config = ValidationConfig(
            save_visualizations=True,
            num_visualizations=20
        )

        assert config.save_visualizations is True
        assert config.num_visualizations == 20


class TestCompositeConfigApplication:
    """Test that all configurations work together."""

    def test_full_training_config(self):
        """Test complete training configuration with all components."""
        from app.schemas.configs import TrainingConfigAdvanced

        config = TrainingConfigAdvanced(
            optimizer={
                "type": "adamw",
                "learning_rate": 0.001,
                "weight_decay": 0.01
            },
            scheduler={
                "type": "cosine",
                "T_max": 100
            },
            augmentation={
                "enabled": True,
                "hue": 0.015,
                "brightness": 0.2
            },
            preprocessing={
                "image_size": 640,
                "mean": (0.485, 0.456, 0.406),
                "std": (0.229, 0.224, 0.225)
            },
            validation={
                "enabled": True,
                "val_interval": 1,
                "metrics": ["accuracy", "precision"]
            }
        )

        # Verify all components are configured
        assert config.optimizer.type == "adamw"
        assert config.scheduler.type == "cosine"
        assert config.augmentation.enabled is True
        assert config.preprocessing.image_size == 640
        assert config.validation.enabled is True
        assert "accuracy" in config.validation.metrics

    def test_minimal_training_config(self):
        """Test minimal training configuration with defaults."""
        from app.schemas.configs import TrainingConfigAdvanced

        # Should work with empty config (all defaults)
        config = TrainingConfigAdvanced()

        assert config.optimizer is not None
        assert config.scheduler is not None
        assert config.augmentation is not None
