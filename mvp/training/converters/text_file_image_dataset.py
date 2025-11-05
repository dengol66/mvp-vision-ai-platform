"""
Text-file-based Image Classification Dataset.

Similar to torchvision.datasets.ImageFolder but loads from text file splits
instead of directory structure. No file copying required.

Format:
    train.txt:
        images/img1.jpg 0
        images/img2.jpg 1
        ...

    classes.txt:
        cat
        dog
        ...
"""

import os
from pathlib import Path
from typing import Callable, Optional, Tuple, List
from PIL import Image
import torch
from torch.utils.data import Dataset


class TextFileImageDataset(Dataset):
    """
    Image classification dataset loaded from text file splits.

    Compatible with torchvision.datasets.ImageFolder interface.

    Args:
        root: Dataset root directory (contains images/ and splits/)
        split_file: Path to split file (e.g., splits/train.txt)
        classes_file: Path to classes file (e.g., splits/classes.txt)
        transform: Optional transform to apply to images
        target_transform: Optional transform to apply to labels

    Example:
        >>> dataset = TextFileImageDataset(
        ...     root="/path/to/dataset",
        ...     split_file="splits/train.txt",
        ...     classes_file="splits/classes.txt",
        ...     transform=transforms.Compose([...])
        ... )
        >>> image, label = dataset[0]
        >>> print(f"Classes: {dataset.classes}")
    """

    def __init__(
        self,
        root: str,
        split_file: str,
        classes_file: str,
        transform: Optional[Callable] = None,
        target_transform: Optional[Callable] = None
    ):
        self.root = Path(root)
        self.transform = transform
        self.target_transform = target_transform

        # Load class names
        self.classes = self._load_classes(classes_file)
        self.class_to_idx = {cls: idx for idx, cls in enumerate(self.classes)}

        # Load samples (image_path, class_id)
        self.samples = self._load_samples(split_file)

        # For compatibility with ImageFolder
        self.targets = [s[1] for s in self.samples]

    def _load_classes(self, classes_file: str) -> List[str]:
        """Load class names from classes.txt."""
        classes_path = self.root / classes_file if not os.path.isabs(classes_file) else Path(classes_file)

        if not classes_path.exists():
            raise FileNotFoundError(f"Classes file not found: {classes_path}")

        with open(classes_path, 'r', encoding='utf-8') as f:
            classes = [line.strip() for line in f if line.strip()]

        return classes

    def _load_samples(self, split_file: str) -> List[Tuple[str, int]]:
        """
        Load samples from split file.

        Format: image_path class_id
        Example:
            images/img1.jpg 0
            images/img2.jpg 1
        """
        split_path = self.root / split_file if not os.path.isabs(split_file) else Path(split_file)

        if not split_path.exists():
            raise FileNotFoundError(f"Split file not found: {split_path}")

        samples = []
        with open(split_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue

                parts = line.split()
                if len(parts) != 2:
                    raise ValueError(
                        f"Invalid format in {split_path} at line {line_num}: '{line}'\n"
                        f"Expected: <image_path> <class_id>"
                    )

                image_path, class_id = parts
                class_id = int(class_id)

                # Convert relative path to absolute
                if not os.path.isabs(image_path):
                    image_path = self.root / image_path

                # Validate image exists
                if not Path(image_path).exists():
                    print(f"[WARNING] Image not found: {image_path} (skipping)")
                    continue

                samples.append((str(image_path), class_id))

        if not samples:
            raise ValueError(f"No valid samples found in {split_path}")

        return samples

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, index: int) -> Tuple[torch.Tensor, int]:
        """
        Get image and label at index.

        Returns:
            (image, target) where image is a PIL Image or Tensor (after transform)
            and target is the class index
        """
        image_path, target = self.samples[index]

        # Load image
        try:
            image = Image.open(image_path).convert('RGB')
        except Exception as e:
            raise RuntimeError(f"Failed to load image {image_path}: {e}")

        # Apply transforms
        if self.transform is not None:
            image = self.transform(image)

        if self.target_transform is not None:
            target = self.target_transform(target)

        return image, target

    def __repr__(self) -> str:
        head = "Dataset " + self.__class__.__name__
        body = [
            f"Number of datapoints: {len(self)}",
            f"Root location: {self.root}",
            f"Number of classes: {len(self.classes)}",
        ]
        if self.transform is not None:
            body += [repr(self.transform)]
        lines = [head] + [" " * 4 + line for line in body]
        return '\n'.join(lines)


def create_text_file_datasets(
    dataset_root: str,
    train_transform: Optional[Callable] = None,
    val_transform: Optional[Callable] = None,
    splits_dir: str = "splits"
) -> Tuple[TextFileImageDataset, TextFileImageDataset]:
    """
    Create train and val datasets from text file splits.

    Args:
        dataset_root: Path to dataset root (contains images/ and splits/)
        train_transform: Transform for training set
        val_transform: Transform for validation set
        splits_dir: Directory containing split files (relative to dataset_root)

    Returns:
        (train_dataset, val_dataset)

    Example:
        >>> from torchvision import transforms
        >>> train_transform = transforms.Compose([
        ...     transforms.Resize(256),
        ...     transforms.RandomCrop(224),
        ...     transforms.ToTensor(),
        ... ])
        >>> val_transform = transforms.Compose([
        ...     transforms.Resize(256),
        ...     transforms.CenterCrop(224),
        ...     transforms.ToTensor(),
        ... ])
        >>> train_ds, val_ds = create_text_file_datasets(
        ...     dataset_root="/path/to/dataset",
        ...     train_transform=train_transform,
        ...     val_transform=val_transform
        ... )
    """
    train_split = os.path.join(splits_dir, "train.txt")
    val_split = os.path.join(splits_dir, "val.txt")
    classes_file = os.path.join(splits_dir, "classes.txt")

    train_dataset = TextFileImageDataset(
        root=dataset_root,
        split_file=train_split,
        classes_file=classes_file,
        transform=train_transform
    )

    val_dataset = TextFileImageDataset(
        root=dataset_root,
        split_file=val_split,
        classes_file=classes_file,
        transform=val_transform
    )

    return train_dataset, val_dataset


if __name__ == "__main__":
    # Example usage
    import argparse
    from torchvision import transforms

    parser = argparse.ArgumentParser(description="Test TextFileImageDataset")
    parser.add_argument("--dataset-root", required=True, help="Dataset root directory")
    parser.add_argument("--splits-dir", default="splits", help="Splits directory")
    args = parser.parse_args()

    # Define transforms
    transform = transforms.Compose([
        transforms.Resize(256),
        transforms.CenterCrop(224),
        transforms.ToTensor(),
    ])

    # Create datasets
    train_ds, val_ds = create_text_file_datasets(
        dataset_root=args.dataset_root,
        train_transform=transform,
        val_transform=transform,
        splits_dir=args.splits_dir
    )

    print(f"\nTrain Dataset:")
    print(f"  Size: {len(train_ds)}")
    print(f"  Classes: {train_ds.classes}")
    print(f"  Sample 0: image shape = {train_ds[0][0].shape}, label = {train_ds[0][1]}")

    print(f"\nVal Dataset:")
    print(f"  Size: {len(val_ds)}")
    print(f"  Classes: {val_ds.classes}")
    print(f"  Sample 0: image shape = {val_ds[0][0].shape}, label = {val_ds[0][1]}")
