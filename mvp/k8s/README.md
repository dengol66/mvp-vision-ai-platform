# Kubernetes Training Infrastructure

This directory contains Kubernetes configurations and utilities for running training jobs in containerized environments.

## Overview

The K8s training infrastructure enables:
- ✅ **Containerized Training** - Run training in isolated Docker containers
- ✅ **Resource Management** - GPU/CPU/memory limits and requests
- ✅ **Automatic Recovery** - K8s Job retry policies
- ✅ **Scalability** - Run multiple jobs in parallel across nodes
- ✅ **Framework Independence** - Separate images per framework (ultralytics, timm, etc.)

## Directory Structure

```
mvp/k8s/
├── README.md              # This file
├── QUICKSTART.md          # 15-minute setup guide
├── setup.sh               # Setup script (Linux/macOS)
├── setup.ps1              # Setup script (Windows)
└── examples/              # Example manifests (coming soon)
```

## Quick Links

- **Getting Started**: See [QUICKSTART.md](./QUICKSTART.md)
- **Migration Plan**: See [docs/k8s/20251106_kubernetes_job_migration_plan.md](../../docs/k8s/20251106_kubernetes_job_migration_plan.md)
- **Docker Images**: See [mvp/training/docker/](../training/docker/)
- **VMController**: See [mvp/backend/app/services/vm_controller.py](../backend/app/services/vm_controller.py)

## Architecture

### Current Flow (Subprocess)

```
Backend API → Training Service API → subprocess.Popen() → train.py
```

### New Flow (Kubernetes)

```
Backend API → VMController → K8s API → K8s Job → Pod → Container → train.py
```

### Key Components

1. **Docker Images** (`mvp/training/docker/`)
   - `Dockerfile.base` - Shared dependencies (PyTorch, CUDA, boto3)
   - `Dockerfile.ultralytics` - YOLO models
   - `Dockerfile.timm` - Classification models (ResNet, EfficientNet)

2. **VMController** (`mvp/backend/app/services/vm_controller.py`)
   - Creates Kubernetes Jobs
   - Monitors job status
   - Retrieves logs
   - Manages job lifecycle

3. **TrainingManagerK8s** (`mvp/backend/app/utils/training_manager_k8s.py`)
   - Dual executor support (subprocess or kubernetes)
   - Automatic fallback if K8s unavailable
   - Unified interface for both modes

4. **Setup Scripts**
   - Creates namespace: `training`
   - Creates secrets: R2 credentials
   - Creates configmaps: Backend API URL

## Features

### ✅ Implemented

- [x] Dockerfile for base image with common dependencies
- [x] Dockerfile for Ultralytics YOLO
- [x] Dockerfile for timm (PyTorch Image Models)
- [x] Build scripts (Linux/macOS/Windows)
- [x] VMController for K8s Job management
- [x] TrainingManagerK8s with dual executor support
- [x] Setup scripts for K8s resources
- [x] QuickStart guide

### 🚧 In Progress

- [ ] GPU node support (NVIDIA Device Plugin)
- [ ] Monitoring with Prometheus/Grafana
- [ ] Background job status monitor
- [ ] WebSocket notifications for job events

### 📋 Planned

- [ ] Temporal workflow integration
- [ ] Cloud GPU support (AWS ECS/EKS, GCP GKE)
- [ ] Auto-scaling based on job queue
- [ ] Cost tracking and optimization
- [ ] Sidecar pattern for advanced monitoring

## Usage

### 1. Local Development

**Setup** (one-time):
```bash
# Build images
cd mvp/training/docker
./build.sh all

# Load into Kind
kind load docker-image vision-platform/trainer-ultralytics:v1.0

# Setup K8s resources
cd mvp/k8s
./setup.sh
```

**Use in code**:
```python
from app.utils.training_manager_k8s import TrainingManagerK8s

# Initialize with K8s as default
manager = TrainingManagerK8s(db, default_executor="kubernetes")

# Start training
manager.start_training(job_id=123)

# Check status
status = manager.get_training_status(job_id=123)

# Get logs
logs = manager.get_training_logs(job_id=123, tail_lines=100)

# Stop training
manager.stop_training(job_id=123)
```

### 2. Production Deployment

See [docs/k8s/20251106_kubernetes_job_migration_plan.md](../../docs/k8s/20251106_kubernetes_job_migration_plan.md) for:
- Production cluster setup (AWS EKS, GCP GKE)
- GPU node configuration
- CI/CD pipeline
- Monitoring and alerting

## Configuration

### Environment Variables

**Backend** (`.env` or environment):
```bash
# Kubernetes settings
K8S_TRAINING_NAMESPACE=training
DOCKER_REGISTRY=ghcr.io/myorg
TRAINER_IMAGE_VERSION=v1.0

# Executor selection
DEFAULT_EXECUTOR=kubernetes  # or "subprocess"

# R2 Storage (will be injected into pods via Secret)
AWS_S3_ENDPOINT_URL=https://xxx.r2.cloudflarestorage.com
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key

# Backend API (will be injected into pods via ConfigMap)
BACKEND_API_URL=http://backend-api:8000
```

### Kubernetes Resources

**Namespace**: `training`
- Isolates training jobs from other workloads

**Secret**: `r2-credentials`
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: r2-credentials
  namespace: training
type: Opaque
data:
  endpoint: <base64>
  access-key: <base64>
  secret-key: <base64>
```

**ConfigMap**: `backend-config`
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: backend-config
  namespace: training
data:
  api-url: http://backend-api:8000
```

### Resource Limits

Default limits per job (configurable in `TrainingJobConfig`):
```yaml
resources:
  limits:
    nvidia.com/gpu: 1
    memory: 16Gi
    cpu: 4
  requests:
    nvidia.com/gpu: 1
    memory: 8Gi
    cpu: 2
```

## Docker Images

### Build Locally

```bash
cd mvp/training/docker

# Build all images
./build.sh all --tag v1.0

# Build specific image
./build.sh ultralytics --tag v1.0

# Build and push to registry
./build.sh all --tag v1.0 --push
```

### Image Sizes (Approximate)

- `trainer-base`: ~3.5 GB (CUDA 11.8, PyTorch 2.1, Python 3.11)
- `trainer-ultralytics`: +500 MB (Ultralytics 8.3.0)
- `trainer-timm`: +300 MB (timm 1.0.3)

### Image Registry

**Local development**:
```bash
# Load into Kind
kind load docker-image vision-platform/trainer-ultralytics:v1.0

# Use in Job spec
image: vision-platform/trainer-ultralytics:v1.0
imagePullPolicy: IfNotPresent
```

**Production**:
```bash
# Push to registry (GitHub Container Registry example)
docker tag vision-platform/trainer-ultralytics:v1.0 \
  ghcr.io/myorg/trainer-ultralytics:v1.0

docker push ghcr.io/myorg/trainer-ultralytics:v1.0

# Use in Job spec
image: ghcr.io/myorg/trainer-ultralytics:v1.0
imagePullPolicy: IfNotPresent
```

## Monitoring

### View Jobs

```bash
# List all jobs
kubectl get jobs -n training

# Watch jobs in real-time
kubectl get jobs -n training -w

# Get job details
kubectl describe job training-job-123 -n training

# Delete completed jobs
kubectl delete jobs --field-selector status.successful=1 -n training
```

### View Pods

```bash
# List pods
kubectl get pods -n training

# Get pod details
kubectl describe pod training-job-123-xxxxx -n training

# View logs
kubectl logs -f training-job-123-xxxxx -n training

# Follow logs from specific container
kubectl logs -f training-job-123-xxxxx -c trainer -n training
```

### View Events

```bash
# Recent events
kubectl get events -n training --sort-by='.lastTimestamp'

# Watch events
kubectl get events -n training -w
```

## Troubleshooting

### Common Issues

**1. Job stays in Pending**

Check pod status:
```bash
kubectl get pods -n training
kubectl describe pod training-job-123-xxxxx -n training
```

Possible causes:
- No GPU nodes → Remove GPU requirement temporarily
- Image not found → Check image name and load it
- Resource limits too high → Reduce requests

**2. ImagePullBackOff error**

Ensure image is available:
```bash
# For Kind
kind load docker-image vision-platform/trainer-ultralytics:v1.0

# For Minikube
minikube image load vision-platform/trainer-ultralytics:v1.0

# Verify image in cluster
kubectl run test --image=vision-platform/trainer-ultralytics:v1.0 \
  --restart=Never --rm -it -- python --version
```

**3. R2 credentials not working**

Verify secret:
```bash
# Check secret exists
kubectl get secret r2-credentials -n training

# View secret values (base64 encoded)
kubectl get secret r2-credentials -n training -o yaml

# Update secret
kubectl create secret generic r2-credentials \
  --from-literal=endpoint=YOUR_ENDPOINT \
  --from-literal=access-key=YOUR_ACCESS_KEY \
  --from-literal=secret-key=YOUR_SECRET_KEY \
  --namespace=training \
  --dry-run=client -o yaml | kubectl apply -f -
```

**4. Training fails immediately**

Check logs:
```bash
kubectl logs training-job-123-xxxxx -n training
```

Common causes:
- Python import errors → Check Dockerfile
- Dataset not found → Verify dataset exists in R2
- Invalid arguments → Check VMController argument building

### Debug Mode

Run training job interactively:
```bash
# Create temporary pod
kubectl run debug-trainer \
  --image=vision-platform/trainer-ultralytics:v1.0 \
  --restart=Never \
  --rm -it \
  --namespace=training \
  -- bash

# Inside pod, run train.py manually
python train.py \
  --framework ultralytics \
  --model_name yolo11n \
  --task_type object_detection \
  --dataset_path coco8 \
  --dataset_format yolo \
  --epochs 5 \
  --batch_size 16 \
  --learning_rate 0.001 \
  --output_dir /workspace/output \
  --job_id 999
```

## Migration from Subprocess

### Phase 1: Test K8s Locally

1. Keep subprocess mode as default
2. Test K8s mode with select jobs
3. Compare results

```python
# Test both executors
manager = TrainingManagerK8s(db, default_executor="subprocess")

# Try K8s
manager.start_training(job_id=123, executor="kubernetes")

# Try subprocess
manager.start_training(job_id=124, executor="subprocess")
```

### Phase 2: Gradual Rollout

1. Make K8s default for new jobs
2. Keep subprocess available for fallback
3. Monitor for issues

```python
manager = TrainingManagerK8s(db, default_executor="kubernetes")
```

### Phase 3: Full Migration

1. Deprecate subprocess mode
2. Remove Training Service API
3. K8s only

## Performance Considerations

### Resource Optimization

**Training speed comparison**:
- Subprocess: ~100 ms overhead
- Kubernetes: ~2-5 seconds overhead (image pull + pod scheduling)

**Storage I/O**:
- R2 download: Same for both (happens in train.py)
- Checkpoint upload: Same for both (happens in train.py)

**Recommendations**:
- Use image pull policy `IfNotPresent` to cache images
- Pre-pull images on nodes for faster startup
- Use PersistentVolumes for frequently used datasets (optional)

### Cost Optimization

- Use node auto-scaling for dynamic capacity
- Set appropriate resource requests/limits
- Enable job TTL for automatic cleanup
- Use spot instances for non-critical jobs (future)

## Security

### RBAC

Ensure Backend service account has permissions:
```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: training-job-creator
  namespace: training
rules:
- apiGroups: ["batch"]
  resources: ["jobs"]
  verbs: ["create", "get", "list", "delete"]
- apiGroups: [""]
  resources: ["pods", "pods/log"]
  verbs: ["get", "list"]
```

### Network Policies

Isolate training pods:
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: training-isolation
  namespace: training
spec:
  podSelector:
    matchLabels:
      app: training-job
  policyTypes:
  - Egress
  egress:
  - to:
    - namespaceSelector: {}
    ports:
    - protocol: TCP
      port: 443  # HTTPS (R2, Backend API)
```

## Support

- **QuickStart**: [QUICKSTART.md](./QUICKSTART.md)
- **Migration Plan**: [docs/k8s/20251106_kubernetes_job_migration_plan.md](../../docs/k8s/20251106_kubernetes_job_migration_plan.md)
- **Issues**: Report at GitHub Issues

## License

Same as main project.
