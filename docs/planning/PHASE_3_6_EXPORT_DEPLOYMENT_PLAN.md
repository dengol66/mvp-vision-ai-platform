# Phase 3.6: Model Export & Deployment Implementation Plan

**Created**: 2025-11-14
**Status**: Planning
**Reference**: `platform/docs/architecture/EXPORT_DEPLOYMENT_DESIGN.md`

## Overview

Phase 3.6 implements the complete model export and deployment system, enabling users to convert trained checkpoints to production-ready formats and deploy them to various targets.

**Timeline**: 3-4 weeks (Phase 1 MVP only)
**Priority**: High (after Phase 3.2 & 3.5 completion)

## Goals

### Primary Goals (Phase 1 MVP)

1. **Multi-Format Export**
   - ONNX, TensorRT, CoreML, TFLite, TorchScript, OpenVINO
   - Framework capability matrix
   - Dynamic quantization support

2. **Deployment Options**
   - Self-hosted download (presigned URLs)
   - **Platform inference endpoints** (Triton Inference Server) ⭐ CRITICAL
   - Edge deployment packages (iOS, Android)
   - Container packages (Docker)

3. **Production-Ready Output**
   - Comprehensive metadata (preprocessing, postprocessing, classes)
   - Runtime wrappers (Python, C++, Swift, Kotlin)
   - Export package (zip with all artifacts)

4. **3-Tier Execution**
   - Tier-1: Subprocess (local development)
   - Tier-2: Kind (local Kubernetes)
   - Tier-3: Production Kubernetes

### Out of Scope (Phase 2/3)

- Static quantization with calibration
- Structured/unstructured pruning
- Validation after export
- Platform Docker registry
- A/B testing for endpoints
- Quantization-Aware Training (QAT)

## Architecture

### Two-Phase Workflow

```
TrainingJob (checkpoint.pt)
    ↓
ExportJob (format=onnx, optimize=quantize_int8)
    ↓
Exported Model Package
  ├── model.onnx
  ├── metadata.json
  └── runtimes/
      ├── python/model_wrapper.py
      ├── cpp/model_wrapper.cpp
      ├── swift/ModelWrapper.swift
      └── kotlin/ModelWrapper.kt
    ↓
DeploymentTarget (type=platform_endpoint)
    ↓
Platform Inference Endpoint
  - Triton Inference Server
  - REST API: POST /v1/infer/{deployment_id}
  - Auto-scaling (HPA)
```

### Database Schema

**ExportJob**:
- Primary: export_format, checkpoint_path, export_config, optimization_config
- Version management: version, version_tag, is_default
- Results: exported_model_path, export_package_path, model_size_bytes
- Metrics: optimization_stats, validation_metrics

**DeploymentTarget**:
- Primary: deployment_type, deployment_config
- Platform endpoint: endpoint_url, api_key, replicas, auto_scaling
- Usage: request_count, last_request_at, total_inference_time_ms

**DeploymentHistory**:
- Event tracking: deployed, updated, scaled, deactivated
- Status transitions: status_before, status_after

## Implementation Breakdown

### Week 1: Backend Models & API Foundation

**Day 1-2: Database Models**
- [ ] Create ExportJob model (app/models/export_job.py)
  - Enums: ExportFormat, ExportJobStatus
  - Fields: All fields from design doc
  - Relationships: TrainingJob ↔ ExportJob
  - Indexes: training_job_id + version, is_default
- [ ] Create DeploymentTarget model (app/models/deployment_target.py)
  - Enums: DeploymentType, DeploymentStatus
  - Fields: deployment_type, deployment_config
  - Relationships: ExportJob ↔ DeploymentTarget
- [ ] Create DeploymentHistory model (app/models/deployment_history.py)
  - Event logging structure
- [ ] Alembic migrations
  - Create tables
  - Add foreign keys
  - Create indexes

**Day 3-5: Core API Endpoints**
- [ ] Export capabilities endpoint
  - GET /api/v1/export/capabilities?framework={framework}
  - Return framework capability matrix
  - Quality levels: excellent, good, fair
- [ ] Export job CRUD endpoints
  - POST /api/v1/export/jobs (create)
  - GET /api/v1/training/{id}/exports (list)
  - GET /api/v1/export/{id} (get)
  - POST /api/v1/export/{id}/set-default
  - GET /api/v1/export/{id}/download (presigned URL)
- [ ] Export callback endpoint
  - POST /api/v1/export/{id}/callback/completion
  - Update status, results, metrics
- [ ] Basic deployment endpoints
  - POST /api/v1/deployments (create)
  - GET /api/v1/deployments (list)
  - GET /api/v1/deployments/{id} (get)

**Deliverables**:
- 3 database models with migrations
- 9 API endpoints
- Unit tests for models
- Integration tests for CRUD operations

### Week 2: Trainer Export Scripts & Runtime Wrappers

**Day 1-3: Ultralytics Export Script**
- [ ] Create platform/trainers/ultralytics/export.py
  - CLI interface (--export-format, --checkpoint-path, etc.)
  - Environment variable support (K8s Job compatible)
  - Download checkpoint from S3 (Internal Storage)
  - Format conversion:
    - [ ] ONNX export (model.export(format='onnx'))
    - [ ] TensorRT export (format='engine')
    - [ ] CoreML export (format='coreml')
    - [ ] TFLite export (format='tflite')
    - [ ] TorchScript export (format='torchscript')
  - Dynamic quantization (optional)
  - Generate metadata.json
  - Upload to S3 (Internal Storage)
  - Send completion callback

**Day 4-5: Runtime Wrappers**
- [ ] Python wrapper template (runtimes/python/model_wrapper.py)
  - Preprocessing: resize, normalize, format conversion
  - ONNX Runtime integration
  - Postprocessing: NMS, threshold, class filtering
  - Example usage script
- [ ] C++ wrapper template (runtimes/cpp/model_wrapper.cpp)
  - ONNXRuntime C++ API
  - OpenCV preprocessing
  - Header file (model_wrapper.h)
  - CMakeLists.txt
- [ ] Swift wrapper template (runtimes/swift/ModelWrapper.swift)
  - CoreML integration
  - Vision framework preprocessing
  - Package.swift
- [ ] Kotlin wrapper template (runtimes/kotlin/ModelWrapper.kt)
  - TFLite Interpreter integration
  - Android Camera2 preprocessing
  - build.gradle

**Deliverables**:
- export.py (300-400 lines)
- 4 runtime wrapper templates
- Metadata schema definition
- E2E test: Training → Export → Package

### Week 3: Platform Inference Endpoint (CRITICAL)

**Day 1-2: Triton Inference Server Setup**
- [ ] Add Triton to docker-compose.tier0.yaml
  - Image: nvcr.io/nvidia/tritonserver:24.01-py3
  - Ports: 8100 (HTTP), 8101 (gRPC), 8102 (metrics)
  - Model repository: S3-backed or local volume
  - Health check endpoint
- [ ] Create Triton model repository structure
  - Models directory: /models
  - Per-model structure: /models/{deployment_id}/1/model.onnx
  - Config file: /models/{deployment_id}/config.pbtxt

**Day 3-4: Platform Endpoint API**
- [ ] POST /v1/infer/{deployment_id}
  - Authentication: Bearer token (API key from DeploymentTarget)
  - Request: {"image": "base64...", "confidence_threshold": 0.5}
  - Load deployment from DB (get model path, api_key)
  - Forward to Triton: POST http://triton:8100/v2/models/{model}/infer
  - Parse Triton response
  - Apply postprocessing (NMS, threshold)
  - Return predictions: [{"class": "cat", "confidence": 0.95, "bbox": [...]}]
  - Update usage stats (request_count, total_inference_time_ms)
- [ ] Rate limiting
  - Use user tier from User model
  - Apply limits: free (10 req/min), pro (100 req/min), enterprise (1000 req/min)
  - Return 429 Too Many Requests if exceeded
- [ ] Usage tracking
  - Increment request_count
  - Update last_request_at
  - Track total_inference_time_ms

**Day 5: Deployment Workflow**
- [ ] POST /api/v1/deployments (platform_endpoint type)
  - Upload model to Triton repository
  - Generate config.pbtxt (max_batch_size, instance_count, backend)
  - Register deployment in DeploymentTarget table
  - Generate API key (JWT or random token)
  - Return endpoint_url and api_key
- [ ] Deployment lifecycle
  - [ ] Deploy: Upload model to Triton
  - [ ] Deactivate: Remove model from Triton (POST /v2/repository/models/{model}/unload)
  - [ ] Reactivate: Re-upload model to Triton

**Deliverables**:
- Triton Inference Server integration
- Platform inference API endpoint
- Deployment workflow (create, deactivate, reactivate)
- Rate limiting implementation
- Usage tracking

### Week 4: Frontend & Integration

**Day 1-3: Export/Deploy Page**
- [ ] Create ExportDeployPage.tsx
  - Route: /training/{job_id}/export-deploy
  - Two-column layout: Export (left) + Deployment (right)
- [ ] Export Section
  - [ ] ExportHistoryTable
    - Columns: Version, Format, Size, Status, Created, Actions
    - Actions: Download, Deploy, Set Default, Delete
  - [ ] CreateExportModal (3-step wizard)
    - Step 1: Format selection (grid of cards)
    - Step 2: Optimization options (quantization toggle)
    - Step 3: Review & submit
  - [ ] ExportDetailModal
    - Job info, optimization stats, download button
- [ ] Deployment Section
  - [ ] ActiveDeploymentsList (card grid)
    - Deployment type badges
    - Status indicators
  - [ ] CreateDeploymentModal
    - Deployment type selector
    - Platform endpoint config (GPU, auto-scaling)
  - [ ] PlatformEndpointCard
    - Endpoint URL (copy button)
    - API key (show/hide, regenerate)
    - Usage stats (requests, avg latency)
    - Test playground (image upload, predictions display)

**Day 4-5: Testing & Documentation**
- [ ] Integration tests
  - Export workflow (create → execute → download)
  - Platform endpoint deployment
  - Inference API calls
- [ ] E2E tests
  - Complete flow: UI → Export → Deploy → Infer
- [ ] Documentation
  - Update EXPORT_DEPLOYMENT_DESIGN.md
  - Create EXPORT_GUIDE.md for trainers
  - Update CLAUDE.md with new endpoints

**Deliverables**:
- Export/Deploy page with 10+ components
- Complete integration tests
- E2E test suite
- Updated documentation

## Backend subprocess Integration

### training_subprocess.py Extensions

```python
async def start_export(
    self,
    export_job_id: str,
    training_job_id: str,
    framework: str,
    export_format: str,
    checkpoint_path: str,
    export_config: Dict[str, Any],
    optimization_config: Dict[str, Any],
    callback_url: str,
) -> subprocess.Popen:
    """Start export subprocess (export.py)."""

    # Get trainer path
    trainer_dir = Path("platform/trainers") / framework
    python_exe = self._get_venv_python(trainer_dir)

    # Prepare command (K8s Job style - env vars)
    cmd = [str(python_exe), "export.py", "--log-level", "INFO"]

    # Prepare environment
    env = os.environ.copy()
    env['EXPORT_JOB_ID'] = str(export_job_id)
    env['TRAINING_JOB_ID'] = str(training_job_id)
    env['EXPORT_FORMAT'] = export_format
    env['CHECKPOINT_PATH'] = checkpoint_path
    env['EXPORT_CONFIG'] = json.dumps(export_config)
    env['OPTIMIZATION_CONFIG'] = json.dumps(optimization_config)
    env['CALLBACK_URL'] = callback_url

    # Inject storage credentials
    storage_env_vars = [
        'INTERNAL_STORAGE_ENDPOINT',
        'INTERNAL_STORAGE_ACCESS_KEY',
        'INTERNAL_STORAGE_SECRET_KEY',
        'INTERNAL_BUCKET_CHECKPOINTS',
    ]
    for var in storage_env_vars:
        if var in os.environ:
            env[var] = os.environ[var]

    # Start process
    process = subprocess.Popen(
        cmd,
        cwd=trainer_dir,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    # Track process
    process_key = f"export_{export_job_id}"
    self.processes[process_key] = process

    logger.info(f"Started export job {export_job_id} (PID: {process.pid})")

    return process
```

## Triton Inference Server Configuration

### docker-compose.tier0.yaml

```yaml
services:
  triton:
    image: nvcr.io/nvidia/tritonserver:24.01-py3
    container_name: triton-inference-server
    ports:
      - "8100:8000"  # HTTP
      - "8101:8001"  # gRPC
      - "8102:8002"  # Metrics
    volumes:
      - ./triton-models:/models
    command: tritonserver --model-repository=/models --log-verbose=1
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/v2/health/ready"]
      interval: 10s
      timeout: 5s
      retries: 5
```

### Model Repository Structure

```
triton-models/
├── deployment-{uuid-1}/
│   ├── 1/
│   │   └── model.onnx
│   └── config.pbtxt
├── deployment-{uuid-2}/
│   ├── 1/
│   │   └── model.onnx
│   └── config.pbtxt
└── ...
```

### config.pbtxt Template

```
name: "deployment-{uuid}"
platform: "onnxruntime_onnx"
max_batch_size: 8

input [
  {
    name: "input"
    data_type: TYPE_FP32
    dims: [3, 640, 640]
  }
]

output [
  {
    name: "output"
    data_type: TYPE_FP32
    dims: [25200, 85]
  }
]

instance_group [
  {
    count: 2
    kind: KIND_CPU
  }
]
```

## Testing Strategy

### Unit Tests

**Backend Models**:
```python
def test_export_job_creation():
    """Test ExportJob model creation"""
    job = ExportJob(
        training_job_id=uuid4(),
        export_format=ExportFormat.ONNX,
        framework="ultralytics",
        checkpoint_path="s3://...",
        export_config={"opset_version": 17}
    )
    assert job.status == ExportJobStatus.PENDING
    assert job.version == 1
```

**API Endpoints**:
```python
def test_create_export_job(client, db_session):
    """Test POST /api/v1/export/jobs"""
    response = client.post("/api/v1/export/jobs", json={
        "training_job_id": str(uuid4()),
        "export_format": "onnx",
        "export_config": {"opset_version": 17}
    })
    assert response.status_code == 201
    assert "export_job_id" in response.json()
```

### Integration Tests

**Export Workflow**:
```python
async def test_export_workflow():
    """Test complete export workflow"""
    # 1. Create export job via API
    export_job = await create_export_job(...)

    # 2. Start export subprocess
    process = await training_subprocess.start_export(...)

    # 3. Wait for completion
    await asyncio.wait_for(process.wait(), timeout=300)

    # 4. Verify results
    export_job = get_export_job(export_job.id)
    assert export_job.status == "completed"
    assert export_job.exported_model_path is not None

    # 5. Verify S3 artifacts
    assert s3_client.object_exists(export_job.exported_model_path)
    assert s3_client.object_exists(export_job.export_package_path)
```

**Platform Endpoint**:
```python
async def test_platform_endpoint_inference():
    """Test platform inference endpoint"""
    # 1. Deploy model
    deployment = await create_deployment(
        export_job_id=export_job.id,
        deployment_type="platform_endpoint"
    )

    # 2. Call inference API
    response = client.post(
        f"/v1/infer/{deployment.id}",
        headers={"Authorization": f"Bearer {deployment.api_key}"},
        json={"image": base64_image, "confidence_threshold": 0.5}
    )

    # 3. Verify response
    assert response.status_code == 200
    predictions = response.json()["predictions"]
    assert len(predictions) > 0
    assert "class" in predictions[0]
    assert "confidence" in predictions[0]
```

### E2E Tests

**Complete Flow**:
1. Train model → TrainingJob completes
2. Export to ONNX → ExportJob completes
3. Deploy to platform endpoint → DeploymentTarget active
4. Call inference API → Predictions returned
5. Verify usage tracking → request_count incremented

## Success Criteria

**Phase 1 MVP Complete** when:
- [ ] All 75 tasks completed
- [ ] Export to 6 formats working (ONNX, TensorRT, CoreML, TFLite, TorchScript, OpenVINO)
- [ ] 4 runtime wrappers generated (Python, C++, Swift, Kotlin)
- [ ] Platform inference endpoint operational
- [ ] Triton Inference Server integrated
- [ ] Rate limiting and usage tracking working
- [ ] Frontend Export/Deploy page complete
- [ ] All tests passing (unit, integration, E2E)
- [ ] Documentation updated

## Risks & Mitigation

### Risk 1: Triton Integration Complexity
**Impact**: High (CRITICAL feature)
**Probability**: Medium
**Mitigation**:
- Start with simple ONNX models
- Use Triton's HTTP API (simpler than gRPC)
- Fallback to TorchServe if Triton too complex

### Risk 2: Format Conversion Failures
**Impact**: High
**Probability**: Medium
**Mitigation**:
- Test with multiple model architectures
- Provide clear error messages
- Fall back to ONNX if native export fails

### Risk 3: Performance Bottlenecks
**Impact**: Medium
**Probability**: Low
**Mitigation**:
- Use Triton's batching support
- Implement caching for metadata
- Monitor latency and throughput

## Next Steps After Phase 1

**Phase 2** (4-5 weeks):
- Static quantization with calibration
- Structured pruning
- Validation after export
- Platform Docker registry
- Deployment scaling UI

**Phase 3** (6-8 weeks):
- Quantization-Aware Training (QAT)
- Knowledge distillation
- Unstructured pruning
- A/B testing for endpoints
- Multi-model deployments

## Resources

### Documentation
- [EXPORT_DEPLOYMENT_DESIGN.md](../architecture/EXPORT_DEPLOYMENT_DESIGN.md) - Complete design doc
- [MVP_TO_PLATFORM_CHECKLIST.md](./MVP_TO_PLATFORM_CHECKLIST.md) - Phase 3.6 section
- [Triton Docs](https://docs.nvidia.com/deeplearning/triton-inference-server/) - Triton reference
- [ONNX Runtime](https://onnxruntime.ai/) - ONNX runtime docs
- [Ultralytics Export](https://docs.ultralytics.com/modes/export/) - YOLO export guide

### Key Files
- `platform/backend/app/models/export_job.py` - ExportJob model
- `platform/backend/app/api/export.py` - Export API endpoints
- `platform/trainers/ultralytics/export.py` - Export script
- `platform/frontend/app/training/[id]/export-deploy/page.tsx` - Frontend page

---

**Last Updated**: 2025-11-14
**Status**: Planning Complete, Ready for Implementation
