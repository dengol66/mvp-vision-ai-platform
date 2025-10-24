"""Ultralytics YOLO adapter for object detection, segmentation, and pose estimation."""

import os
import yaml
from typing import List, Dict, Any
from .base import TrainingAdapter, MetricsResult, TaskType, DatasetFormat


class UltralyticsAdapter(TrainingAdapter):
    """
    Adapter for Ultralytics YOLO models.

    Supported tasks:
    - Object Detection (yolov8n.pt, yolov9e.pt)
    - Instance Segmentation (yolov8n-seg.pt)
    - Pose Estimation (yolov8n-pose.pt)
    - Classification (yolov8n-cls.pt)
    - OBB (yolov8n-obb.pt)
    """

    TASK_SUFFIX_MAP = {
        TaskType.OBJECT_DETECTION: "",
        TaskType.INSTANCE_SEGMENTATION: "-seg",
        TaskType.POSE_ESTIMATION: "-pose",
        TaskType.IMAGE_CLASSIFICATION: "-cls",
    }

    def prepare_model(self):
        """Initialize YOLO model."""
        try:
            from ultralytics import YOLO
        except ImportError:
            raise ImportError(
                "ultralytics not installed. Install with: pip install ultralytics"
            )

        # Determine model path based on task
        suffix = self.TASK_SUFFIX_MAP.get(self.task_type, "")
        model_path = f"{self.model_config.model_name}{suffix}.pt"

        print(f"Loading YOLO model: {model_path}")
        self.model = YOLO(model_path)
        print(f"Model loaded successfully")

    def prepare_dataset(self):
        """Prepare dataset in YOLO format."""
        # YOLO requires data.yaml file
        self.data_yaml = self._create_data_yaml()
        print(f"Dataset config created: {self.data_yaml}")

    def _create_data_yaml(self) -> str:
        """
        Create YOLO format data.yaml configuration file.

        Expected directory structure:
        dataset_path/
        ├── images/
        │   ├── train/
        │   └── val/
        └── labels/
            ├── train/
            └── val/
        """
        # Check if data.yaml already exists
        existing_yaml = os.path.join(self.dataset_config.dataset_path, "data.yaml")
        if os.path.exists(existing_yaml):
            print(f"Using existing data.yaml: {existing_yaml}")
            return existing_yaml

        # Create new data.yaml
        if self.dataset_config.format == DatasetFormat.YOLO:
            # YOLO format - create data.yaml
            data = {
                'path': os.path.abspath(self.dataset_config.dataset_path),
                'train': 'images/train',
                'val': 'images/val',
                'nc': self.model_config.num_classes,
                'names': [f'class_{i}' for i in range(self.model_config.num_classes)]
            }
        elif self.dataset_config.format == DatasetFormat.COCO:
            # COCO format - convert to YOLO format reference
            data = {
                'path': os.path.abspath(self.dataset_config.dataset_path),
                'train': self.dataset_config.train_split,
                'val': self.dataset_config.val_split,
                'nc': self.model_config.num_classes,
                'names': [f'class_{i}' for i in range(self.model_config.num_classes)]
            }
        else:
            raise ValueError(f"Unsupported dataset format for YOLO: {self.dataset_config.format}")

        # Save data.yaml
        yaml_path = os.path.join(self.output_dir, "data.yaml")
        os.makedirs(os.path.dirname(yaml_path), exist_ok=True)

        with open(yaml_path, 'w') as f:
            yaml.dump(data, f, default_flow_style=False)

        print(f"Created YOLO data.yaml with {data['nc']} classes")
        return yaml_path

    def train(self) -> List[MetricsResult]:
        """
        Train using YOLO's built-in training API.

        YOLO handles the full training loop internally,
        so we override the base train() method.
        """
        self.prepare_model()
        self.prepare_dataset()

        print(f"\nStarting YOLO training...")
        print(f"  Model: {self.model_config.model_name}")
        print(f"  Task: {self.task_type.value}")
        print(f"  Epochs: {self.training_config.epochs}")
        print(f"  Batch size: {self.training_config.batch_size}")
        print(f"  Device: {self.training_config.device}")

        # Build YOLO training arguments from advanced config
        train_args = self._build_yolo_train_args()

        # YOLO training
        results = self.model.train(**train_args)

        print(f"\nTraining completed!")
        print(f"Results saved to: {self.output_dir}/job_{self.job_id}")

        # Convert results to MetricsResult format
        metrics_list = self._convert_yolo_results(results)
        return metrics_list

    def _build_yolo_train_args(self) -> Dict[str, Any]:
        """
        Build YOLO training arguments from advanced config.

        Maps our advanced config schema to YOLO's training parameters.
        """
        args = {
            # Basic parameters
            'data': self.data_yaml,
            'epochs': self.training_config.epochs,
            'imgsz': self.model_config.image_size,
            'batch': self.training_config.batch_size,
            'lr0': self.training_config.learning_rate,
            'device': self.training_config.device,
            'project': self.output_dir,
            'name': f'job_{self.job_id}',
            'exist_ok': True,
            'verbose': True,
        }

        adv_config = self.training_config.advanced_config
        if not adv_config:
            return args

        # Optimizer config
        if 'optimizer' in adv_config:
            opt_config = adv_config['optimizer']
            opt_type = opt_config.get('type', 'adam').upper()

            # Map our optimizer types to YOLO optimizer types
            optimizer_map = {
                'ADAM': 'Adam',
                'ADAMW': 'AdamW',
                'SGD': 'SGD',
                'RMSPROP': 'RMSprop',
            }
            args['optimizer'] = optimizer_map.get(opt_type, 'Adam')

            if 'weight_decay' in opt_config:
                args['weight_decay'] = opt_config['weight_decay']
            if 'momentum' in opt_config and opt_type == 'SGD':
                args['momentum'] = opt_config['momentum']

        # Scheduler config
        if 'scheduler' in adv_config:
            sched_config = adv_config['scheduler']
            sched_type = sched_config.get('type', 'none')

            # YOLO has built-in cosine LR scheduler
            if sched_type == 'cosine':
                args['cos_lr'] = True
                args['lrf'] = sched_config.get('eta_min', 0.01)

            # Warmup
            if 'warmup_epochs' in sched_config:
                args['warmup_epochs'] = sched_config['warmup_epochs']

        # Augmentation config
        if 'augmentation' in adv_config:
            aug_config = adv_config['augmentation']

            if aug_config.get('enabled', True):
                # Random flip
                if aug_config.get('random_flip', False):
                    args['fliplr'] = aug_config.get('random_flip_prob', 0.5)

                # Rotation
                if aug_config.get('random_rotation', False):
                    args['degrees'] = aug_config.get('rotation_degrees', 15)

                # Color jitter (HSV augmentation)
                if aug_config.get('color_jitter', False):
                    # YOLO uses HSV augmentation parameters
                    args['hsv_h'] = aug_config.get('hue', 0.015)
                    args['hsv_s'] = aug_config.get('saturation', 0.7)
                    args['hsv_v'] = aug_config.get('brightness', 0.4)

                # Mixup
                if aug_config.get('mixup', False):
                    args['mixup'] = aug_config.get('mixup_alpha', 0.0)

                # YOLO-specific augmentations
                args['mosaic'] = 1.0  # Enable mosaic augmentation by default
                args['copy_paste'] = 0.0  # Disable copy-paste by default

        # Preprocessing config
        if 'preprocessing' in adv_config:
            preprocess_config = adv_config['preprocessing']
            if 'image_size' in preprocess_config:
                args['imgsz'] = preprocess_config['image_size']

        # Validation config
        if 'validation' in adv_config:
            val_config = adv_config['validation']
            # YOLO always validates, but we can control the interval
            # Note: YOLO doesn't have a val_interval parameter in the same way

        # Mixed precision
        if self.training_config.mixed_precision:
            args['amp'] = True

        return args

    def _convert_yolo_results(self, results) -> List[MetricsResult]:
        """
        Convert YOLO training results to standardized MetricsResult.

        YOLO results contain metrics like:
        - train/box_loss, train/cls_loss, train/dfl_loss
        - val/box_loss, val/cls_loss, val/dfl_loss
        - metrics/precision, metrics/recall
        - metrics/mAP50, metrics/mAP50-95
        """
        # YOLO saves results in results.csv
        # For now, return simplified metrics
        # TODO: Parse results.csv for detailed metrics

        metrics_list = []

        # Extract final metrics if available
        if hasattr(results, 'results_dict'):
            final_results = results.results_dict
            metrics = MetricsResult(
                epoch=self.training_config.epochs - 1,
                step=self.training_config.epochs - 1,
                train_loss=final_results.get('train/box_loss', 0.0),
                val_loss=final_results.get('val/box_loss', 0.0),
                metrics={
                    'mAP50': final_results.get('metrics/mAP50(B)', 0.0),
                    'mAP50-95': final_results.get('metrics/mAP50-95(B)', 0.0),
                    'precision': final_results.get('metrics/precision(B)', 0.0),
                    'recall': final_results.get('metrics/recall(B)', 0.0),
                }
            )
            metrics_list.append(metrics)

        return metrics_list

    # These methods are not used since YOLO handles training internally
    # but must be implemented for the interface

    def train_epoch(self, epoch: int) -> MetricsResult:
        """Not used - YOLO handles training internally."""
        pass

    def validate(self, epoch: int) -> MetricsResult:
        """Not used - YOLO handles validation internally."""
        pass

    def save_checkpoint(self, epoch: int, metrics: MetricsResult) -> str:
        """
        YOLO automatically saves checkpoints.

        Returns path to best checkpoint.
        """
        best_weights = os.path.join(self.output_dir, f'job_{self.job_id}', 'weights', 'best.pt')
        last_weights = os.path.join(self.output_dir, f'job_{self.job_id}', 'weights', 'last.pt')

        if os.path.exists(best_weights):
            return best_weights
        elif os.path.exists(last_weights):
            return last_weights
        else:
            return f"{self.output_dir}/job_{self.job_id}/weights/"
