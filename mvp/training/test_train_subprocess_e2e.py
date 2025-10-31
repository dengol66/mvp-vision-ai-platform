#!/usr/bin/env python3
"""
train.py Subprocess E2E Tests

Tests that train.py can be run as a subprocess (as the backend does in production):
- Command-line argument parsing
- Process execution and exit codes
- Checkpoint generation
- stdout/stderr output capture

This tests the full production workflow: Backend → subprocess → train.py → Adapter → Framework

Usage:
    python test_train_subprocess_e2e.py
"""

import subprocess
import tempfile
import sys
import json
from pathlib import Path
import numpy as np
from PIL import Image


def create_classification_dataset(root_dir):
    """Create a tiny ImageFolder classification dataset."""
    print(f"[SETUP] Creating classification dataset at {root_dir}...")

    for split in ["train", "val"]:
        split_dir = Path(root_dir) / split
        split_dir.mkdir(parents=True, exist_ok=True)

        for class_idx in range(2):
            class_dir = split_dir / f"class_{class_idx}"
            class_dir.mkdir(exist_ok=True)

            num_images = 5 if split == "train" else 2
            for img_idx in range(num_images):
                img_array = np.random.randint(0, 255, (64, 64, 3), dtype=np.uint8)
                img = Image.fromarray(img_array)
                img_path = class_dir / f"img_{img_idx}.jpg"
                img.save(img_path)

    print(f"[OK] Classification dataset created")


def create_detection_dataset(root_dir):
    """Create a tiny YOLO detection dataset."""
    print(f"[SETUP] Creating detection dataset at {root_dir}...")

    root = Path(root_dir)
    images_dir = root / "images"
    labels_dir = root / "labels"

    for split in ["train", "val"]:
        (images_dir / split).mkdir(parents=True, exist_ok=True)
        (labels_dir / split).mkdir(parents=True, exist_ok=True)

        num_images = 5 if split == "train" else 2
        for img_idx in range(num_images):
            img_array = np.random.randint(0, 255, (640, 640, 3), dtype=np.uint8)
            img = Image.fromarray(img_array)
            img_path = images_dir / split / f"img_{img_idx}.jpg"
            img.save(img_path)

            label_path = labels_dir / split / f"img_{img_idx}.txt"
            with open(label_path, "w") as f:
                num_boxes = np.random.randint(1, 3)
                for _ in range(num_boxes):
                    class_id = np.random.randint(0, 2)
                    x = np.random.uniform(0.2, 0.8)
                    y = np.random.uniform(0.2, 0.8)
                    w = np.random.uniform(0.1, 0.3)
                    h = np.random.uniform(0.1, 0.3)
                    f.write(f"{class_id} {x:.6f} {y:.6f} {w:.6f} {h:.6f}\n")

    data_yaml = root / "data.yaml"
    with open(data_yaml, "w") as f:
        f.write(f"path: {root}\n")
        f.write("train: images/train\n")
        f.write("val: images/val\n")
        f.write("nc: 2\n")
        f.write("names: ['class_0', 'class_1']\n")

    print(f"[OK] Detection dataset created")


def create_segmentation_dataset(root_dir):
    """Create a tiny YOLO segmentation dataset."""
    print(f"[SETUP] Creating segmentation dataset at {root_dir}...")

    root = Path(root_dir)
    images_dir = root / "images"
    labels_dir = root / "labels"

    for split in ["train", "val"]:
        (images_dir / split).mkdir(parents=True, exist_ok=True)
        (labels_dir / split).mkdir(parents=True, exist_ok=True)

        num_images = 3 if split == "train" else 2
        for img_idx in range(num_images):
            img_array = np.random.randint(0, 255, (640, 640, 3), dtype=np.uint8)
            img = Image.fromarray(img_array)
            img_path = images_dir / split / f"img_{img_idx}.jpg"
            img.save(img_path)

            label_path = labels_dir / split / f"img_{img_idx}.txt"
            with open(label_path, "w") as f:
                class_id = 0
                # Simple hexagon
                num_points = 6
                center_x = 0.5
                center_y = 0.5
                radius = 0.2

                points = []
                for i in range(num_points):
                    angle = 2 * np.pi * i / num_points
                    x = center_x + radius * np.cos(angle)
                    y = center_y + radius * np.sin(angle)
                    points.append(f"{x:.6f}")
                    points.append(f"{y:.6f}")

                f.write(f"{class_id} " + " ".join(points) + "\n")

    data_yaml = root / "data.yaml"
    with open(data_yaml, "w") as f:
        f.write(f"path: {root}\n")
        f.write("train: images/train\n")
        f.write("val: images/val\n")
        f.write("nc: 2\n")
        f.write("names: ['class_0', 'class_1']\n")

    print(f"[OK] Segmentation dataset created")


def test_subprocess_classification():
    """Test train.py subprocess for TIMM classification."""
    print("\n" + "=" * 80)
    print("TEST 1: train.py Subprocess - TIMM Classification")
    print("=" * 80)

    with tempfile.TemporaryDirectory() as tmpdir:
        dataset_dir = Path(tmpdir) / "dataset"
        output_dir = Path(tmpdir) / "output"
        output_dir.mkdir()

        # Create dataset
        create_classification_dataset(dataset_dir)

        # Build command
        train_script = Path(__file__).parent / "train.py"
        cmd = [
            sys.executable,
            str(train_script),
            "--framework", "timm",
            "--task_type", "image_classification",
            "--model_name", "resnet18",
            "--dataset_path", str(dataset_dir),
            "--dataset_format", "imagefolder",
            "--num_classes", "2",
            "--output_dir", str(output_dir),
            "--epochs", "2",
            "--batch_size", "2",
            "--learning_rate", "0.001",
            "--image_size", "64",
            "--device", "cpu",
            "--job_id", "88888",
            "--pretrained"
        ]

        print(f"\n[SUBPROCESS] Running command:")
        print(f"  {' '.join(cmd)}")

        # Run subprocess
        print(f"\n[SUBPROCESS] Executing train.py...")
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=180
        )

        print(f"\n[SUBPROCESS] Process exited with code: {result.returncode}")

        # Check exit code
        if result.returncode != 0:
            print(f"\n[ERROR] Subprocess failed!")
            print(f"\n[STDERR]:\n{result.stderr}")
            print(f"\n[STDOUT]:\n{result.stdout}")
            return False

        print(f"  ✓ Process completed successfully")

        # Check output contains training logs
        if "Training completed!" not in result.stdout:
            print(f"\n[ERROR] Training completion message not found in stdout")
            print(f"\n[STDOUT]:\n{result.stdout}")
            return False

        print(f"  ✓ Training completion message found")

        # Check checkpoint exists
        checkpoint_files = list(output_dir.glob("**/*.pth"))
        if not checkpoint_files:
            print(f"\n[ERROR] No checkpoint files found in {output_dir}")
            return False

        print(f"  ✓ Found {len(checkpoint_files)} checkpoint(s): {[f.name for f in checkpoint_files]}")

        print(f"\n✅ Classification subprocess test passed!")
        return True


def test_subprocess_detection():
    """Test train.py subprocess for YOLO detection."""
    print("\n" + "=" * 80)
    print("TEST 2: train.py Subprocess - YOLO Detection")
    print("=" * 80)

    with tempfile.TemporaryDirectory() as tmpdir:
        dataset_dir = Path(tmpdir) / "dataset"
        output_dir = Path(tmpdir) / "output"
        output_dir.mkdir()

        # Create dataset
        create_detection_dataset(dataset_dir)

        # Build command
        train_script = Path(__file__).parent / "train.py"
        cmd = [
            sys.executable,
            str(train_script),
            "--framework", "ultralytics",
            "--task_type", "object_detection",
            "--model_name", "yolo11n",
            "--dataset_path", str(dataset_dir),
            "--dataset_format", "yolo",
            "--output_dir", str(output_dir),
            "--epochs", "1",
            "--batch_size", "2",
            "--learning_rate", "0.01",
            "--image_size", "64",
            "--device", "cpu",
            "--job_id", "77777",
            "--pretrained"
        ]

        print(f"\n[SUBPROCESS] Running command:")
        print(f"  {' '.join(cmd)}")

        # Run subprocess
        print(f"\n[SUBPROCESS] Executing train.py...")
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=180
        )

        print(f"\n[SUBPROCESS] Process exited with code: {result.returncode}")

        # Check exit code
        if result.returncode != 0:
            print(f"\n[ERROR] Subprocess failed!")
            print(f"\n[STDERR]:\n{result.stderr}")
            print(f"\n[STDOUT]:\n{result.stdout}")
            return False

        print(f"  ✓ Process completed successfully")

        # Check output contains training logs
        if "Training completed!" not in result.stdout:
            print(f"\n[ERROR] Training completion message not found in stdout")
            print(f"\n[STDOUT]:\n{result.stdout}")
            return False

        print(f"  ✓ Training completion message found")

        # Check checkpoint exists (YOLO saves in job_id subdirectory)
        checkpoint_files = list(output_dir.glob("**/weights/*.pt"))
        if not checkpoint_files:
            print(f"\n[ERROR] No checkpoint files found in {output_dir}")
            return False

        print(f"  ✓ Found {len(checkpoint_files)} checkpoint(s): {[f.name for f in checkpoint_files]}")

        print(f"\n✅ Detection subprocess test passed!")
        return True


def test_subprocess_segmentation():
    """
    Test train.py subprocess for YOLO segmentation.

    This is the critical E2E test that verifies the suffix bug fix!
    Frontend → Backend → subprocess → train.py → Adapter → YOLO
    """
    print("\n" + "=" * 80)
    print("TEST 3: train.py Subprocess - YOLO Segmentation (Bug Catcher)")
    print("=" * 80)
    print("\nThis test verifies the full production workflow with model_name='yolo11n-seg'")

    with tempfile.TemporaryDirectory() as tmpdir:
        dataset_dir = Path(tmpdir) / "dataset"
        output_dir = Path(tmpdir) / "output"
        output_dir.mkdir()

        # Create dataset
        create_segmentation_dataset(dataset_dir)

        # Build command - EXACTLY as backend would send it
        train_script = Path(__file__).parent / "train.py"
        cmd = [
            sys.executable,
            str(train_script),
            "--framework", "ultralytics",
            "--task_type", "instance_segmentation",
            "--model_name", "yolo11n-seg",  # ← The problematic name!
            "--dataset_path", str(dataset_dir),
            "--dataset_format", "yolo",
            "--output_dir", str(output_dir),
            "--epochs", "1",
            "--batch_size", "2",
            "--learning_rate", "0.01",
            "--image_size", "64",
            "--device", "cpu",
            "--job_id", "66666",
            "--pretrained"
        ]

        print(f"\n[SUBPROCESS] Running command:")
        print(f"  {' '.join(cmd)}")
        print(f"\n[CRITICAL] model_name='yolo11n-seg' should load 'yolo11n-seg.pt'")
        print(f"           NOT 'yolo11n-seg-seg.pt' (the bug we fixed)")

        # Run subprocess
        print(f"\n[SUBPROCESS] Executing train.py...")
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=180
        )

        print(f"\n[SUBPROCESS] Process exited with code: {result.returncode}")

        # Check exit code
        if result.returncode != 0:
            print(f"\n[ERROR] Subprocess failed!")

            # Check if it's the suffix bug
            if "yolo11n-seg-seg" in result.stderr or "yolo11n-seg-seg" in result.stdout:
                print(f"\n❌ SUFFIX DUPLICATION BUG DETECTED!")
                print(f"   The bug is NOT fixed in the E2E workflow!")

            print(f"\n[STDERR]:\n{result.stderr}")
            print(f"\n[STDOUT]:\n{result.stdout}")
            return False

        print(f"  ✓ Process completed successfully (no suffix duplication!)")

        # Check output contains training logs
        if "Training completed!" not in result.stdout:
            print(f"\n[ERROR] Training completion message not found in stdout")
            print(f"\n[STDOUT]:\n{result.stdout}")
            return False

        print(f"  ✓ Training completion message found")

        # Check that correct model was loaded
        if "yolo11n-seg-seg" in result.stdout:
            print(f"\n❌ SUFFIX DUPLICATION BUG DETECTED IN STDOUT!")
            return False

        if "yolo11n-seg.pt" in result.stdout:
            print(f"  ✓ Correctly loaded 'yolo11n-seg.pt' (not 'yolo11n-seg-seg.pt')")

        # Check checkpoint exists
        checkpoint_files = list(output_dir.glob("**/weights/*.pt"))
        if not checkpoint_files:
            print(f"\n[ERROR] No checkpoint files found in {output_dir}")
            return False

        print(f"  ✓ Found {len(checkpoint_files)} checkpoint(s): {[f.name for f in checkpoint_files]}")

        print(f"\n✅ Segmentation subprocess test passed!")
        print(f"   Full E2E workflow verified: Frontend → Backend → train.py → Adapter → YOLO")
        return True


def main():
    """Run all subprocess E2E tests."""
    print("\n" + "=" * 80)
    print("train.py SUBPROCESS E2E TESTS")
    print("=" * 80)
    print("\nThese tests verify the full production workflow:")
    print("  Backend API → subprocess → train.py → Adapter → Framework")
    print("\nThis catches integration issues that unit tests miss:")
    print("  - Command-line argument parsing")
    print("  - Process isolation")
    print("  - Checkpoint file generation")
    print("  - stdout/stderr output")

    results = []

    try:
        # Test 1: Classification
        results.append(("Classification Subprocess", test_subprocess_classification()))

        # Test 2: Detection
        results.append(("Detection Subprocess", test_subprocess_detection()))

        # Test 3: Segmentation (the critical one!)
        results.append(("Segmentation Subprocess (Bug Catcher)", test_subprocess_segmentation()))

        # Summary
        print("\n" + "=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)

        all_passed = all(result for _, result in results)

        for test_name, passed in results:
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"  {status} - {test_name}")

        if all_passed:
            print("\n✅ All subprocess E2E tests passed!")
            print("\nThese tests verify:")
            print("  - train.py can be run as subprocess (production workflow)")
            print("  - Command-line arguments are parsed correctly")
            print("  - Adapters are invoked correctly from train.py")
            print("  - Checkpoints are generated")
            print("  - No suffix duplication bug in E2E flow")
            print("\nThis gives us confidence that the production workflow works!")
            return 0
        else:
            print("\n❌ Some tests failed!")
            return 1

    except Exception as e:
        print(f"\n❌ Test execution failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
