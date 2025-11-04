"""
Folder upload API endpoint for dataset management.
"""
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from pydantic import BaseModel
from pathlib import Path
from typing import List, Optional, Dict, Any
import logging
import json
import uuid
from datetime import datetime
from sqlalchemy.orm import Session
from collections import defaultdict

from app.utils.r2_storage import r2_storage
from app.db.database import get_db
from app.db.models import Dataset

router = APIRouter()
logger = logging.getLogger(__name__)


class FolderUploadResponse(BaseModel):
    """Response model for folder upload"""
    status: str
    dataset_id: Optional[str] = None
    message: str
    metadata: Optional[Dict[str, Any]] = None


@router.post("/{dataset_id}/upload-images", response_model=FolderUploadResponse)
async def upload_folder(
    dataset_id: str,
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db)
):
    """
    Upload images to an existing dataset.

    Supports both labeled and unlabeled datasets:
    - Unlabeled: Just images in folder structure
    - Labeled: Images + annotation.json file

    The folder structure is preserved in R2 storage.

    Args:
        dataset_id: Existing dataset ID to upload images to
        files: List of files from folder (with relative paths in filename)
        db: Database session

    Returns:
        FolderUploadResponse with upload status and metadata
    """
    try:
        if not files:
            raise HTTPException(status_code=400, detail="No files provided")

        # Find existing dataset
        dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
        if not dataset:
            raise HTTPException(status_code=404, detail=f"Dataset {dataset_id} not found")

        logger.info(f"Received folder upload with {len(files)} files for dataset {dataset_id}")

        # Analyze folder structure and find annotation.json
        annotation_data = None
        image_files = []
        folder_structure = defaultdict(int)  # path -> count

        for file in files:
            # Extract relative path from filename
            # Browser sends webkitRelativePath as filename
            relative_path = file.filename

            if not relative_path:
                logger.warning(f"File without relative path: {file.filename}")
                continue

            # Check if it's annotation.json
            if relative_path.endswith('annotation.json'):
                logger.info(f"Found annotation.json at: {relative_path}")
                try:
                    content = await file.read()
                    annotation_data = json.loads(content.decode('utf-8'))
                    await file.seek(0)  # Reset file pointer for upload
                except Exception as e:
                    logger.error(f"Failed to parse annotation.json: {e}")
                    raise HTTPException(status_code=400, detail="Invalid annotation.json format")

            # Track folder structure
            path_parts = Path(relative_path).parts
            if len(path_parts) > 1:
                # Has subdirectories
                folder_path = str(Path(*path_parts[:-1]))
                folder_structure[folder_path] += 1

            # Check if it's an image
            if file.content_type and file.content_type.startswith('image/'):
                image_files.append({
                    'file': file,
                    'relative_path': relative_path,
                    'content_type': file.content_type
                })

        if not image_files:
            raise HTTPException(status_code=400, detail="No image files found in folder")

        logger.info(f"Found {len(image_files)} image files")
        logger.info(f"Folder structure: {dict(folder_structure)}")

        # Determine if labeled
        labeled = annotation_data is not None
        num_classes = None
        class_names = None
        annotation_path = None

        if labeled:
            # Extract metadata from annotation.json
            annotations = annotation_data.get('annotations', [])
            categories = annotation_data.get('categories', [])

            num_classes = len(categories)
            class_names = [cat.get('name') for cat in categories]

            logger.info(f"Labeled dataset: {num_classes} classes, {len(annotations)} annotations")

        # Upload files to R2
        logger.info(f"Uploading {len(image_files)} files to R2...")
        uploaded_count = 0

        for item in image_files:
            file_obj = item['file']
            relative_path = item['relative_path']
            content_type = item['content_type']

            # R2 path: datasets/{id}/images/{relative_path}
            r2_key = f"datasets/{dataset_id}/images/{relative_path}"

            # Upload to R2
            try:
                await file_obj.seek(0)
                file_bytes = await file_obj.read()

                success = r2_storage.upload_bytes(
                    file_bytes,
                    r2_key,
                    content_type=content_type
                )

                if success:
                    uploaded_count += 1
                else:
                    logger.warning(f"Failed to upload: {relative_path}")
            except Exception as e:
                logger.error(f"Error uploading {relative_path}: {e}")

        logger.info(f"Uploaded {uploaded_count}/{len(image_files)} files")

        # Upload annotation.json if exists
        if annotation_data:
            annotation_r2_key = f"datasets/{dataset_id}/annotation.json"
            annotation_bytes = json.dumps(annotation_data, indent=2).encode('utf-8')

            r2_storage.upload_bytes(
                annotation_bytes,
                annotation_r2_key,
                content_type="application/json"
            )
            annotation_path = annotation_r2_key
            logger.info(f"Uploaded annotation.json to: {annotation_r2_key}")

        # Update existing Dataset record in DB
        dataset.labeled = labeled
        dataset.annotation_path = annotation_path if annotation_data else dataset.annotation_path
        dataset.num_classes = num_classes if num_classes else dataset.num_classes
        dataset.num_images = dataset.num_images + len(image_files)  # Increment image count
        dataset.class_names = class_names if class_names else dataset.class_names
        dataset.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(dataset)

        logger.info(f"Dataset updated in DB: {dataset_id} - added {len(image_files)} images")

        return FolderUploadResponse(
            status="success",
            dataset_id=dataset_id,
            message=f"Uploaded {len(image_files)} images to dataset '{dataset.name}'",
            metadata={
                "dataset_id": dataset_id,
                "dataset_name": dataset.name,
                "labeled": labeled,
                "num_images": dataset.num_images,
                "num_classes": num_classes,
                "class_names": class_names,
                "folder_structure": dict(folder_structure),
                "visibility": dataset.visibility,
                "storage_path": f"datasets/{dataset_id}/"
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading folder: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Upload failed: {str(e)}"
        )
