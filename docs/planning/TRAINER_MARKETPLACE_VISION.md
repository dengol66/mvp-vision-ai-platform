# Trainer Marketplace Vision

**Status**: 📋 Planned (Future Enhancement)
**Target**: Phase 4+
**Created**: 2025-01-17

## Overview

Vision AI Training Platform의 궁극적인 목표는 **자동화된 Trainer 등록 및 검증 시스템**을 통해 개발자가 UI를 통해 Custom Trainer를 업로드하면 자동으로 검증, 등록, 배포되어 즉시 사용 가능하도록 하는 것입니다.

**핵심 컨셉**: "Plugin System" 또는 "Trainer Marketplace"
- 개발자: Trainer 코드 업로드
- 플랫폼: 자동 검증 + 등록
- 사용자: 즉시 학습 가능

## Current State (Phase 3.6 완료)

### ✅ 구현된 기반 시스템

**Convention-Based Architecture**:
```
platform/trainers/{framework}/
├── train.py                    # Training CLI
├── config_schema.py            # Config schema generator
├── capabilities.json           # Model registry (static)
├── export.py                   # Export CLI
└── Dockerfile                  # Isolated container
```

**Automated Upload (GitHub Actions)**:
```
1. Developer commits capabilities.json
2. GitHub Actions validates + uploads to R2
3. Backend dynamically discovers from R2
4. Frontend automatically shows new models
```

**Dynamic Framework Discovery**:
- Backend: `discover_available_frameworks()` - R2에서 동적 조회
- Frontend: 자동 갱신 (redeployment 불필요)

### 🚧 현재 제약사항

**Manual Process**:
1. 개발자가 직접 `platform/trainers/{framework}/` 폴더 생성
2. 수동으로 capabilities.json 작성 (오타/누락 가능)
3. Git commit + PR 생성
4. GitHub Actions 검증 후 merge
5. R2 업로드 후 사용 가능

**Validation Gaps**:
- capabilities.json의 모델이 실제로 로드 가능한지 검증 안 됨
- Training test 없음 (실제 학습 가능한지 미검증)
- Inference test 없음 (export/inference 가능한지 미검증)
- Security scan 없음 (악성 코드 체크 없음)

## Future Vision

### Phase 2: Trainer Validation Infrastructure (Next)

**목표**: 자동화된 검증 시스템 구축

#### 2.1 Validator Framework

각 trainer에 validation 스크립트 추가:

```python
# platform/trainers/{framework}/validate_capabilities.py

class CapabilityValidator:
    def validate_model_exists(self, model_name: str) -> bool:
        """모델이 실제로 로드 가능한지 검증"""
        raise NotImplementedError

    def list_available_models(self) -> List[str]:
        """프레임워크에서 지원하는 전체 모델 목록"""
        raise NotImplementedError

# Ultralytics 예시
class UltralyticsValidator(CapabilityValidator):
    def validate_model_exists(self, model_name: str) -> bool:
        try:
            YOLO(f"{model_name}.pt")
            return True
        except:
            return False
```

#### 2.2 Upload Script Integration

```python
# platform/scripts/upload_model_capabilities.py

def validate_capabilities(capabilities: Dict, framework: str) -> bool:
    """capabilities.json의 모든 모델이 실제로 존재하는지 검증"""

    # Dynamic import of framework validator
    validator = import_validator(framework)

    for model in capabilities["models"]:
        if not validator.validate_model_exists(model["model_name"]):
            raise ValueError(f"Model {model['model_name']} not found")

    return True

# Usage in main()
capabilities = load_capabilities(framework, trainers_dir)
validate_capabilities(capabilities, framework)  # ← 검증 추가
upload_capabilities_to_s3(...)
```

#### 2.3 Automated Testing

```python
# platform/trainers/{framework}/test_trainer.py

def test_training_1_epoch(sample_dataset):
    """1 epoch 학습이 정상 완료되는지 테스트"""
    result = subprocess.run([
        "python", "train.py",
        "--job-id", "test-123",
        "--model-name", "yolo11n",
        "--dataset-s3-uri", sample_dataset,
        "--config", '{"epochs": 1, "batch": 2}'
    ])
    assert result.returncode == 0

def test_inference(trained_checkpoint):
    """학습된 모델로 inference가 가능한지 테스트"""
    result = subprocess.run([
        "python", "predict.py",
        "--checkpoint", trained_checkpoint,
        "--image", "test.jpg"
    ])
    assert result.returncode == 0
```

#### 2.4 GitHub Actions Enhancement

```yaml
# .github/workflows/validate-trainer.yml

- name: Validate capabilities models exist
  run: |
    cd platform/trainers/${{ matrix.framework }}
    python validate_capabilities.py

- name: Run training test (1 epoch)
  run: |
    docker build -t trainer-test .
    docker run trainer-test pytest test_trainer.py::test_training_1_epoch

- name: Run inference test
  run: |
    docker run trainer-test pytest test_trainer.py::test_inference
```

**Phase 2 완료 기준**:
- [ ] All trainers have `validate_capabilities.py`
- [ ] Upload script validates models before upload
- [ ] GitHub Actions runs training/inference tests
- [ ] 100% test coverage for core trainers

---

### Phase 3: Trainer Upload API & UI

**목표**: UI를 통한 Trainer 업로드 및 자동 검증

#### 3.1 Backend API

```python
# platform/backend/app/api/trainers.py

@router.post("/trainers/upload")
async def upload_trainer(
    file: UploadFile,
    metadata: TrainerMetadata,
    current_user: User = Depends(get_current_user)
):
    """
    Upload custom trainer package.

    File formats:
    - trainer.zip (containing train.py, config_schema.py, etc.)
    - Dockerfile + requirements.txt

    Returns:
        validation_job_id for tracking progress
    """
    # 1. Extract and validate file structure
    trainer_dir = extract_trainer(file)
    validate_trainer_structure(trainer_dir)

    # 2. Create validation job (Kubernetes Job)
    validation_job = await create_validation_job(
        trainer_dir=trainer_dir,
        metadata=metadata,
        user_id=current_user.id
    )

    return {
        "validation_job_id": validation_job.id,
        "status": "validating"
    }

@router.get("/trainers/validation/{job_id}")
async def get_validation_status(job_id: str):
    """Get real-time validation progress via WebSocket or polling"""
    job = await get_validation_job(job_id)

    return {
        "status": job.status,  # validating, passed, failed
        "current_step": job.current_step,
        "steps_completed": job.steps_completed,
        "steps_total": 6,
        "results": {
            "structure": {"passed": True, "issues": []},
            "config_schema": {"passed": True, "schema": {...}},
            "capabilities": {"passed": True, "models_validated": 12},
            "training_test": {"passed": True, "duration": 45.3},
            "inference_test": {"passed": True, "output_valid": True},
            "security": {"passed": True, "threats": []}
        }
    }
```

#### 3.2 Validation Service

```python
# platform/backend/app/services/trainer_validator.py

class TrainerValidator:
    async def validate_trainer(self, trainer_path: Path) -> ValidationResult:
        """
        Run comprehensive validation pipeline.

        Steps:
        1. Structure validation (필수 파일 존재 확인)
        2. Config schema validation (schema 생성 및 검증)
        3. Capabilities validation (모델 목록 검증)
        4. Training test (1 epoch 학습 테스트)
        5. Inference test (inference 가능 여부)
        6. Security scan (악성 코드, secrets 스캔)
        """
        results = {}

        # Step 1: Structure
        results['structure'] = self.validate_structure(trainer_path)
        if not results['structure']['passed']:
            return ValidationResult(passed=False, results=results)

        # Step 2: Config Schema
        results['config_schema'] = self.validate_config_schema(trainer_path)

        # Step 3: Capabilities
        results['capabilities'] = self.validate_capabilities(trainer_path)

        # Step 4: Training Test (K8s Job with 5min timeout)
        results['training_test'] = await self.run_training_test(trainer_path)

        # Step 5: Inference Test
        results['inference_test'] = await self.run_inference_test(trainer_path)

        # Step 6: Security Scan
        results['security'] = self.scan_security(trainer_path)

        return ValidationResult(
            passed=all(r['passed'] for r in results.values()),
            results=results
        )

    async def run_training_test(self, trainer_path: Path) -> dict:
        """
        Run 1-epoch training on sample dataset.

        Uses Kubernetes Job with:
        - Sample dataset (COCO val2017 subset, 100 images)
        - Config: {epochs: 1, batch: 2}
        - Timeout: 5 minutes
        """
        # 1. Create sample dataset
        sample_dataset_uri = await self.create_sample_dataset()

        # 2. Build Docker image
        image_tag = f"trainer-validation:{uuid.uuid4()}"
        await self.build_docker_image(trainer_path, image_tag)

        # 3. Run K8s Job
        job_result = await self.run_k8s_job(
            image=image_tag,
            command=[
                "python", "train.py",
                "--job-id", "validation-test",
                "--model-name", "test-model",
                "--dataset-s3-uri", sample_dataset_uri,
                "--config", '{"epochs": 1, "batch": 2}'
            ],
            timeout=300
        )

        return {
            "passed": job_result.exit_code == 0,
            "duration": job_result.duration,
            "logs": job_result.logs,
            "checkpoint_created": job_result.checkpoint_exists,
            "metrics": job_result.metrics
        }

    def scan_security(self, trainer_path: Path) -> dict:
        """
        Security scan:
        - Malware detection (ClamAV)
        - Secrets scanning (detect-secrets)
        - Dependency vulnerability check (safety)
        """
        issues = []

        # Scan for secrets
        secrets = self.scan_secrets(trainer_path)
        if secrets:
            issues.append(f"Found {len(secrets)} potential secrets")

        # Scan dependencies
        vulnerabilities = self.scan_dependencies(trainer_path)
        if vulnerabilities:
            issues.append(f"Found {len(vulnerabilities)} vulnerabilities")

        return {
            "passed": len(issues) == 0,
            "issues": issues
        }
```

#### 3.3 Auto Registration

검증 통과 시 자동 등록:

```python
async def register_trainer(validation_job: ValidationJob):
    """
    Validation passed → Auto register trainer.

    Steps:
    1. Create platform/trainers/{framework}/ directory
    2. Upload config schema to R2
    3. Upload capabilities to R2
    4. Build & push Docker image to registry
    5. Update trainer registry DB
    6. Notify user
    """
    framework = validation_job.metadata.framework_name

    # 1. Create trainer directory (Git automation or direct filesystem)
    trainer_dir = create_trainer_directory(framework)
    copy_validated_files(validation_job.trainer_path, trainer_dir)

    # 2. Upload to R2
    await upload_config_schema(framework)
    await upload_capabilities(framework)

    # 3. Build & push Docker image
    image_tag = f"trainer-{framework}:latest"
    await build_and_push_image(trainer_dir, image_tag)

    # 4. Update DB
    await db.trainers.insert({
        "framework": framework,
        "version": "1.0.0",
        "image": image_tag,
        "uploaded_by": validation_job.user_id,
        "status": "active",
        "created_at": datetime.now()
    })

    # 5. Notify user
    await notify_user(validation_job.user_id, {
        "type": "trainer_registered",
        "framework": framework,
        "message": f"Trainer '{framework}' is now available for training!"
    })
```

#### 3.4 Frontend UI

```tsx
// platform/frontend/components/trainer/TrainerUploadModal.tsx

export function TrainerUploadModal() {
  const [file, setFile] = useState<File | null>(null)
  const [metadata, setMetadata] = useState<TrainerMetadata>({
    framework_name: '',
    display_name: '',
    description: '',
    version: '1.0.0'
  })
  const [validationJobId, setValidationJobId] = useState<string | null>(null)
  const [validationStatus, setValidationStatus] = useState<ValidationStatus | null>(null)

  const handleUpload = async () => {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('metadata', JSON.stringify(metadata))

    const { validation_job_id } = await uploadTrainer(formData)
    setValidationJobId(validation_job_id)
  }

  useEffect(() => {
    if (!validationJobId) return

    // Poll validation status every 2 seconds
    const interval = setInterval(async () => {
      const status = await getValidationStatus(validationJobId)
      setValidationStatus(status)

      if (status.status !== 'validating') {
        clearInterval(interval)
      }
    }, 2000)

    return () => clearInterval(interval)
  }, [validationJobId])

  return (
    <Modal title="Upload Custom Trainer">
      {/* Step 1: Upload File */}
      <UploadZone
        accept=".zip"
        onDrop={setFile}
        description="Upload trainer.zip containing train.py, config_schema.py, capabilities.json"
      />

      {/* Step 2: Metadata */}
      <MetadataForm
        value={metadata}
        onChange={setMetadata}
      />

      {/* Step 3: Validation Progress */}
      {validationStatus && (
        <ValidationProgress
          status={validationStatus}
          steps={[
            'Structure validation',
            'Config schema validation',
            'Capabilities validation',
            'Training test (1 epoch)',
            'Inference test',
            'Security scan'
          ]}
        />
      )}

      {/* Step 4: Results */}
      {validationStatus?.status === 'passed' && (
        <SuccessMessage>
          <CheckCircle className="text-green-500" />
          <div>
            <h3>Trainer Registered Successfully!</h3>
            <p>Your trainer '{metadata.framework_name}' is now available for training.</p>
            <Link href="/training/new">Start Training →</Link>
          </div>
        </SuccessMessage>
      )}

      {validationStatus?.status === 'failed' && (
        <ErrorMessage results={validationStatus.results} />
      )}
    </Modal>
  )
}

// Validation Progress Component
function ValidationProgress({ status, steps }) {
  return (
    <div className="space-y-4">
      {steps.map((step, idx) => {
        const stepStatus = status.steps_completed > idx ? 'completed' :
                          status.steps_completed === idx ? 'running' : 'pending'

        return (
          <div key={idx} className="flex items-center gap-3">
            {stepStatus === 'completed' && <CheckCircle className="text-green-500" />}
            {stepStatus === 'running' && <Loader className="animate-spin text-blue-500" />}
            {stepStatus === 'pending' && <Circle className="text-gray-300" />}

            <span className={stepStatus === 'running' ? 'font-semibold' : ''}>
              {step}
            </span>

            {status.results?.[step] && (
              <span className="text-sm text-gray-500">
                ({status.results[step].duration}s)
              </span>
            )}
          </div>
        )
      })}
    </div>
  )
}
```

**Phase 3 완료 기준**:
- [ ] Trainer upload API implemented
- [ ] Validation service with K8s integration
- [ ] Auto registration after validation
- [ ] Frontend upload UI with real-time progress
- [ ] E2E test: Upload → Validate → Register → Train

---

### Phase 4: Trainer Marketplace

**목표**: Community-driven trainer ecosystem

#### 4.1 Features

**Trainer Versioning**:
```json
{
  "framework": "custom-yolo-turbo",
  "versions": [
    {
      "version": "1.0.0",
      "uploaded_at": "2025-01-17",
      "docker_image": "trainer-custom-yolo-turbo:1.0.0",
      "changelog": "Initial release"
    },
    {
      "version": "1.1.0",
      "uploaded_at": "2025-02-01",
      "docker_image": "trainer-custom-yolo-turbo:1.1.0",
      "changelog": "Added new augmentation support"
    }
  ]
}
```

**Trainer Categories**:
- Official (Platform team verified)
- Community (User-contributed)
- Enterprise (Paid/licensed trainers)

**Ratings & Reviews**:
```tsx
<TrainerCard framework="custom-yolo-turbo">
  <Rating value={4.5} reviews={128} />
  <UsageStats downloads={1.2k} trainings={3.5k} />
  <Reviews>
    <Review user="user123" rating={5}>
      "10x faster than standard YOLO!"
    </Review>
  </Reviews>
</TrainerCard>
```

**Usage Analytics**:
- Download count
- Training job count
- Success rate
- Average training time
- User satisfaction score

#### 4.2 Marketplace UI

```tsx
// platform/frontend/pages/marketplace/trainers.tsx

export default function TrainerMarketplace() {
  const [filter, setFilter] = useState({
    category: 'all',  // official, community, enterprise
    task: 'all',      // detection, segmentation, classification
    sort: 'popular'   // popular, newest, rating
  })

  return (
    <Page title="Trainer Marketplace">
      <Filters value={filter} onChange={setFilter} />

      <TrainerGrid>
        {trainers.map(trainer => (
          <TrainerCard
            key={trainer.id}
            trainer={trainer}
            onInstall={() => installTrainer(trainer.id)}
          />
        ))}
      </TrainerGrid>
    </Page>
  )
}
```

**Phase 4 완료 기준**:
- [ ] Trainer versioning system
- [ ] Community upload & review
- [ ] Rating & review system
- [ ] Usage analytics dashboard
- [ ] Marketplace UI

---

## Technical Requirements

### Infrastructure

**Kubernetes Resources**:
- Validation Jobs: 1 CPU, 2Gi RAM, 5min timeout
- Training Tests: 1 GPU (optional), 4Gi RAM, 5min timeout
- Image Registry: Docker Registry or Harbor

**Storage**:
- R2/S3: Config schemas, capabilities
- Docker Registry: Trainer images
- PostgreSQL: Trainer metadata, versions, reviews

**Security**:
- ClamAV: Malware scanning
- detect-secrets: Secret scanning
- safety: Dependency vulnerability check
- Sandboxed execution for validation

### Convention Requirements

모든 custom trainer는 다음 규칙을 따라야 함:

**Required Files**:
```
trainers/{framework}/
├── train.py                    # REQUIRED: Training CLI
├── config_schema.py            # REQUIRED: Config schema generator
├── capabilities.json           # REQUIRED: Model registry
├── export.py                   # OPTIONAL: Export CLI
├── predict.py                  # OPTIONAL: Inference CLI
├── validate_capabilities.py    # REQUIRED: Model validator
├── requirements.txt            # REQUIRED: Dependencies
├── Dockerfile                  # REQUIRED: Container definition
└── README.md                   # RECOMMENDED: Documentation
```

**CLI Interface**:
```bash
# Training (REQUIRED)
python train.py \
  --job-id {id} \
  --model-name {model} \
  --dataset-s3-uri {uri} \
  --callback-url {url} \
  --config '{json}'

# Export (OPTIONAL)
python export.py \
  --checkpoint {path} \
  --format {onnx|tensorrt|...} \
  --output {path}

# Inference (OPTIONAL)
python predict.py \
  --checkpoint {path} \
  --image {path} \
  --output {path}
```

**Exit Codes**:
- 0: Success
- 1: Training/inference failure
- 2: Callback failure

---

## Migration Path

### From Current (Phase 3.6) to Phase 2

**Step 1**: Add validators to existing trainers
```bash
# For each trainer
cd platform/trainers/ultralytics
touch validate_capabilities.py
# Implement UltralyticsValidator
```

**Step 2**: Update upload script
```python
# platform/scripts/upload_model_capabilities.py
# Add validation before upload
```

**Step 3**: Update GitHub Actions
```yaml
# Add validation steps to workflow
```

**Estimated Effort**: 2-3 weeks

### From Phase 2 to Phase 3

**Step 1**: Implement validation service
```bash
cd platform/backend/app/services
touch trainer_validator.py
```

**Step 2**: Implement upload API
```bash
cd platform/backend/app/api
touch trainers.py
```

**Step 3**: Implement frontend UI
```bash
cd platform/frontend/components/trainer
touch TrainerUploadModal.tsx
```

**Estimated Effort**: 4-6 weeks

### From Phase 3 to Phase 4

**Step 1**: Add versioning support
**Step 2**: Build marketplace UI
**Step 3**: Add analytics tracking
**Step 4**: Implement review system

**Estimated Effort**: 6-8 weeks

---

## Success Metrics

### Phase 2
- ✅ 100% of capabilities.json models validated before upload
- ✅ Zero invalid models in production
- ✅ Automated testing coverage: 90%+

### Phase 3
- ✅ UI upload success rate: >95%
- ✅ Validation time: <5 minutes per trainer
- ✅ Time from upload to usable: <10 minutes

### Phase 4
- ✅ Community trainers: 50+ trainers
- ✅ Monthly active trainers: 100+
- ✅ Average trainer rating: >4.0/5.0
- ✅ Training job success rate: >90%

---

## Related Documentation

- [MODEL_CAPABILITIES_SYSTEM.md](../MODEL_CAPABILITIES_SYSTEM.md) - Current implementation
- [CONFIG_SCHEMA_SYSTEM.md](../CONFIG_SCHEMA_SYSTEM.md) - Config schema convention
- [EXPORT_CONVENTION.md](../EXPORT_CONVENTION.md) - Export convention
- [DUAL_STORAGE.md](../DUAL_STORAGE.md) - Storage architecture

---

## Appendix: Example Trainer Package

**trainer.zip structure**:
```
custom-yolo-turbo/
├── train.py
├── config_schema.py
├── capabilities.json
├── export.py
├── predict.py
├── validate_capabilities.py
├── requirements.txt
├── Dockerfile
├── README.md
└── utils.py
```

**capabilities.json example**:
```json
{
  "framework": "custom-yolo-turbo",
  "display_name": "YOLO Turbo (Custom)",
  "description": "10x faster YOLO with custom optimizations",
  "version": "1.0.0",
  "author": "user123",
  "license": "MIT",
  "models": [
    {
      "model_name": "yolo-turbo-n",
      "display_name": "YOLO Turbo Nano",
      "task_types": ["detection"],
      "description": "Ultra-fast nano model",
      "parameters": {"min": 0.9, "macs": 3.2},
      "supported": true
    }
  ],
  "task_types": [
    {
      "name": "detection",
      "display_name": "Object Detection",
      "description": "Detect objects with bounding boxes",
      "supported": true
    }
  ],
  "dataset_formats": [
    {
      "name": "yolo",
      "display_name": "YOLO Format",
      "supported": true
    }
  ]
}
```

**Dockerfile example**:
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Validation entry point
CMD ["python", "train.py"]
```
