"""
Configuration schemas for different training frameworks.

This module defines configuration schemas without heavy dependencies (torch, etc.)
so they can be imported by the backend API without requiring ML libraries.
"""

from platform_sdk import ConfigSchema, ConfigField


def get_timm_schema() -> ConfigSchema:
    """Return configuration schema for timm models (image classification)."""
    fields = [
        # ========== Optimizer Settings ==========
        ConfigField(
            name="optimizer_type",
            type="select",
            default="adam",
            options=["adam", "adamw", "sgd", "rmsprop"],
            description="Optimizer algorithm",
            group="optimizer",
            required=False
        ),
        ConfigField(
            name="weight_decay",
            type="float",
            default=0.0001,
            min=0.0,
            max=0.1,
            step=0.0001,
            description="L2 regularization (weight decay)",
            group="optimizer",
            advanced=True
        ),
        ConfigField(
            name="momentum",
            type="float",
            default=0.9,
            min=0.0,
            max=1.0,
            step=0.1,
            description="Momentum for SGD optimizer",
            group="optimizer",
            advanced=True
        ),

        # ========== Scheduler Settings ==========
        ConfigField(
            name="scheduler_type",
            type="select",
            default="cosine",
            options=["none", "step", "cosine", "plateau", "exponential"],
            description="Learning rate scheduler",
            group="scheduler",
            required=False
        ),
        ConfigField(
            name="warmup_epochs",
            type="int",
            default=5,
            min=0,
            max=50,
            step=1,
            description="Number of warmup epochs",
            group="scheduler",
            advanced=False
        ),
        ConfigField(
            name="step_size",
            type="int",
            default=30,
            min=1,
            max=100,
            step=1,
            description="Step size for StepLR scheduler",
            group="scheduler",
            advanced=True
        ),
        ConfigField(
            name="gamma",
            type="float",
            default=0.1,
            min=0.01,
            max=1.0,
            step=0.01,
            description="Multiplicative factor of learning rate decay",
            group="scheduler",
            advanced=True
        ),
        ConfigField(
            name="eta_min",
            type="float",
            default=0.000001,
            min=0.0,
            max=0.01,
            step=0.000001,
            description="Minimum learning rate for CosineAnnealingLR",
            group="scheduler",
            advanced=True
        ),

        # ========== Augmentation Settings ==========
        ConfigField(
            name="aug_enabled",
            type="bool",
            default=True,
            description="Enable data augmentation",
            group="augmentation",
            required=False
        ),
        ConfigField(
            name="random_flip",
            type="bool",
            default=True,
            description="Random horizontal flip",
            group="augmentation",
            required=False
        ),
        ConfigField(
            name="random_flip_prob",
            type="float",
            default=0.5,
            min=0.0,
            max=1.0,
            step=0.1,
            description="Probability of random flip",
            group="augmentation",
            advanced=False
        ),
        ConfigField(
            name="random_rotation",
            type="bool",
            default=False,
            description="Random rotation",
            group="augmentation",
            required=False
        ),
        ConfigField(
            name="rotation_degrees",
            type="int",
            default=15,
            min=0,
            max=180,
            step=5,
            description="Maximum rotation degrees",
            group="augmentation",
            advanced=False
        ),
        ConfigField(
            name="random_crop",
            type="bool",
            default=True,
            description="Random crop with resize",
            group="augmentation",
            required=False
        ),
        ConfigField(
            name="color_jitter",
            type="bool",
            default=False,
            description="Random color jitter",
            group="augmentation",
            required=False
        ),
        ConfigField(
            name="brightness",
            type="float",
            default=0.2,
            min=0.0,
            max=1.0,
            step=0.1,
            description="Brightness variation",
            group="augmentation",
            advanced=False
        ),
        ConfigField(
            name="contrast",
            type="float",
            default=0.2,
            min=0.0,
            max=1.0,
            step=0.1,
            description="Contrast variation",
            group="augmentation",
            advanced=False
        ),
        ConfigField(
            name="saturation",
            type="float",
            default=0.2,
            min=0.0,
            max=1.0,
            step=0.1,
            description="Saturation variation",
            group="augmentation",
            advanced=True
        ),
        ConfigField(
            name="hue",
            type="float",
            default=0.1,
            min=0.0,
            max=0.5,
            step=0.05,
            description="Hue variation",
            group="augmentation",
            advanced=True
        ),
        ConfigField(
            name="random_erasing",
            type="bool",
            default=False,
            description="Random erasing augmentation",
            group="augmentation",
            advanced=True
        ),
        ConfigField(
            name="mixup",
            type="bool",
            default=False,
            description="Mixup augmentation (image blending)",
            group="augmentation",
            required=False
        ),
        ConfigField(
            name="mixup_alpha",
            type="float",
            default=0.2,
            min=0.0,
            max=1.0,
            step=0.1,
            description="Mixup alpha parameter",
            group="augmentation",
            advanced=False
        ),
        ConfigField(
            name="cutmix",
            type="bool",
            default=False,
            description="CutMix augmentation (region blending)",
            group="augmentation",
            required=False
        ),
        ConfigField(
            name="cutmix_alpha",
            type="float",
            default=1.0,
            min=0.0,
            max=2.0,
            step=0.1,
            description="CutMix alpha parameter",
            group="augmentation",
            advanced=False
        ),

        # ========== Validation Settings ==========
        ConfigField(
            name="val_interval",
            type="int",
            default=1,
            min=1,
            max=10,
            step=1,
            description="Validate every N epochs",
            group="validation",
            required=False
        ),
    ]

    presets = {
        "easy": {
            "optimizer_type": "adam",
            "scheduler_type": "cosine",
            "aug_enabled": True,
            "random_flip": True,
            "mixup": False,
            "cutmix": False,
        },
        "medium": {
            "optimizer_type": "adamw",
            "weight_decay": 0.0001,
            "scheduler_type": "cosine",
            "warmup_epochs": 5,
            "aug_enabled": True,
            "random_flip": True,
            "color_jitter": True,
            "mixup": True,
            "mixup_alpha": 0.2,
        },
        "advanced": {
            "optimizer_type": "adamw",
            "weight_decay": 0.0001,
            "scheduler_type": "cosine",
            "warmup_epochs": 10,
            "aug_enabled": True,
            "random_flip": True,
            "random_rotation": True,
            "color_jitter": True,
            "mixup": True,
            "mixup_alpha": 0.3,
            "cutmix": True,
            "cutmix_alpha": 1.0,
            "random_erasing": True,
        }
    }

    return ConfigSchema(fields=fields, presets=presets)


def get_ultralytics_schema() -> ConfigSchema:
    """Return configuration schema for YOLO models (object detection, segmentation, pose)."""
    fields = [
        # ========== Optimizer Settings ==========
        ConfigField(
            name="optimizer_type",
            type="select",
            default="Adam",
            options=["Adam", "AdamW", "SGD", "RMSprop"],
            description="Optimizer algorithm",
            group="optimizer",
            required=False
        ),
        ConfigField(
            name="weight_decay",
            type="float",
            default=0.0005,
            min=0.0,
            max=0.01,
            step=0.0001,
            description="Weight decay (L2 regularization)",
            group="optimizer",
            advanced=True
        ),
        ConfigField(
            name="momentum",
            type="float",
            default=0.937,
            min=0.0,
            max=1.0,
            step=0.001,
            description="Momentum for SGD",
            group="optimizer",
            advanced=True
        ),

        # ========== Scheduler Settings ==========
        ConfigField(
            name="cos_lr",
            type="bool",
            default=True,
            description="Use cosine learning rate scheduler",
            group="scheduler",
            required=False
        ),
        ConfigField(
            name="lrf",
            type="float",
            default=0.01,
            min=0.0,
            max=1.0,
            step=0.01,
            description="Final learning rate (lr0 * lrf)",
            group="scheduler",
            advanced=False
        ),
        ConfigField(
            name="warmup_epochs",
            type="int",
            default=3,
            min=0,
            max=20,
            step=1,
            description="Number of warmup epochs",
            group="scheduler",
            advanced=False
        ),
        ConfigField(
            name="warmup_momentum",
            type="float",
            default=0.8,
            min=0.0,
            max=1.0,
            step=0.1,
            description="Initial warmup momentum",
            group="scheduler",
            advanced=True
        ),
        ConfigField(
            name="warmup_bias_lr",
            type="float",
            default=0.1,
            min=0.0,
            max=1.0,
            step=0.01,
            description="Warmup initial bias learning rate",
            group="scheduler",
            advanced=True
        ),

        # ========== Augmentation Settings (YOLO-specific) ==========
        ConfigField(
            name="mosaic",
            type="float",
            default=1.0,
            min=0.0,
            max=1.0,
            step=0.1,
            description="Mosaic augmentation probability (4-image blend)",
            group="augmentation",
            required=False
        ),
        ConfigField(
            name="mixup",
            type="float",
            default=0.0,
            min=0.0,
            max=1.0,
            step=0.05,
            description="Mixup augmentation probability",
            group="augmentation",
            advanced=False
        ),
        ConfigField(
            name="copy_paste",
            type="float",
            default=0.0,
            min=0.0,
            max=1.0,
            step=0.05,
            description="Copy-Paste augmentation probability",
            group="augmentation",
            advanced=True
        ),
        ConfigField(
            name="degrees",
            type="float",
            default=0.0,
            min=0.0,
            max=180.0,
            step=5.0,
            description="Rotation degrees (+/- deg)",
            group="augmentation",
            advanced=False
        ),
        ConfigField(
            name="translate",
            type="float",
            default=0.1,
            min=0.0,
            max=1.0,
            step=0.05,
            description="Translation (+/- fraction)",
            group="augmentation",
            advanced=False
        ),
        ConfigField(
            name="scale",
            type="float",
            default=0.5,
            min=0.0,
            max=2.0,
            step=0.1,
            description="Scaling (+/- gain)",
            group="augmentation",
            advanced=False
        ),
        ConfigField(
            name="shear",
            type="float",
            default=0.0,
            min=0.0,
            max=45.0,
            step=5.0,
            description="Shear degrees (+/- deg)",
            group="augmentation",
            advanced=True
        ),
        ConfigField(
            name="perspective",
            type="float",
            default=0.0,
            min=0.0,
            max=0.001,
            step=0.0001,
            description="Perspective distortion",
            group="augmentation",
            advanced=True
        ),
        ConfigField(
            name="flipud",
            type="float",
            default=0.0,
            min=0.0,
            max=1.0,
            step=0.1,
            description="Vertical flip probability",
            group="augmentation",
            required=False
        ),
        ConfigField(
            name="fliplr",
            type="float",
            default=0.5,
            min=0.0,
            max=1.0,
            step=0.1,
            description="Horizontal flip probability",
            group="augmentation",
            required=False
        ),
        ConfigField(
            name="hsv_h",
            type="float",
            default=0.015,
            min=0.0,
            max=1.0,
            step=0.005,
            description="HSV-Hue augmentation (fraction)",
            group="augmentation",
            advanced=False
        ),
        ConfigField(
            name="hsv_s",
            type="float",
            default=0.7,
            min=0.0,
            max=1.0,
            step=0.1,
            description="HSV-Saturation augmentation (fraction)",
            group="augmentation",
            advanced=False
        ),
        ConfigField(
            name="hsv_v",
            type="float",
            default=0.4,
            min=0.0,
            max=1.0,
            step=0.1,
            description="HSV-Value augmentation (fraction)",
            group="augmentation",
            advanced=False
        ),

        # ========== Optimization Settings ==========
        ConfigField(
            name="amp",
            type="bool",
            default=True,
            description="Automatic Mixed Precision training",
            group="optimization",
            required=False
        ),
        ConfigField(
            name="close_mosaic",
            type="int",
            default=10,
            min=0,
            max=50,
            step=1,
            description="Disable mosaic augmentation for final N epochs",
            group="optimization",
            advanced=True
        ),

        # ========== Validation Settings ==========
        ConfigField(
            name="val_interval",
            type="int",
            default=1,
            min=1,
            max=10,
            step=1,
            description="Validate every N epochs",
            group="validation",
            required=False
        ),
    ]

    presets = {
        "easy": {
            "mosaic": 1.0,
            "fliplr": 0.5,
            "amp": True,
        },
        "medium": {
            "mosaic": 1.0,
            "mixup": 0.1,
            "fliplr": 0.5,
            "hsv_h": 0.015,
            "hsv_s": 0.7,
            "hsv_v": 0.4,
            "degrees": 10,
            "translate": 0.1,
            "scale": 0.5,
            "amp": True,
        },
        "advanced": {
            "mosaic": 1.0,
            "mixup": 0.15,
            "copy_paste": 0.1,
            "fliplr": 0.5,
            "hsv_h": 0.02,
            "hsv_s": 0.8,
            "hsv_v": 0.5,
            "degrees": 15,
            "translate": 0.2,
            "scale": 0.9,
            "shear": 5.0,
            "perspective": 0.0005,
            "amp": True,
            "close_mosaic": 15,
        }
    }

    return ConfigSchema(fields=fields, presets=presets)
