# Kubernetes Training QuickStart Guide

This guide will help you get started with Kubernetes-based training execution in **under 15 minutes**.

## Prerequisites

- Docker installed
- kubectl installed
- Local Kubernetes cluster (Kind, Minikube, or Docker Desktop)
- Python 3.11+

## Quick Setup (5 Steps)

### Step 1: Install Local Kubernetes Cluster

Choose one:

**Option A: Kind (Recommended)**
```bash
# Install Kind
# macOS
brew install kind

# Windows (with Chocolatey)
choco install kind

# Create cluster
kind create cluster --name training-cluster
```

**Option B: Minikube**
```bash
# Install Minikube
# macOS
brew install minikube

# Windows
choco install minikube

# Start cluster
minikube start --driver=docker
```

**Option C: Docker Desktop**
- Open Docker Desktop → Settings → Kubernetes → Enable Kubernetes

### Step 2: Build Docker Images

```bash
# Navigate to project root
cd mvp-vision-ai-platform

# Build all images (base, ultralytics, timm)
cd mvp/training/docker

# Linux/macOS
./build.sh all --tag v1.0

# Windows
.\build.ps1 -Target all -Tag v1.0
```

This will build:
- `vision-platform/trainer-base:v1.0`
- `vision-platform/trainer-ultralytics:v1.0`
- `vision-platform/trainer-timm:v1.0`

**Load images into Kind** (if using Kind):
```bash
kind load docker-image vision-platform/trainer-base:v1.0 --name training-cluster
kind load docker-image vision-platform/trainer-ultralytics:v1.0 --name training-cluster
kind load docker-image vision-platform/trainer-timm:v1.0 --name training-cluster
```

### Step 3: Setup Kubernetes Resources

```bash
# Navigate to k8s directory
cd mvp/k8s

# Set R2 credentials (optional, can be updated later)
export AWS_S3_ENDPOINT_URL="https://your-account-id.r2.cloudflarestorage.com"
export AWS_ACCESS_KEY_ID="your-access-key"
export AWS_SECRET_ACCESS_KEY="your-secret-key"

# Run setup script
# Linux/macOS
./setup.sh

# Windows
.\setup.ps1
```

This creates:
- Namespace: `training`
- Secret: `r2-credentials` (R2 storage credentials)
- ConfigMap: `backend-config` (Backend API URL)

### Step 4: Install Python Dependencies

```bash
# Navigate to backend directory
cd mvp/backend

# Install kubernetes client
pip install kubernetes==28.1.0
```

### Step 5: Test Job Creation

**Create a test script:**

```python
# test_k8s_job.py
from app.services.vm_controller import VMController, TrainingJobConfig

# Initialize controller
controller = VMController(namespace="training")

# Create test job configuration
job_config = TrainingJobConfig(
    job_id=999,
    framework="ultralytics",
    task_type="object_detection",
    model_name="yolo11n",
    dataset_path="coco8",  # Built-in YOLO dataset
    dataset_format="yolo",
    epochs=10,
    batch_size=16,
    learning_rate=0.001,
)

# Create Kubernetes Job
job_name = controller.create_training_job(job_config)
print(f"✓ Created Job: {job_name}")

# Check status
status = controller.get_job_status(job_name)
print(f"Status: {status}")

# Get logs (wait a bit for pod to start)
import time
time.sleep(10)
logs = controller.get_job_logs(job_name, tail_lines=50)
print(f"Logs:\n{logs}")
```

**Run test:**
```bash
python test_k8s_job.py
```

**Monitor the job:**
```bash
# Watch job status
kubectl get jobs -n training -w

# Watch pod status
kubectl get pods -n training -w

# Get logs (replace pod name)
kubectl logs -f training-job-999-xxxxx -n training
```

## Verify Installation

Check that everything is working:

```bash
# Check namespace
kubectl get namespace training

# Check secrets
kubectl get secrets -n training

# Check configmaps
kubectl get configmaps -n training

# Check if jobs can be created
kubectl auth can-i create jobs --namespace=training
```

Expected output:
```
namespace/training created
NAME              TYPE     DATA   AGE
r2-credentials    Opaque   3      10s

NAME             DATA   AGE
backend-config   1      10s

yes
```

## Configuration

### Update R2 Credentials

```bash
kubectl create secret generic r2-credentials \
  --from-literal=endpoint=https://your-account-id.r2.cloudflarestorage.com \
  --from-literal=access-key=YOUR_ACCESS_KEY \
  --from-literal=secret-key=YOUR_SECRET_KEY \
  --namespace=training \
  --dry-run=client -o yaml | kubectl apply -f -
```

### Update Backend API URL

```bash
kubectl create configmap backend-config \
  --from-literal=api-url=http://your-backend-api:8000 \
  --namespace=training \
  --dry-run=client -o yaml | kubectl apply -f -
```

### Environment Variables

Set these in your backend service:

```bash
# Enable Kubernetes executor
export K8S_TRAINING_NAMESPACE=training
export DOCKER_REGISTRY=vision-platform  # or your registry
export TRAINER_IMAGE_VERSION=v1.0

# Default executor
export DEFAULT_EXECUTOR=kubernetes  # or "subprocess"
```

## Usage in Backend

### Option 1: Use New TrainingManagerK8s

```python
from app.utils.training_manager_k8s import TrainingManagerK8s

# Initialize with Kubernetes as default
manager = TrainingManagerK8s(db, default_executor="kubernetes")

# Start training (will use Kubernetes)
success = manager.start_training(job_id=123)

# Or explicitly specify executor
success = manager.start_training(job_id=123, executor="kubernetes")
```

### Option 2: Use VMController Directly

```python
from app.services.vm_controller import VMController, TrainingJobConfig

controller = VMController()

job_config = TrainingJobConfig(
    job_id=job.id,
    framework=job.framework,
    model_name=job.model_name,
    # ... other params
)

job_name = controller.create_training_job(job_config)
```

## Monitoring

### Watch Jobs

```bash
# List all jobs
kubectl get jobs -n training

# Watch jobs in real-time
kubectl get jobs -n training -w

# Describe job
kubectl describe job training-job-123 -n training
```

### View Logs

```bash
# Get pod name
kubectl get pods -n training -l job-name=training-job-123

# View logs
kubectl logs -f training-job-123-xxxxx -n training

# View previous logs (if pod crashed)
kubectl logs --previous training-job-123-xxxxx -n training
```

### Job Status

```python
from app.services.vm_controller import VMController

controller = VMController()
status = controller.get_job_status("training-job-123")
print(status)  # "pending", "running", "completed", "failed"

logs = controller.get_job_logs("training-job-123", tail_lines=100)
print(logs)
```

## Cleanup

### Delete a Single Job

```bash
kubectl delete job training-job-123 -n training
```

### Delete All Jobs

```bash
kubectl delete jobs --all -n training
```

### Delete All Resources

```bash
kubectl delete namespace training
```

## Troubleshooting

### Job Stays in Pending

**Check pod status:**
```bash
kubectl get pods -n training
kubectl describe pod training-job-123-xxxxx -n training
```

**Common causes:**
- No GPU nodes available → Remove GPU requirement temporarily
- Image not found → Check image name and ensure it's loaded
- Resource limits too high → Reduce CPU/memory requests

**Quick fix for testing (no GPU):**
Edit `vm_controller.py` line 350, comment out:
```python
# node_selector={"accelerator": "nvidia-gpu"},
```

### Pod Fails to Start

**Check events:**
```bash
kubectl get events -n training --sort-by='.lastTimestamp'
```

**Check pod logs:**
```bash
kubectl logs training-job-123-xxxxx -n training
```

**Common causes:**
- Missing R2 credentials → Update secret
- Invalid dataset path → Check dataset exists in R2
- Python import errors → Check Docker image

### Secrets Not Found

**Verify secrets exist:**
```bash
kubectl get secrets -n training
```

**Re-create secrets:**
```bash
cd mvp/k8s
./setup.sh  # or setup.ps1 on Windows
```

### Logs Say "R2 credentials not configured"

**Check secret values:**
```bash
kubectl get secret r2-credentials -n training -o yaml
```

**Update with correct values:**
```bash
kubectl create secret generic r2-credentials \
  --from-literal=endpoint=YOUR_ENDPOINT \
  --from-literal=access-key=YOUR_ACCESS_KEY \
  --from-literal=secret-key=YOUR_SECRET_KEY \
  --namespace=training \
  --dry-run=client -o yaml | kubectl apply -f -
```

### Training Fails with "Dataset not found"

The dataset ID must exist in R2 or be a valid local path in the container.

**For testing, use built-in YOLO datasets:**
- `coco8` - 8 images COCO dataset
- `coco128` - 128 images COCO dataset

**Or upload your dataset to R2:**
```bash
aws s3 cp dataset.zip s3://vision-platform-prod/datasets/my-dataset.zip \
  --endpoint-url YOUR_R2_ENDPOINT
```

## Next Steps

1. **Production Deployment**: See [docs/k8s/20251106_kubernetes_job_migration_plan.md](../../docs/k8s/20251106_kubernetes_job_migration_plan.md)

2. **GPU Setup**: Install NVIDIA Device Plugin
   ```bash
   kubectl create -f https://raw.githubusercontent.com/NVIDIA/k8s-device-plugin/main/nvidia-device-plugin.yml
   ```

3. **Monitoring**: Set up Prometheus + Grafana

4. **CI/CD**: Automate Docker image builds with GitHub Actions

## Support

**Documentation:**
- [K8s Migration Plan](../../docs/k8s/20251106_kubernetes_job_migration_plan.md)
- [Architecture Overview](../../docs/architecture/ARCHITECTURE.md)

**Logs:**
- Backend logs: Check FastAPI console
- Training logs: `kubectl logs -f POD_NAME -n training`
- K8s events: `kubectl get events -n training`

**Common Commands:**
```bash
# List all resources
kubectl get all -n training

# Delete failed jobs
kubectl delete jobs --field-selector status.successful=0 -n training

# Restart a job (delete and recreate)
kubectl delete job training-job-123 -n training
# Then create new job via Backend API

# Port-forward to pod (for debugging)
kubectl port-forward training-job-123-xxxxx 8888:8888 -n training
```
