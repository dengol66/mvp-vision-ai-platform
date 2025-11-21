# Backend 리팩토링 계획

**분석 일자**: 2025-11-21
**목적**: Legacy 코드와 SDK 방식 혼재 정리, 코드 품질 향상

---

## 📊 분석 결과 요약

### 🔴 Critical (즉시 처리 필요)

1. **MLflow 사용 패턴 혼재**
   - `get_mlflow_client()` (legacy) ↔ `MLflowService` (new) 혼재
   - `training.py`에서 4곳은 legacy, 2곳은 new 패턴 사용

2. **사용되지 않는 Training Manager 코드**
   - `training_client.py` (115 lines) - 사용되지 않음
   - `training_manager.py` - 사용되지 않음
   - `training_manager_k8s.py` - 사용되지 않음
   - **실제 사용 중**: `training_subprocess.py` 만 사용

3. **Storage 클라이언트 혼재**
   - `storage_utils.py` (5회 사용)
   - `dual_storage.py` (5회 사용)
   - `s3_storage.py` (1회 사용)
   - 3가지 방식이 혼재되어 일관성 부족

---

## 🎯 리팩토링 우선순위

### Priority 1: 사용되지 않는 코드 제거 (Low Risk, High Impact)

**목표**: Dead code 제거로 코드베이스 단순화

#### 1.1 Training Manager 정리
```bash
# 제거 대상
- app/utils/training_client.py (전체)
- app/utils/training_manager.py (전체)
- app/utils/training_manager_k8s.py (전체)

# 유지
- app/utils/training_subprocess.py (현재 사용 중)
```

**이유**:
- 현재 아키텍처는 subprocess 직접 실행 방식으로 확정됨
- Training Service HTTP API 호출 방식은 사용하지 않음
- 3개 파일 총 ~500+ lines 제거 가능

**리스크**: ⭕ 없음 (사용되지 않는 코드)

**예상 시간**: 30분

---

### Priority 2: MLflow 패턴 통일 (Medium Risk, High Impact)

**목표**: 모든 MLflow 호출을 `MLflowService`로 통일

#### 2.1 training.py의 get_mlflow_client() 교체

**현재 상태**:
```python
# training.py - 4곳에서 legacy 패턴 사용
from app.utils.mlflow_client import get_mlflow_client

mlflow_client = get_mlflow_client()
mlflow_run = mlflow_client.get_run_by_job_id(job_id)
```

**변경 후**:
```python
# training.py - MLflowService로 통일
from app.services.mlflow_service import MLflowService

mlflow_service = MLflowService(db)
mlflow_run = mlflow_service.get_run_by_job_id(job_id)
```

**영향 받는 파일**:
- `app/api/training.py` (4 locations)
  - Line ~332: `get_mlflow_client()` in `get_training_job()`
  - Line ~834: `get_mlflow_client()` in `get_mlflow_metrics()`
  - Line ~864: `get_mlflow_client()` in `get_mlflow_summary()`
  - Import 제거

**이유**:
- `MLflowService`는 DB session을 받아 TrainingJob과 연동
- Error handling이 개선됨
- 일관된 서비스 패턴

**리스크**: ⚠️ Medium
- MLflow API 동작 변경 가능성
- 기존 테스트 영향

**완화 방안**:
- 변경 전 기존 동작 단위 테스트 작성
- 변경 후 E2E 테스트로 검증

**예상 시간**: 2시간

---

### Priority 3: Storage 클라이언트 통일 (Low Risk, Medium Impact)

**목표**: Storage 접근 방식을 `dual_storage` 싱글톤으로 통일

#### 3.1 Storage 사용 패턴 분석

**현재 혼재 상황**:
1. `storage_utils.get_storage_client()` - 5회
2. `dual_storage` (싱글톤) - 3회
3. `DualStorageClient` (클래스) - 2회
4. `s3_storage` (싱글톤) - 1회

**통일 방향**:
```python
# 권장: dual_storage 싱글톤 사용
from app.utils.dual_storage import dual_storage

# Internal storage (models, checkpoints, schemas)
await dual_storage.upload_file(
    local_path,
    s3_key,
    bucket_type='internal'
)

# External storage (datasets, inference data)
await dual_storage.upload_file(
    local_path,
    s3_key,
    bucket_type='external'
)
```

**영향 받는 파일**:
- `app/api/datasets.py`
- `app/api/training.py`
- `app/api/export.py`
- `app/api/inference.py`

**리스크**: ⚠️ Low-Medium
- Storage 로직 변경으로 인한 파일 업로드/다운로드 이슈

**완화 방안**:
- 각 API endpoint별로 점진적 변경
- 변경 후 즉시 테스트

**예상 시간**: 3시간

---

### Priority 4: 중복 Callback 로직 리팩토링 (Low Risk, Low Impact)

**목표**: 3개 callback endpoint의 공통 로직 추출

#### 4.1 공통 패턴 식별

**현재 중복**:
```python
# training.py에서 반복되는 패턴
# 1. Job 조회
job = db.query(models.TrainingJob).filter(...).first()
if not job:
    raise HTTPException(404, "Job not found")

# 2. MLflow 처리
if mlflow_service.mlflow_client.available:
    # MLflow 로직
    pass

# 3. WebSocket broadcast
ws_manager = get_websocket_manager()
await ws_manager.broadcast_to_job(job_id, {...})

# 4. DB commit
db.commit()
```

**리팩토링 방향**:
```python
# app/services/training_callback_service.py (new)
class TrainingCallbackService:
    def __init__(self, db: Session):
        self.db = db
        self.mlflow = MLflowService(db)
        self.ws_manager = get_websocket_manager()

    async def handle_progress(self, job_id: int, callback: ProgressCallback):
        job = self._get_job_or_404(job_id)

        # Update DB
        self._update_progress(job, callback)

        # Log to MLflow
        await self._log_mlflow_metrics(job, callback.metrics)

        # Broadcast via WebSocket
        await self._broadcast_progress(job_id, callback)

        self.db.commit()
```

**이유**:
- 3개 callback endpoint의 중복 제거
- 테스트 용이성 향상
- 비즈니스 로직 집중화

**리스크**: ⭕ Low
- 순수 리팩토링 (동작 변경 없음)

**예상 시간**: 4시간

---

## 📋 상세 실행 계획

### Phase 1: Dead Code 제거 (1일)

**Step 1.1**: 사용되지 않는 Training Manager 제거
```bash
# 백업
git checkout -b refactor/remove-unused-training-managers

# 파일 제거
rm app/utils/training_client.py
rm app/utils/training_manager.py
rm app/utils/training_manager_k8s.py

# Import 확인 (없어야 함)
grep -r "training_client\|training_manager" app/ --include="*.py"

# 테스트
pytest tests/ -v
```

**검증**:
- [ ] 모든 테스트 통과
- [ ] Backend 정상 실행
- [ ] Training job 생성/실행 정상 동작

---

### Phase 2: MLflow 패턴 통일 (1일)

**Step 2.1**: training.py의 get_mlflow_client() 교체

```python
# Before: app/api/training.py (line ~332)
mlflow_client = get_mlflow_client()
mlflow_run = mlflow_client.get_run_by_job_id(job_id)

# After:
mlflow_service = MLflowService(db)
mlflow_run = mlflow_service.get_run_by_job_id(job_id)
```

**수정 위치**:
1. `get_training_job()` (line ~332)
2. `get_mlflow_metrics()` (line ~834)
3. `get_mlflow_summary()` (line ~864)
4. Import 문 제거

**검증**:
- [ ] MLflow metrics 조회 정상 동작
- [ ] MLflow summary 정상 동작
- [ ] Training job 상세 조회 정상 동작
- [ ] E2E Observability 테스트 통과

---

### Phase 3: Storage 통일 (2일)

**Step 3.1**: `storage_utils` → `dual_storage` 마이그레이션

**수정 순서** (위험도 낮은 것부터):
1. `app/api/export.py` (export 결과 저장)
2. `app/api/inference.py` (inference 결과 저장)
3. `app/api/datasets.py` (dataset 업로드)
4. `app/api/training.py` (checkpoint 업로드)

**각 API별 검증**:
```bash
# Export API 테스트
pytest tests/e2e/test_export_deploy_e2e.py -v

# Inference API 테스트
pytest tests/e2e/test_inference_e2e.py -v

# Dataset API 테스트 (수동)
curl -X POST .../datasets/upload ...
```

---

### Phase 4: Callback 로직 리팩토링 (2일)

**Step 4.1**: TrainingCallbackService 생성

```python
# app/services/training_callback_service.py
class TrainingCallbackService:
    """통합 Training Callback 처리 서비스"""

    def __init__(self, db: Session):
        self.db = db
        self.mlflow = MLflowService(db)
        self.ws_manager = get_websocket_manager()

    def _get_job_or_404(self, job_id: int) -> models.TrainingJob:
        """Job 조회 (공통)"""
        job = self.db.query(models.TrainingJob).filter(
            models.TrainingJob.id == job_id
        ).first()
        if not job:
            raise HTTPException(404, "Training job not found")
        return job

    async def handle_progress(self, job_id: int, callback: ProgressCallback):
        """Progress callback 처리"""
        # 구현
        pass

    async def handle_completion(self, job_id: int, callback: CompletionCallback):
        """Completion callback 처리"""
        # 구현
        pass

    async def handle_log(self, job_id: int, callback: LogCallback):
        """Log callback 처리"""
        # 구현
        pass
```

**Step 4.2**: training.py endpoint 간소화

```python
# Before (training.py - 50+ lines)
@router.post("/jobs/{job_id}/callback/progress")
async def training_progress_callback(...):
    job = db.query(...).first()
    if not job:
        raise HTTPException(404)

    # Update DB (10 lines)
    # MLflow logging (15 lines)
    # WebSocket broadcast (10 lines)
    # Commit (5 lines)

    return response

# After (training.py - 10 lines)
@router.post("/jobs/{job_id}/callback/progress")
async def training_progress_callback(
    job_id: int,
    callback: training.TrainingProgressCallback,
    db: Session = Depends(get_db)
):
    service = TrainingCallbackService(db)
    return await service.handle_progress(job_id, callback)
```

---

## 🧪 테스트 전략

### 리팩토링 전 체크리스트
- [ ] 현재 코드의 동작을 검증하는 테스트 작성
- [ ] E2E 테스트 모두 통과 확인
- [ ] 브랜치 백업

### 리팩토링 중
- [ ] 각 단계마다 커밋
- [ ] 각 커밋마다 테스트 실행
- [ ] 실패 시 즉시 롤백

### 리팩토링 후 검증
- [ ] 모든 E2E 테스트 통과
- [ ] 성능 저하 없음 확인
- [ ] 메모리 누수 확인

---

## 📅 예상 일정

| Phase | 작업 | 예상 시간 | 위험도 |
|-------|------|----------|--------|
| 1 | Dead Code 제거 | 0.5일 | Low |
| 2 | MLflow 패턴 통일 | 1일 | Medium |
| 3 | Storage 통일 | 2일 | Low-Medium |
| 4 | Callback 리팩토링 | 2일 | Low |
| **Total** | | **5.5일** | |

---

## 💡 추가 개선 사항 (차기 버전)

### 1. Pydantic V2 마이그레이션
**현황**: 83 warnings (Pydantic V1 deprecated)
```
Support for class-based `config` is deprecated, use ConfigDict instead.
```

**작업량**: 중간 (50+ 파일)
**우선순위**: Low (Warning이지만 동작은 정상)

### 2. FastAPI Lifespan 마이그레이션
**현황**: `@app.on_event("startup")` deprecated
```python
# Before
@app.on_event("startup")
async def startup():
    pass

# After
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    yield
    # Shutdown
```

**작업량**: 작음 (2-3 locations)
**우선순위**: Low

### 3. SQLAlchemy 2.0 마이그레이션
**현황**: `declarative_base()` deprecated
```
MovedIn20Warning: The declarative_base() function is now available
as sqlalchemy.orm.declarative_base().
```

**작업량**: 중간
**우선순위**: Medium (SQLAlchemy 2.0이 표준화됨)

---

## 📝 Notes

### 의존성 트리
```
training.py (API)
├── TrainingSubprocessManager (사용 중)
│   └── trainer_sdk.py (각 Trainer에서)
│
├── MLflowService (new, 부분 사용)
└── get_mlflow_client() (legacy, 제거 대상)

storage
├── dual_storage (싱글톤, 권장)
├── storage_utils (legacy?, 제거 검토)
└── s3_storage (특수 용도)
```

### 리팩토링 원칙
1. **점진적 변경**: 한 번에 하나씩
2. **테스트 우선**: 변경 전후 테스트
3. **롤백 가능**: 각 단계마다 커밋
4. **문서화**: 변경 이유와 방법 기록

---

**작성자**: Claude
**검토 필요**: Phase 2 (MLflow) 위험도 재평가
**다음 단계**: Phase 1 실행 승인 대기
