# Backend Data Upload Analysis (Revised)

**분석 일시**: 2025-11-20 15:30 KST
**분석 범위**: Backend가 Trainer SDK로부터 받은 데이터를 설계대로 업로드하는지 검증
**핵심 발견**: **MLflow, S3 업로드 기능이 설계만 되고 구현 안 됨**

---

## Executive Summary

| 데이터 타입 | 설계 의도 | 실제 구현 상태 | Gap |
|------------|-----------|---------------|-----|
| **Logs** | Backend → DB + Loki | ✅ DB 구현, ⚠️ Loki 선택적 | Minor |
| **Metrics** | Backend → DB + MLflow | ✅ DB 구현, ❌ **MLflow 미구현** | **Critical** |
| **Checkpoints** | Backend → S3 (upload) | ❌ **업로드 미구현** (경로만 저장) | **Critical** |
| **Results** | Backend → DB | ✅ 구현됨 | None |
| **WebSocket** | Backend → Frontend | ✅ 구현됨, ❌ 미테스트 | Minor |

---

## 설계 원칙 (THIN_SDK_DESIGN.md)

### Backend-Proxied Observability (Lines 636-802)

```
핵심 원칙: Trainer는 Backend에만 통신하고,
Backend가 모든 Observability 서비스와 Storage를 처리합니다.

Architecture:
Trainer (SDK)                    Backend                     Services
    |                               |                           |
    |-- report_progress() --------->|                           |
    |   {epoch, metrics}            |-- MLflow log_metrics() -->| MLflow
    |                               |-- Prometheus gauge ------>| Prometheus
    |                               |-- WebSocket broadcast --->| Frontend
    |                               |                           |
    |-- upload_checkpoint() ------->|                           |
    |   {local_path}                |-- S3 upload -------------->| MinIO
    |                               |-- Store path ------------>| PostgreSQL
```

**이유**:
- **Trainer 의존성 최소화**: httpx, boto3, yaml만 필요
- **보안**: Trainer가 내부 인프라에 직접 접근 안 함
- **단일 접점**: CALLBACK_URL만 알면 됨
- **DB/Storage 접근은 Backend만**: 설계 원칙

---

## 1. Log Upload Flow

### 1.1 현재 구현 (training_subprocess.py)

```python
async def _save_logs_to_db(self, job_id: int, lines: list[str], log_type: str):
    """Save log lines to database AND Loki (dual storage)."""

    # 1. Database 저장 ✅
    db.bulk_save_objects([
        models.TrainingLog(job_id=job_id, log_type=log_type, content=line)
        for line in lines
    ])

    # 2. Loki 전송 (선택적) ⚠️
    if self.loki_enabled:
        await self._send_logs_to_loki(job_id, lines, log_type)
```

| 기능 | 상태 | 테스트 |
|------|------|--------|
| DB 저장 | ✅ 구현됨 | ✅ E2E 테스트됨 |
| Loki 전송 | ⚠️ 선택적 구현 | ❌ 미테스트 |

---

## 2. Metric Upload Flow - **CRITICAL GAP**

### 2.1 설계 의도

**THIN_SDK_DESIGN.md:670-677**:
```
| SDK Function | Backend가 처리해야 하는 것 |
|report_progress()| MLflow log_metrics, Prometheus gauge, WebSocket, DB 저장 |
```

### 2.2 실제 구현 상태: ❌ **MLflow 업로드 미구현**

**증거 1 - Backend MLflow Client**:
```python
# platform/backend/app/utils/mlflow_client.py

class MLflowClientWrapper:
    # READ-ONLY methods만 존재
    def get_run_by_job_id(...)  # 조회만
    def get_run_metrics(...)     # 조회만
    def get_run_summary(...)     # 조회만

    # ❌ log_metric(), log_param(), log_artifact() 없음!
```

**증거 2 - Grep 검색 결과**:
```bash
$ grep -r "mlflow.log_metric\|mlflow.start_run\|mlflow.log_param" platform/backend
# → No matches found

$ grep -r "mlflow.log_metric\|mlflow.start_run\|mlflow.log_param" platform/trainers
# → No matches found
```

**증거 3 - Callback Handler 분석** (training.py:1532-1640):
```python
@router.post("/jobs/{job_id}/callback/progress")
async def training_progress_callback(job_id, callback):
    # ✅ DB 저장만 구현됨
    metric = models.TrainingMetric(
        job_id=job_id,
        epoch=callback.current_epoch,
        loss=metrics_dict.get('loss'),
        extra_metrics=extra_metrics
    )
    db.add(metric)
    db.commit()

    # ❌ MLflow 업로드 없음!
    # 있어야 하는 코드:
    # with mlflow.start_run(run_id=job.mlflow_run_id):
    #     mlflow.log_metrics(sanitized_metrics, step=epoch)

    # ✅ WebSocket 브로드캐스트는 구현됨
    await ws_manager.broadcast_to_job(job_id, {...})
```

### 2.3 필요한 구현

**training.py에 추가해야 할 코드**:

```python
from app.utils.mlflow_service import MLflowService  # 새로 만들어야 함

@router.post("/jobs/{job_id}/callback/progress")
async def training_progress_callback(job_id, callback):
    job = db.query(models.TrainingJob).get(job_id)

    # 1. DB 저장 (기존)
    metric = models.TrainingMetric(...)
    db.add(metric)
    db.commit()

    # 2. MLflow 업로드 (추가 필요) ❌
    mlflow_service = MLflowService()
    if job.mlflow_run_id or mlflow_service.available:
        if not job.mlflow_run_id:
            # Create MLflow run if not exists
            run_id = mlflow_service.create_run(
                experiment_name="vision-training",
                run_name=f"job-{job_id}",
                tags={"job_id": job_id, "model": job.model_name}
            )
            job.mlflow_run_id = run_id
            db.commit()

        # Log metrics to MLflow
        mlflow_service.log_metrics(
            run_id=job.mlflow_run_id,
            metrics=sanitize_metrics(callback.metrics),
            step=callback.current_epoch
        )

    # 3. Prometheus (선택적) ❌
    # prometheus_client.gauge(...).set(...)

    # 4. WebSocket (기존) ✅
    await ws_manager.broadcast_to_job(job_id, {...})
```

### 2.4 Status Summary

| 기능 | 설계 | 구현 | Gap |
|------|------|------|-----|
| DB 저장 | ✅ 필요 | ✅ 구현됨 | None |
| MLflow log_metrics | ✅ 필요 | ❌ **미구현** | **Critical** |
| Prometheus gauge | ⚠️ 선택적 | ❌ 미구현 | Minor |
| WebSocket broadcast | ✅ 필요 | ✅ 구현됨 | None |

---

## 3. Checkpoint Upload Flow - **CRITICAL GAP**

### 3.1 설계 의도

**THIN_SDK_DESIGN.md:549-579**:
```python
def upload_checkpoint(
    self,
    local_path: str,
    checkpoint_type: str,
    metrics: Optional[Dict] = None
) -> str:
    """
    Upload checkpoint to Internal Storage.

    SDK는 Backend callback을 호출하고,
    Backend가 실제 S3 업로드를 수행.
    """
```

**설계 원칙**: "DB/Storage 접근은 Backend가 담당"

### 3.2 실제 구현 상태: ❌ **S3 업로드 미구현**

**현재 동작**:
1. SDK가 `upload_checkpoint()` 호출
2. ❌ 실제로는 SDK가 직접 S3에 업로드 (설계 위반!)
3. Backend는 경로만 DB에 저장

**증거 - Backend callback handler** (training.py:1601-1603, 1719-1722):
```python
# Progress callback
if callback.best_checkpoint_path:
    job.best_checkpoint_path = callback.best_checkpoint_path  # 경로만 저장

# Completion callback
if callback.best_checkpoint_path:
    job.best_checkpoint_path = callback.best_checkpoint_path
if callback.last_checkpoint_path:
    job.last_checkpoint_path = callback.last_checkpoint_path

# ❌ S3 업로드 코드 없음!
```

### 3.3 필요한 구현

**Option 1: Backend가 S3 업로드 담당 (설계 의도)**

```python
@router.post("/jobs/{job_id}/callback/checkpoint")
async def checkpoint_upload_callback(
    job_id: int,
    file: UploadFile,  # SDK가 파일 전송
    checkpoint_type: str,
    metrics: Optional[Dict] = None
):
    # Backend가 S3 업로드
    storage_client = DualStorageClient()
    s3_uri = storage_client.upload_checkpoint(
        file_content=await file.read(),
        job_id=job_id,
        filename=f"{checkpoint_type}.pt"
    )

    # DB에 경로 저장
    job = db.query(models.TrainingJob).get(job_id)
    if checkpoint_type == "best":
        job.best_checkpoint_path = s3_uri
    elif checkpoint_type == "last":
        job.last_checkpoint_path = s3_uri
    db.commit()

    return {"s3_uri": s3_uri}
```

**Option 2: Presigned URL 방식**

```python
@router.post("/jobs/{job_id}/checkpoint/get-upload-url")
async def get_checkpoint_upload_url(job_id: int, checkpoint_type: str):
    """SDK가 업로드 URL 요청"""
    storage_client = DualStorageClient()
    presigned_url = storage_client.generate_presigned_upload_url(
        bucket=INTERNAL_BUCKET,
        key=f"checkpoints/{job_id}/{checkpoint_type}.pt",
        expiration=3600
    )
    return {"upload_url": presigned_url}

# SDK는 presigned URL로 직접 업로드 (S3 credentials 불필요)
# 업로드 완료 후 Backend에 완료 callback 전송
```

### 3.4 Status Summary

| 기능 | 설계 | 현재 구현 | Gap |
|------|------|----------|-----|
| S3 업로드 | ✅ Backend 담당 | ❌ **SDK가 직접** | **Critical** |
| 경로 저장 | ✅ 필요 | ✅ 구현됨 | None |

---

## 4. Result Storage Flow - ✅ OK

### 4.1 구현 상태

```python
@router.post("/jobs/{job_id}/callback/completion")
async def training_completion_callback(job_id, callback):
    # ✅ Status 업데이트
    job.status = callback.status
    job.completed_at = datetime.utcnow()

    # ✅ Final metrics
    if callback.final_metrics:
        job.final_accuracy = callback.final_metrics.get('accuracy')

    # ✅ Checkpoint paths
    if callback.best_checkpoint_path:
        job.best_checkpoint_path = callback.best_checkpoint_path

    # ✅ MLflow run_id
    if callback.mlflow_run_id:
        job.mlflow_run_id = callback.mlflow_run_id

    # ✅ Error message
    if callback.status == "failed":
        job.error_message = callback.error_message

    db.commit()
```

| 기능 | 상태 | 테스트 |
|------|------|--------|
| Status 업데이트 | ✅ 구현됨 | ✅ E2E 테스트됨 |
| Final metrics 저장 | ✅ 구현됨 | ✅ E2E 테스트됨 |
| Error handling | ✅ 구현됨 | ❌ Failed case 미테스트 |

---

## 5. WebSocket Broadcasting - ✅ OK (테스트 필요)

### 5.1 구현 상태

```python
# Progress broadcast
await ws_manager.broadcast_to_job(job_id, {
    "type": "training_progress",
    "job_id": job_id,
    "status": callback.status,
    "current_epoch": callback.current_epoch,
    "metrics": callback.metrics.dict(),
    ...
})

# Completion broadcast
await ws_manager.broadcast_to_job(job_id, {
    "type": "training_complete",
    "job_id": job_id,
    "final_metrics": callback.final_metrics.dict(),
    ...
})
```

| 기능 | 상태 | 테스트 |
|------|------|--------|
| Progress broadcast | ✅ 구현됨 | ❌ 미테스트 |
| Completion broadcast | ✅ 구현됨 | ❌ 미테스트 |

---

## Critical Gaps Summary

### ❌ 미구현 기능 (설계 위반)

1. **MLflow 메트릭 업로드** (CRITICAL)
   - 설계: Backend가 callback 받아서 MLflow에 log_metrics
   - 현실: ❌ Backend에 MLflow 업로드 코드 없음
   - 영향: 메트릭 추적 불가능

2. **S3 Checkpoint 업로드** (CRITICAL)
   - 설계: Backend가 S3 업로드 담당
   - 현실: ❌ SDK가 직접 S3 접근 (설계 원칙 위반)
   - 영향: Trainer에 S3 credentials 필요 (보안 문제)

3. **Prometheus 메트릭** (MINOR)
   - 설계: Backend가 Prometheus gauge 업데이트
   - 현실: ❌ 미구현
   - 영향: 실시간 모니터링 제한적

### ✅ 정상 동작

1. **Database 저장**: 로그, 메트릭, 결과 모두 DB에 정상 저장
2. **WebSocket**: 실시간 브로드캐스트 구현됨 (테스트 필요)
3. **Loki 로그**: 선택적으로 구현됨

---

## Implementation Recommendations

### High Priority (즉시 구현 필요)

#### 1. MLflow Service 구현

**파일**: `platform/backend/app/services/mlflow_service.py` (신규)

```python
import mlflow
from mlflow.tracking import MlflowClient

class MLflowService:
    def __init__(self):
        self.tracking_uri = os.getenv("MLFLOW_TRACKING_URI")
        self.client = MlflowClient(self.tracking_uri)
        self.available = self._check_availability()

    def create_run(self, experiment_name, run_name, tags):
        """Create MLflow run"""
        experiment = self.client.get_experiment_by_name(experiment_name)
        if not experiment:
            experiment_id = self.client.create_experiment(experiment_name)
        else:
            experiment_id = experiment.experiment_id

        run = self.client.create_run(experiment_id, tags=tags, run_name=run_name)
        return run.info.run_id

    def log_metrics(self, run_id, metrics, step):
        """Log metrics to MLflow"""
        with mlflow.start_run(run_id=run_id):
            mlflow.log_metrics(metrics, step=step)

    def end_run(self, run_id, status="FINISHED"):
        """End MLflow run"""
        self.client.set_terminated(run_id, status)
```

#### 2. Callback Handler 수정

**파일**: `platform/backend/app/api/training.py`

```python
from app.services.mlflow_service import MLflowService

mlflow_service = MLflowService()

@router.post("/jobs/{job_id}/callback/progress")
async def training_progress_callback(job_id, callback):
    # 1. DB 저장 (기존)
    metric = models.TrainingMetric(...)
    db.add(metric)

    # 2. MLflow 업로드 (신규)
    if mlflow_service.available:
        if not job.mlflow_run_id:
            job.mlflow_run_id = mlflow_service.create_run(...)
        mlflow_service.log_metrics(
            run_id=job.mlflow_run_id,
            metrics=callback.metrics,
            step=callback.current_epoch
        )

    db.commit()

    # 3. WebSocket (기존)
    await ws_manager.broadcast_to_job(...)
```

#### 3. S3 Upload Endpoint

**Option A: Direct upload to Backend**
```python
@router.post("/jobs/{job_id}/checkpoint/upload")
async def upload_checkpoint(
    job_id: int,
    file: UploadFile,
    checkpoint_type: str
):
    storage = DualStorageClient()
    s3_uri = storage.upload_checkpoint(
        file_content=await file.read(),
        job_id=job_id,
        filename=f"{checkpoint_type}.pt"
    )

    # Update DB
    job = db.query(models.TrainingJob).get(job_id)
    if checkpoint_type == "best":
        job.best_checkpoint_path = s3_uri
    db.commit()

    return {"s3_uri": s3_uri}
```

**Option B: Presigned URL (권장)**
```python
@router.post("/jobs/{job_id}/checkpoint/get-upload-url")
async def get_checkpoint_upload_url(job_id: int, checkpoint_type: str):
    storage = DualStorageClient()
    presigned_url = storage.generate_presigned_upload_url(
        key=f"checkpoints/{job_id}/{checkpoint_type}.pt"
    )
    return {"upload_url": presigned_url, "s3_uri": f"s3://.../{key}"}

@router.post("/jobs/{job_id}/checkpoint/upload-complete")
async def checkpoint_upload_complete(job_id: int, s3_uri: str, checkpoint_type: str):
    """SDK가 업로드 완료 후 호출"""
    job = db.query(models.TrainingJob).get(job_id)
    if checkpoint_type == "best":
        job.best_checkpoint_path = s3_uri
    db.commit()
```

### Medium Priority

4. **WebSocket E2E 테스트**: Frontend 통합 테스트
5. **Failed Job 테스트**: 에러 케이스 검증
6. **Loki 통합 테스트**: Docker Compose에 Loki 추가

### Low Priority

7. **Prometheus 통합**: Gauge/Counter 메트릭 추가

---

## Test Plan

### Critical Tests (Must Have)

1. **MLflow Upload Test**
   ```python
   def test_training_progress_uploads_to_mlflow():
       # Create job
       job_id = create_training_job()

       # Send progress callback
       response = client.post(f"/jobs/{job_id}/callback/progress", json={
           "current_epoch": 1,
           "metrics": {"loss": 0.5, "mAP50-95": 0.6}
       })

       # Verify MLflow run created
       mlflow_client = MlflowClient()
       run = mlflow_client.search_runs(filter_string=f"tags.job_id = '{job_id}'")[0]
       assert run is not None

       # Verify metrics logged
       metrics = run.data.metrics
       assert metrics["loss"] == 0.5
       assert metrics["mAP50-95"] == 0.6
   ```

2. **S3 Checkpoint Upload Test**
   ```python
   def test_checkpoint_upload_via_backend():
       job_id = create_training_job()

       # Get presigned URL
       response = client.post(f"/jobs/{job_id}/checkpoint/get-upload-url", json={
           "checkpoint_type": "best"
       })
       upload_url = response.json()["upload_url"]
       s3_uri = response.json()["s3_uri"]

       # Upload file to presigned URL
       with open("test_checkpoint.pt", "rb") as f:
           requests.put(upload_url, data=f)

       # Notify Backend
       client.post(f"/jobs/{job_id}/checkpoint/upload-complete", json={
           "s3_uri": s3_uri,
           "checkpoint_type": "best"
       })

       # Verify DB updated
       job = db.query(TrainingJob).get(job_id)
       assert job.best_checkpoint_path == s3_uri
   ```

3. **WebSocket Integration Test**
   ```python
   async def test_websocket_broadcast():
       # Connect WebSocket
       async with websockets.connect(f"ws://localhost:8000/ws/jobs/{job_id}") as ws:
           # Send progress callback
           client.post(f"/jobs/{job_id}/callback/progress", json={...})

           # Receive WebSocket message
           message = await ws.recv()
           data = json.loads(message)

           assert data["type"] == "training_progress"
           assert data["current_epoch"] == 1
   ```

---

## Conclusion

### Current State

| 항목 | 설계 | 구현 | Gap |
|------|------|------|-----|
| **구현 완성도** | 100% | 60% | 40% missing |
| **DB 저장** | 100% | 100% | ✅ Complete |
| **MLflow 업로드** | 100% | 0% | ❌ **Not implemented** |
| **S3 업로드** | 100% | 0% | ❌ **Not implemented** |
| **WebSocket** | 100% | 100% | ⚠️ Needs testing |

### Next Steps

1. **즉시 구현 필요**:
   - MLflowService 클래스 구현
   - Callback handler에 MLflow 업로드 추가
   - S3 checkpoint upload endpoint 추가

2. **테스트 추가**:
   - MLflow upload 통합 테스트
   - S3 upload 통합 테스트
   - WebSocket E2E 테스트

3. **문서 업데이트**:
   - 구현 완료 후 IMPLEMENTATION_TO_DO_LIST.md 업데이트
   - E2E 테스트 가이드 작성

---

**Report Generated**: 2025-11-20 15:30 KST
**Author**: Claude Code
**Related Documents**:
- [THIN_SDK_DESIGN.md](THIN_SDK_DESIGN.md) - 설계 문서
- [TRAINING_SDK_E2E_TEST_REPORT.md](TRAINING_SDK_E2E_TEST_REPORT.md) - E2E 테스트 결과
- [BACKEND_DATA_UPLOAD_ANALYSIS.md](BACKEND_DATA_UPLOAD_ANALYSIS.md) - 이전 분석 (잘못된 결론)
