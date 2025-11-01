# Training Issues Guide

## 해결된 문제들

### 1. ✅ faster-coco-eval 모듈 에러 (Fixed)

**문제**:
```
ModuleNotFoundError: No module named 'faster_coco_eval'
```

**원인**:
- Ultralytics가 segmentation validation 시 `faster-coco-eval` 라이브러리 필요
- requirements에 포함되지 않아 런타임 중 자동 설치 시도
- 설치는 성공하지만 현재 실행 중인 프로세스는 재시작 필요

**해결**:
- `requirements/requirements-ultralytics.txt`에 `faster-coco-eval>=1.6.7` 추가
- venv 재생성 또는 수동 설치 필요:
  ```bash
  pip install faster-coco-eval>=1.6.7
  ```

### 2. ✅ MLflow 파라미터 충돌 (Fixed)

**문제**:
```
INVALID_PARAMETER_VALUE: Changing param values is not allowed
- model: 'yolo11n-seg' → 'yolo11n-seg.pt'
- device: 'cuda' → 'cpu'
```

**원인**:
- 우리 Callbacks가 먼저 MLflow에 파라미터 로깅
- YOLO 자체 MLflow 통합이 동일 파라미터를 다른 값으로 재로깅 시도

**해결**:
- `ultralytics_adapter.py`에서 YOLO MLflow 비활성화:
  ```python
  from ultralytics import settings
  settings.update({'mlflow': False})
  ```

---

## 데이터셋 관련 경고 (Action Required)

### 3. ✅ Validation 폴더 누락 (Auto-Fixed)

**이전 경고** (더 이상 발생하지 않음):
```
Warning: No val folder found, using train for validation
```

**자동 해결**:
- Val 폴더가 없으면 자동으로 80/20 train/val split 수행
- 랜덤 시드 고정으로 재현 가능한 split (seed=42)
- **모든 Task Type에서 지원**: Classification, Detection, Segmentation, Pose Estimation

**구현 방식**:
- **Detection/Segmentation/Pose** (Ultralytics): `.txt` 파일로 이미지 경로 참조 (파일 복사 없음)
- **Classification** (TIMM): `torch.utils.data.random_split`으로 데이터셋 분할

**로그 예시**:
```
[_detect_yolo_folders] Val folder not found, auto-splitting train data...
[_auto_split_dataset] Splitting dataset with ratio 0.8
[_auto_split_dataset] Total images: 128
[_auto_split_dataset] Train: 102, Val: 26
[_auto_split_dataset] Created train.txt
[_auto_split_dataset] Created val.txt
[_create_data_yaml] Using txt file format (auto-split dataset)
```

**지원되는 데이터셋 구조**:

**Detection/Segmentation/Pose (YOLO 형식)**:
```
# 구조 1: train/val 폴더 모두 존재 (자동 감지)
C:\datasets\my-dataset\
  images/
    train/  ← 사용
    val/    ← 사용
  labels/
    train/
    val/

# 구조 2: train만 존재 (자동 split)
C:\datasets\my-dataset\
  images/
    train/  ← 80/20 split으로 train.txt, val.txt 생성
  labels/
    train/

# 구조 3: 폴더 없이 images만 (자동 split)
C:\datasets\my-dataset\
  images/  ← 모든 이미지를 80/20 split
  labels/
```

**Classification (ImageFolder 형식)**:
```
# 구조 1: train/val 폴더 모두 존재
C:\datasets\my-dataset\
  train/
    class_0/
      img1.jpg
      img2.jpg
    class_1/
      img3.jpg
  val/
    class_0/
    class_1/

# 구조 2: train만 존재 (자동 split)
C:\datasets\my-dataset\
  train/
    class_0/  ← 80/20 split
    class_1/  ← 80/20 split
```

**수동 Split이 필요한 경우**:
- 특정 이미지를 train/val에 배치하고 싶을 때
- 시간 순서 기반 split이 필요할 때 (예: 시계열 데이터)
- 클래스 균형을 맞추고 싶을 때

→ 이런 경우 수동으로 train/val 폴더를 나눠서 데이터 배치

### 4. ⚠️ 클래스 수 불일치

**설정**:
- Frontend 설정: `num_classes: 69`
- 실제 데이터: 71개 unique class IDs
- YOLO 설정: `nc: 80` (COCO 표준)

**문제**:
- COCO 데이터셋은 80개 클래스가 맞음 (0-79)
- 일부 클래스 ID가 누락됨 (예: 10, 12, 18, 19, ...)
- 모델은 80개 클래스로 학습되어야 함

**권장 해결**:
1. **COCO 데이터셋 사용 시**: `num_classes`를 80으로 설정
2. **커스텀 데이터셋**: 실제 클래스 수에 맞게 설정
3. **자동 감지**: 코드가 자동으로 max class ID 기반 nc 설정 (현재 동작 중)

---

## 무시 가능한 경고

### 5. ℹ️ albumentations 호환성 경고

**경고**:
```
albumentations: ImageCompression.__init__() got an unexpected keyword argument 'quality_range'
```

**설명**:
- albumentations 라이브러리 버전 호환성 문제
- 학습에는 영향 없음
- 필요시 albumentations 버전 업데이트

---

## 재학습 체크리스트

다음 순서로 문제를 해결하고 재학습하세요:

### Step 1: 필수 패키지 설치
```bash
cd mvp/training
pip install faster-coco-eval>=1.6.7
```

### Step 2: 데이터셋 검증
```bash
# 1. Validation 폴더 확인
ls C:\datasets\seg-coco128\images\
ls C:\datasets\seg-coco128\labels\

# 2. data.yaml 확인
cat C:\datasets\seg-coco128\data.yaml
```

### Step 3: 설정 조정
- COCO 데이터셋이면: `num_classes=80`
- Validation 폴더가 없으면: 데이터 분할 또는 `val=train`으로 명시

### Step 4: 재학습 실행
```bash
# 백엔드 API를 통해 재학습 시작
# 또는 직접 실행:
python train.py \
  --framework ultralytics \
  --task_type instance_segmentation \
  --model_name yolo11n-seg \
  --dataset_path C:\datasets\seg-coco128 \
  --dataset_format yolo \
  --epochs 5 \
  --batch_size 32 \
  --device cuda \
  --job_id 27
```

### Step 5: 로그 확인
성공 시 표시되어야 할 메시지:
- ✅ `[YOLO] Disabled YOLO's built-in MLflow (using custom Callbacks)`
- ✅ `MLflow: logging run_id(...)` (에러 없이)
- ✅ `Epoch 1/5`, `Epoch 2/5`, ... 정상 진행
- ✅ `Training completed!`

---

## 문제 발생 시

### 여전히 faster-coco-eval 에러가 나면:
```bash
# 1. 설치 확인
pip show faster-coco-eval

# 2. 재설치
pip uninstall faster-coco-eval
pip install faster-coco-eval>=1.6.7

# 3. 환경 재시작
# - 백엔드 재시작
# - Python 인터프리터 재시작
```

### MLflow 에러가 여전히 나면:
```bash
# 1. MLflow 실행 확인
# Run ID가 중복되었을 수 있음
mlflow server --host localhost --port 5000

# 2. 새 job_id로 재학습
# (다른 MLflow run 생성)
```

### Validation 폴더를 만들 수 없다면:
```python
# data.yaml 임시 수정
val: images/train2017  # train 데이터 재사용 (비권장)
```

---

## 예상 학습 시간

- YOLO11n-seg + COCO128 (128 images)
- GPU: NVIDIA (CUDA)
- Batch Size: 32
- Epochs: 5

**예상**: 약 5-10분

**실제 로그 기준**:
- Epoch 1: 약 1분 44초 (로그 기준)
- Total: 약 5-10분 예상

---

## 성공 지표

학습이 성공적으로 완료되면:

1. **체크포인트 생성**:
   ```
   C:\Users\flyto\...\outputs\job_20251031_131654\job_26\weights\
     ├── best.pt
     └── last.pt
   ```

2. **MLflow 로깅**:
   - Run이 정상 생성됨
   - 메트릭이 epoch마다 기록됨

3. **Validation 결과**:
   - mAP50, mAP50-95 지표 출력
   - Precision, Recall 값 표시

4. **출력 파일**:
   - `labels.jpg` (클래스 분포)
   - `predictions.json` (예측 결과)
   - `results.csv` (메트릭 히스토리)

---

## 추가 참고

- YOLO 공식 문서: https://docs.ultralytics.com
- COCO 데이터셋: https://cocodataset.org
- MLflow 문서: https://mlflow.org/docs/latest
