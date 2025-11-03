"""
Datasets API endpoints for dataset analysis and management.
"""
from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel
from pathlib import Path
from typing import Optional, Dict, List, Any
import logging
import os
from sqlalchemy.orm import Session

from app.utils.dataset_analyzer import DatasetAnalyzer
from app.db.database import get_db
from app.db.models import Dataset

router = APIRouter()
logger = logging.getLogger(__name__)


class DatasetAnalyzeRequest(BaseModel):
    """Request model for dataset analysis"""
    path: str
    format_hint: Optional[str] = None  # 'imagefolder', 'yolo', 'coco', or None for auto-detect


class DatasetAnalyzeResponse(BaseModel):
    """Response model for dataset analysis"""
    status: str  # 'success' or 'error'
    dataset_info: Optional[Dict[str, Any]] = None
    error_type: Optional[str] = None
    message: Optional[str] = None
    suggestions: Optional[List[str]] = None


def _get_dataset_metadata_from_db(dataset_id: str, db: Session) -> Optional[DatasetAnalyzeResponse]:
    """
    Check if dataset_id exists in database and return metadata.

    Works for all public datasets (including platform samples).
    """
    # Query dataset from database
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id, Dataset.visibility == 'public').first()

    if not dataset:
        return None

    logger.info(f"Found dataset in database: {dataset_id}")

    # Build response from database record
    dataset_info = {
        "format": dataset.format,
        "confidence": 1.0,  # DB datasets are pre-validated
        "task_type": dataset.task_type,
        "structure": {
            "num_classes": dataset.num_classes,
            "num_images": dataset.num_images,
            "classes": dataset.class_names[:10] if dataset.class_names else [],  # First 10 classes
        },
        "statistics": {
            "total_images": dataset.num_images,
            "source": dataset.storage_type,
            "validated": True,
        },
        "samples_per_class": {},  # Not detailed for DB datasets
        "quality_checks": {
            "corrupted_files": [],
            "missing_labels": [],
            "class_imbalance": False,
            "resolution_variance": "uniform",
            "overall_status": "excellent",
        },
        "preview_images": [],  # No preview for DB datasets
    }

    return DatasetAnalyzeResponse(
        status="success",
        dataset_info=dataset_info
    )


@router.post("/analyze", response_model=DatasetAnalyzeResponse)
async def analyze_dataset(request: DatasetAnalyzeRequest, db: Session = Depends(get_db)):
    """
    Analyze a dataset and return structure, statistics, and quality checks.

    - Automatically detects format (ImageFolder, YOLO, COCO)
    - Counts classes and samples
    - Calculates statistics (resolution, size, etc.)
    - Performs quality checks (corrupted files, class imbalance, etc.)
    - Supports public datasets from database (pre-validated metadata)
    """
    try:
        # Check if this is a public dataset in database
        db_dataset = _get_dataset_metadata_from_db(request.path, db)
        if db_dataset:
            logger.info(f"Found public dataset in database: {request.path}")
            return db_dataset

        # Validate path exists
        path = Path(request.path)
        if not path.exists():
            return DatasetAnalyzeResponse(
                status="error",
                error_type="path_not_found",
                message=f"경로를 찾을 수 없습니다: {request.path}",
                suggestions=[
                    "경로가 올바른지 확인하세요",
                    "절대 경로를 사용하세요 (예: C:\\datasets\\imagenet-10)",
                    "네트워크 드라이브의 경우 연결 상태를 확인하세요"
                ]
            )

        if not path.is_dir():
            return DatasetAnalyzeResponse(
                status="error",
                error_type="not_a_directory",
                message=f"경로가 디렉토리가 아닙니다: {request.path}",
                suggestions=[
                    "데이터셋 폴더 경로를 입력하세요",
                    "파일이 아닌 폴더를 선택하세요"
                ]
            )

        # Initialize analyzer
        analyzer = DatasetAnalyzer(path)

        # Detect format
        logger.info(f"Analyzing dataset at: {path}")
        detected_format = analyzer.detect_format(hint=request.format_hint)
        logger.info(f"[DEBUG] detected_format = {detected_format}")

        if detected_format['format'] == 'unknown':
            return DatasetAnalyzeResponse(
                status="error",
                error_type="unknown_format",
                message="데이터셋 형식을 인식할 수 없습니다",
                suggestions=[
                    "지원 형식: ImageFolder, YOLO, COCO",
                    "ImageFolder: dataset/class1/img1.jpg",
                    "YOLO: images/*.jpg + labels/*.txt",
                    "COCO: annotations/*.json + images/"
                ]
            )

        # Collect statistics
        logger.info(f"Collecting statistics for {detected_format['format']} format")
        stats = analyzer.collect_statistics(detected_format['format'])

        # Perform quality checks
        logger.info("Performing quality checks")
        quality_checks = analyzer.check_quality(stats)

        # Build response
        dataset_info = {
            "format": detected_format['format'],
            "confidence": detected_format['confidence'],
            "task_type": detected_format.get('task_type'),
            "structure": stats.get('structure', {}),
            "statistics": stats.get('statistics', {}),
            "samples_per_class": stats.get('samples_per_class', {}),
            "quality_checks": quality_checks,
            "preview_images": stats.get('preview_images', [])
        }

        return DatasetAnalyzeResponse(
            status="success",
            dataset_info=dataset_info
        )

    except PermissionError:
        return DatasetAnalyzeResponse(
            status="error",
            error_type="permission_denied",
            message="경로에 대한 접근 권한이 없습니다",
            suggestions=[
                "폴더의 권한을 확인하세요",
                "관리자 권한으로 실행해보세요"
            ]
        )
    except Exception as e:
        logger.error(f"Error analyzing dataset: {str(e)}", exc_info=True)
        return DatasetAnalyzeResponse(
            status="error",
            error_type="analysis_error",
            message=f"데이터셋 분석 중 오류가 발생했습니다: {str(e)}",
            suggestions=[
                "데이터셋 구조가 올바른지 확인하세요",
                "일부 파일이 손상되었을 수 있습니다"
            ]
        )


class SampleDatasetInfo(BaseModel):
    """Sample dataset information"""
    id: str
    name: str
    description: str
    format: str
    task_type: str
    num_items: int
    size_mb: Optional[float] = None
    source: str
    path: str


class DatasetListItem(BaseModel):
    """Dataset list item"""
    name: str
    path: str
    size_mb: Optional[float] = None
    num_items: Optional[int] = None


class DatasetListResponse(BaseModel):
    """Response model for dataset list"""
    base_path: str
    datasets: List[DatasetListItem]


@router.get("/available", response_model=List[SampleDatasetInfo])
async def list_sample_datasets(
    task_type: Optional[str] = Query(default=None, description="Filter by task type (image_classification, object_detection, etc.)"),
    tags: Optional[str] = Query(default=None, description="Filter by tags (comma-separated)"),
    db: Session = Depends(get_db)
):
    """
    List available public datasets from database.

    Returns all public datasets, including platform-provided samples.
    Platform sample datasets have 'platform-sample' tag.

    Args:
        task_type: Optional filter by task type
        tags: Optional filter by tags (comma-separated, e.g., "platform-sample,coco")
        db: Database session

    Returns:
        List of datasets with metadata
    """
    # Query public datasets
    query = db.query(Dataset).filter(Dataset.visibility == 'public')

    # Filter by task type
    if task_type:
        query = query.filter(Dataset.task_type == task_type)

    # Filter by tags
    if tags:
        tag_list = [t.strip() for t in tags.split(',')]
        # Check if dataset has any of the specified tags
        for tag in tag_list:
            query = query.filter(Dataset.tags.contains([tag]))

    datasets = query.all()

    # Convert to response format
    result = []
    for ds in datasets:
        result.append({
            "id": ds.id,
            "name": ds.name,
            "description": ds.description or f"Dataset for {ds.task_type}",
            "format": ds.format,
            "task_type": ds.task_type,
            "num_items": ds.num_images,
            "size_mb": None,  # Size not stored in DB yet
            "source": ds.storage_type,
            "path": ds.id,  # Use ID as path
        })

    return result


@router.get("/list", response_model=DatasetListResponse)
async def list_datasets(
    base_path: str = Query(default="C:\\datasets", description="Base directory to scan for datasets")
):
    """
    List available datasets in the specified base directory.

    Scans for subdirectories that appear to be datasets based on their structure.
    """
    try:
        base = Path(base_path)

        if not base.exists():
            # Try common dataset locations
            alternative_paths = [
                Path("C:\\datasets"),
                Path("D:\\datasets"),
                Path.home() / "datasets",
                Path.cwd() / "datasets"
            ]

            for alt_path in alternative_paths:
                if alt_path.exists():
                    base = alt_path
                    break
            else:
                # None found, return empty list
                return DatasetListResponse(
                    base_path=str(base),
                    datasets=[]
                )

        if not base.is_dir():
            return DatasetListResponse(
                base_path=str(base),
                datasets=[]
            )

        datasets = []

        # Scan subdirectories
        try:
            for item in base.iterdir():
                if not item.is_dir():
                    continue

                # Skip hidden directories
                if item.name.startswith('.'):
                    continue

                # Calculate directory size and item count
                size_bytes = 0
                num_items = 0

                try:
                    for root, dirs, files in os.walk(item):
                        # Count image files
                        image_files = [f for f in files if f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff'))]
                        num_items += len(image_files)

                        # Calculate size
                        for file in files:
                            try:
                                size_bytes += os.path.getsize(os.path.join(root, file))
                            except:
                                pass
                except:
                    pass

                size_mb = round(size_bytes / (1024 * 1024), 2) if size_bytes > 0 else None

                datasets.append(DatasetListItem(
                    name=item.name,
                    path=str(item),
                    size_mb=size_mb,
                    num_items=num_items if num_items > 0 else None
                ))

        except PermissionError:
            logger.warning(f"Permission denied accessing {base}")

        # Sort by name
        datasets.sort(key=lambda x: x.name.lower())

        return DatasetListResponse(
            base_path=str(base),
            datasets=datasets
        )

    except Exception as e:
        logger.error(f"Error listing datasets: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list datasets: {str(e)}")
