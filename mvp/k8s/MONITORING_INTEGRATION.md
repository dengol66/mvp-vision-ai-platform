# Monitoring System Integration Guide

Complete guide for integrating the 3-tier monitoring architecture into your application.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                         Frontend                             │
│  ┌─────────────────┐         ┌──────────────────────┐       │
│  │ TrainingJobPage │────────▶│ TrainingMonitorPanel │       │
│  └─────────────────┘         └──────────────────────┘       │
│           │                            │                     │
│           │ REST API                   │ WebSocket           │
│           ▼                            ▼                     │
└───────────┼────────────────────────────┼─────────────────────┘
            │                            │
┌───────────┼────────────────────────────┼─────────────────────┐
│           │        Backend             │                     │
│  ┌────────▼─────────┐      ┌──────────▼──────────┐          │
│  │  /api/v1/        │      │  /api/v1/ws/        │          │
│  │  training/jobs   │      │  training           │          │
│  └──────────────────┘      └─────────────────────┘          │
│           │                            ▲                     │
│           │                            │ broadcasts          │
│           ▼                            │                     │
│  ┌─────────────────┐      ┌───────────┴──────────┐          │
│  │    Database     │◀─────│  TrainingMonitor     │          │
│  │   (TrainingJob) │      │  (Background Task)   │          │
│  └─────────────────┘      └──────────────────────┘          │
│                                       │                      │
│                                       │ polls every 10s      │
└───────────────────────────────────────┼──────────────────────┘
                                        │
┌───────────────────────────────────────┼──────────────────────┐
│                    Kubernetes          │                     │
│                                        ▼                     │
│                           ┌──────────────────┐               │
│                           │  K8s Jobs API    │               │
│                           └──────────────────┘               │
│                                       │                      │
│                                       ▼                      │
│                           ┌──────────────────┐               │
│                           │  Training Pods   │               │
│                           └──────────────────┘               │
│                                       │                      │
│                                       │ writes metrics       │
│                                       ▼                      │
│                           ┌──────────────────┐               │
│                           │  TrainingLogger  │               │
│                           │  → Backend API   │               │
│                           └──────────────────┘               │
└─────────────────────────────────────────────────────────────┘
            │
            │ scrapes
            ▼
┌────────────────────────────────────────────────────────────┐
│                    Prometheus + Grafana                     │
│  ┌──────────────┐              ┌──────────────┐            │
│  │  Prometheus  │─────────────▶│   Grafana    │            │
│  │  (Metrics)   │  datasource  │  (Dashboard) │            │
│  └──────────────┘              └──────────────┘            │
└────────────────────────────────────────────────────────────┘
```

## Data Flow by Update Type

### 1. Status Changes (Pending → Running → Completed)

**Flow:**
```
K8s Job Status Change
    ↓
TrainingMonitor detects (polling every 10s)
    ↓
Updates Database (TrainingJob.status)
    ↓
WebSocketManager.broadcast_to_job()
    ↓
Frontend receives "training_status_change" message
    ↓
UI updates StatusBadge and Progress Bar
```

**Backend Code:**
```python
# mvp/backend/app/services/training_monitor.py
async def check_active_jobs(self):
    k8s_status = self.vm_controller.get_job_status(job.execution_id)
    if k8s_status != job.status:
        old_status = job.status
        job.status = k8s_status

        await self.websocket_manager.broadcast_to_job(
            job.job_id,
            {
                "type": "training_status_change",
                "job_id": job.job_id,
                "old_status": old_status,
                "new_status": k8s_status,
                "timestamp": datetime.now().isoformat(),
            }
        )
```

**Frontend Code:**
```typescript
// mvp/frontend/hooks/useTrainingMonitor.ts
const { isConnected } = useTrainingMonitor({
  jobId,
  onStatusChange: (jobId, oldStatus, newStatus) => {
    console.log(`Status: ${oldStatus} → ${newStatus}`);
    setStatus(newStatus);
  }
});
```

### 2. Training Metrics (Loss, Accuracy, Epoch)

**Flow:**
```
Training Pod (train.py)
    ↓
TrainingLogger.log_metrics()
    ↓
POST /api/v1/training/jobs/{id}/metrics
    ↓
WebSocketManager.broadcast_to_job()
    ↓
Frontend receives "training_metrics" message
    ↓
UI updates MetricsChart and MetricCards
```

**Training Code:**
```python
# mvp/training/platform_sdk/training_logger.py
class TrainingLogger:
    def log_metrics(self, epoch: int, metrics: Dict[str, float]):
        # Send to backend via HTTP
        response = requests.post(
            f"{self.backend_url}/api/v1/training/jobs/{self.job_id}/metrics",
            json={
                "epoch": epoch,
                "metrics": metrics,
                "timestamp": datetime.now().isoformat(),
            }
        )
```

**Backend Code:**
```python
# mvp/backend/app/api/training.py
@router.post("/jobs/{job_id}/metrics")
async def receive_metrics(
    job_id: int,
    metrics: TrainingMetrics,
    ws_manager: WebSocketManager = Depends(get_websocket_manager),
):
    # Broadcast to WebSocket clients
    await ws_manager.broadcast_to_job(
        job_id,
        {
            "type": "training_metrics",
            "job_id": job_id,
            "metrics": metrics.dict(),
        }
    )
```

**Frontend Code:**
```typescript
// mvp/frontend/components/TrainingMonitorPanel.tsx
const { lastMessage } = useTrainingMonitor({
  jobId,
  onMetrics: (jobId, newMetrics) => {
    setMetrics(prev => [...prev, newMetrics].slice(-50));
  }
});
```

### 3. Training Logs (stdout/stderr)

**Flow:**
```
Training Pod stdout
    ↓
K8s Logs API (kubectl logs)
    ↓
TrainingMonitor.get_recent_logs()
    ↓
WebSocketManager.broadcast_to_job()
    ↓
Frontend receives "training_log" message
    ↓
UI appends to Logs Panel
```

**Backend Code:**
```python
# mvp/backend/app/services/training_monitor.py
async def stream_logs(self, job: TrainingJob):
    recent_logs = self.vm_controller.get_job_logs(
        job.execution_id,
        tail_lines=50
    )

    for line in recent_logs:
        await self.websocket_manager.broadcast_to_job(
            job.job_id,
            {
                "type": "training_log",
                "job_id": job.job_id,
                "log": {
                    "message": line,
                    "level": self._parse_log_level(line),
                    "timestamp": datetime.now().isoformat(),
                }
            }
        )
```

### 4. Infrastructure Metrics (GPU, CPU, Memory)

**Flow:**
```
Kubernetes Pods (cAdvisor)
    ↓
Prometheus scrapes (every 15s)
    ↓
Grafana queries Prometheus
    ↓
User views dashboard in browser
```

**Query Examples:**
```promql
# GPU utilization
nvidia_gpu_duty_cycle{namespace="training", pod=~"training-job-.*"}

# Memory usage
container_memory_usage_bytes{namespace="training", pod=~"training-job-.*"}

# CPU usage
rate(container_cpu_usage_seconds_total{namespace="training", pod=~"training-job-.*"}[5m])
```

## Backend Integration

### Step 1: Install Dependencies

```bash
cd mvp/backend
pip install websockets==12.0
```

### Step 2: Enable Monitoring in FastAPI

```python
# mvp/backend/app/main.py
from contextlib import asynccontextmanager
from app.services.training_monitor import get_monitor, start_monitoring
from app.services.websocket_manager import get_websocket_manager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    monitor = get_monitor()
    ws_manager = get_websocket_manager()
    monitor.set_websocket_manager(ws_manager)

    monitoring_task = asyncio.create_task(start_monitoring())

    yield

    # Shutdown
    await monitor.stop()
    monitoring_task.cancel()

app = FastAPI(lifespan=lifespan)

# Include WebSocket routes
from app.api import websocket
app.include_router(websocket.router, prefix="/api/v1")
```

### Step 3: Add Metrics Endpoint

```python
# mvp/backend/app/api/training.py
from app.services.websocket_manager import get_websocket_manager

@router.post("/jobs/{job_id}/metrics")
async def receive_metrics(
    job_id: int,
    metrics: TrainingMetrics,
    ws_manager: WebSocketManager = Depends(get_websocket_manager),
):
    """Receive metrics from TrainingLogger and broadcast via WebSocket"""
    await ws_manager.broadcast_to_job(
        job_id,
        {
            "type": "training_metrics",
            "job_id": job_id,
            "metrics": metrics.dict(),
        }
    )
    return {"status": "ok"}
```

## Frontend Integration

### Step 1: Install Component

The monitoring components are already created:
- `mvp/frontend/hooks/useTrainingMonitor.ts`
- `mvp/frontend/hooks/useTrainingJob.ts`
- `mvp/frontend/components/TrainingMonitorPanel.tsx`

### Step 2: Create Training Job Page

```tsx
// app/training/[jobId]/page.tsx
'use client';

import { useParams } from 'next/navigation';
import { TrainingMonitorPanel } from '@/components/TrainingMonitorPanel';
import { useTrainingJob } from '@/hooks/useTrainingJob';

export default function TrainingJobPage() {
  const params = useParams();
  const jobId = parseInt(params.jobId as string);

  const { job, isLoading, error } = useTrainingJob(jobId);

  if (isLoading) return <LoadingSpinner />;
  if (error) return <ErrorDisplay error={error} />;

  return (
    <div>
      <h1>Training Job #{jobId}</h1>
      <TrainingMonitorPanel jobId={jobId} sessionId={job.session_id} />
    </div>
  );
}
```

### Step 3: Environment Configuration

```bash
# .env.local
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
```

The WebSocket URL is automatically constructed from this.

## Prometheus + Grafana Integration

### Step 1: Deploy to Kubernetes

```bash
# Deploy Prometheus
kubectl apply -f mvp/k8s/prometheus/prometheus-config.yaml

# Deploy Grafana
kubectl apply -f mvp/k8s/prometheus/grafana-config.yaml

# Verify deployment
kubectl get pods -n monitoring
```

### Step 2: Access Dashboards

**Grafana:**
```bash
# Via NodePort
open http://localhost:30030

# Or port-forward
kubectl port-forward svc/grafana 3000:3000 -n monitoring
open http://localhost:3000
```

Login: `admin` / `admin`

**Prometheus:**
```bash
open http://localhost:30090
```

### Step 3: View Pre-configured Dashboard

Navigate to:
- **Grafana → Dashboards → Training Jobs Monitoring**

This dashboard includes:
- Active Training Jobs (count)
- GPU Utilization (per pod)
- Memory Usage (per pod)
- CPU Usage (per pod)
- Training Status (table)

### Step 4: Add Custom Metrics

If you want to expose custom metrics from backend:

```python
# mvp/backend/app/main.py
from prometheus_fastapi_instrumentator import Instrumentator

app = FastAPI()

# Expose /metrics endpoint
Instrumentator().instrument(app).expose(app)
```

Then add to Prometheus config:

```yaml
# mvp/k8s/prometheus/prometheus-config.yaml
scrape_configs:
  - job_name: 'backend-api'
    static_configs:
      - targets: ['backend-api:8000']
```

## Usage Examples

### Example 1: Simple Training Monitor

```tsx
import { TrainingMonitorPanel } from '@/components/TrainingMonitorPanel';

export function MyTrainingPage() {
  return <TrainingMonitorPanel jobId={123} />;
}
```

### Example 2: Custom Callbacks

```tsx
import { useTrainingMonitor } from '@/hooks/useTrainingMonitor';

export function CustomMonitor() {
  const { isConnected, lastMessage } = useTrainingMonitor({
    jobId: 123,
    onStatusChange: (jobId, oldStatus, newStatus) => {
      if (newStatus === 'completed') {
        alert('Training completed!');
      }
    },
    onMetrics: (jobId, metrics) => {
      if (metrics.loss < 0.1) {
        console.log('Loss below threshold!');
      }
    },
    onLog: (jobId, log) => {
      if (log.level === 'ERROR') {
        console.error('Training error:', log.message);
      }
    },
  });

  return (
    <div>
      <ConnectionStatus connected={isConnected} />
      <LastMessage message={lastMessage} />
    </div>
  );
}
```

### Example 3: Multiple Job Monitoring

```tsx
import { useTrainingMonitor } from '@/hooks/useTrainingMonitor';

export function SessionMonitor({ sessionId }: { sessionId: number }) {
  const [jobs, setJobs] = useState<Record<number, any>>({});

  // Monitor all jobs in a session
  useTrainingMonitor({
    sessionId,
    onStatusChange: (jobId, oldStatus, newStatus) => {
      setJobs(prev => ({
        ...prev,
        [jobId]: { ...prev[jobId], status: newStatus }
      }));
    },
  });

  return (
    <div>
      {Object.entries(jobs).map(([jobId, job]) => (
        <JobCard key={jobId} jobId={jobId} job={job} />
      ))}
    </div>
  );
}
```

### Example 4: Grafana Embedding

```tsx
export function EmbeddedGrafana({ jobId }: { jobId: number }) {
  const grafanaUrl = 'http://localhost:30030';
  const dashboardUid = 'training-dashboard';

  return (
    <iframe
      src={`${grafanaUrl}/d/${dashboardUid}?var-job_id=${jobId}&kiosk`}
      width="100%"
      height="600"
      frameBorder="0"
    />
  );
}
```

## Testing

### Test WebSocket Connection

```bash
# Use wscat to test WebSocket
npm install -g wscat

# Connect to WebSocket
wscat -c "ws://localhost:8000/api/v1/ws/training?job_id=123"

# Should receive:
# {"type":"connected","message":"Connected to training monitoring","timestamp":"..."}

# Send ping
# > {"type":"ping"}
# Should receive:
# {"type":"pong"}
```

### Test Backend Monitor

```bash
# Start a training job
curl -X POST http://localhost:8000/api/v1/training/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "model_name": "yolo11n",
    "framework": "ultralytics",
    "dataset_path": "s3://bucket/dataset",
    "num_epochs": 10,
    "batch_size": 16,
    "executor_type": "kubernetes"
  }'

# Check logs for monitoring activity
tail -f backend.log | grep TrainingMonitor
# Should see:
# [TrainingMonitor] Checking 1 active jobs...
# [TrainingMonitor] Job 123: pending → running
```

### Test Prometheus Scraping

```bash
# Check Prometheus targets
curl http://localhost:30090/api/v1/targets | jq

# Query pod metrics
curl -G http://localhost:30090/api/v1/query \
  --data-urlencode 'query=kube_pod_info{namespace="training"}' | jq
```

## Troubleshooting

### WebSocket Not Connecting

**Symptom:** Frontend shows "Disconnected"

**Checks:**
```bash
# 1. Check backend is running
curl http://localhost:8000/health

# 2. Check WebSocket endpoint
wscat -c "ws://localhost:8000/api/v1/ws/training"

# 3. Check browser console for errors
# Look for: "WebSocket connection failed"
```

**Solution:**
- Verify `NEXT_PUBLIC_API_URL` in `.env.local`
- Check CORS settings in backend
- Ensure WebSocket router is included in FastAPI

### Monitoring Not Detecting Job Changes

**Symptom:** Job status stuck at "running" even though k8s job completed

**Checks:**
```bash
# 1. Check k8s job status
kubectl get jobs -n training

# 2. Check monitor logs
tail -f backend.log | grep TrainingMonitor

# 3. Verify VM controller can access k8s
curl http://localhost:8000/api/v1/internal/k8s/health
```

**Solution:**
- Verify TrainingMonitor is running (check lifespan event)
- Check k8s permissions (ServiceAccount)
- Verify `executor_type="kubernetes"` in database

### Prometheus Not Scraping

**Symptom:** No metrics in Grafana

**Checks:**
```bash
# 1. Check Prometheus targets
kubectl port-forward svc/prometheus 9090:9090 -n monitoring
open http://localhost:9090/targets

# 2. Check pod annotations
kubectl get pods -n training -o yaml | grep prometheus.io

# 3. Check Prometheus logs
kubectl logs -f deployment/prometheus -n monitoring
```

**Solution:**
- Add annotations to training pods:
  ```yaml
  annotations:
    prometheus.io/scrape: "true"
    prometheus.io/port: "9090"
    prometheus.io/path: "/metrics"
  ```

### Grafana Dashboard Not Loading

**Symptom:** "Error loading dashboard"

**Checks:**
```bash
# 1. Check Grafana datasource
kubectl logs -f deployment/grafana -n monitoring

# 2. Test Prometheus connectivity
kubectl exec -it deployment/grafana -n monitoring -- \
  curl http://prometheus:9090/api/v1/query?query=up
```

**Solution:**
- Verify datasource URL: `http://prometheus:9090`
- Check dashboard JSON syntax
- Re-provision dashboard: `kubectl delete configmap grafana-dashboards -n monitoring && kubectl apply -f grafana-config.yaml`

## Performance Considerations

### Backend Monitor Polling Interval

Default: 10 seconds

Adjust in `training_monitor.py`:
```python
POLL_INTERVAL = int(os.getenv("MONITOR_POLL_INTERVAL", "10"))
```

**Trade-offs:**
- Lower (5s): More responsive, higher k8s API load
- Higher (30s): Less responsive, lower API load

**Recommendation:** 10s for most use cases

### WebSocket Message Rate Limiting

If training logs are very verbose, consider:

```python
# mvp/backend/app/services/training_monitor.py
async def stream_logs(self, job: TrainingJob):
    # Only send logs every 2 seconds
    if time.time() - self.last_log_time < 2:
        return

    self.last_log_time = time.time()
    # ... send logs
```

### Frontend Metrics History

Default: Keep last 50 metrics in memory

Adjust in `TrainingMonitorPanel.tsx`:
```typescript
setMetrics(prev => [...prev, newMetrics].slice(-50));
```

For longer training (100+ epochs), consider reducing to `-30`.

### Prometheus Retention

Default: 15 days

Adjust in `prometheus-config.yaml`:
```yaml
args:
  - '--storage.tsdb.retention.time=30d'
  - '--storage.tsdb.retention.size=50GB'
```

## Next Steps

1. **Test the complete flow**:
   - Start a training job
   - Open browser to `http://localhost:3000/training/123`
   - Verify real-time updates

2. **Deploy Prometheus/Grafana**:
   ```bash
   kubectl apply -f mvp/k8s/prometheus/prometheus-config.yaml
   kubectl apply -f mvp/k8s/prometheus/grafana-config.yaml
   ```

3. **Set up alerts** (see `mvp/k8s/prometheus/README.md`)

4. **Customize dashboard** for your specific metrics

5. **Add custom metrics** from TrainingLogger

## Related Documentation

- [mvp/k8s/README.md](README.md) - K8s infrastructure overview
- [mvp/k8s/QUICKSTART.md](QUICKSTART.md) - 15-minute setup guide
- [mvp/k8s/prometheus/README.md](prometheus/README.md) - Prometheus/Grafana details
- [mvp/backend/app/services/training_monitor.py](../backend/app/services/training_monitor.py) - Background monitor implementation
- [mvp/frontend/hooks/useTrainingMonitor.ts](../frontend/hooks/useTrainingMonitor.ts) - WebSocket hook implementation
