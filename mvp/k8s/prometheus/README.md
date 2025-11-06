# Prometheus + Grafana Monitoring Setup

Complete monitoring stack for Kubernetes training jobs.

## Quick Setup

### 1. Deploy Prometheus

```bash
kubectl apply -f prometheus-config.yaml
```

This creates:
- Namespace: `monitoring`
- Prometheus deployment
- Prometheus service (NodePort 30090)
- RBAC permissions

### 2. Deploy Grafana

```bash
kubectl apply -f grafana-config.yaml
```

This creates:
- Grafana deployment
- Grafana service (NodePort 30030)
- Pre-configured Prometheus datasource
- Training dashboard

### 3. Access Dashboards

**Prometheus**:
```bash
# Get Prometheus URL
kubectl get svc prometheus -n monitoring

# Access via NodePort
http://localhost:30090

# Or port-forward
kubectl port-forward svc/prometheus 9090:9090 -n monitoring
# Then: http://localhost:9090
```

**Grafana**:
```bash
# Get Grafana URL
kubectl get svc grafana -n monitoring

# Access via NodePort
http://localhost:30030

# Or port-forward
kubectl port-forward svc/grafana 3000:3000 -n monitoring
# Then: http://localhost:3000

# Login: admin / admin (change password on first login)
```

## Available Metrics

### Kubernetes Metrics

**Pod Status**:
```promql
# Count of running training pods
count(kube_pod_info{namespace="training", pod=~"training-job.*"})

# Pod status by job
kube_pod_status_phase{namespace="training"}
```

**Resource Usage**:
```promql
# CPU usage by pod
rate(container_cpu_usage_seconds_total{namespace="training", pod=~"training-job.*"}[5m])

# Memory usage by pod
container_memory_usage_bytes{namespace="training", pod=~"training-job.*"}

# GPU utilization (requires NVIDIA Device Plugin)
nvidia_gpu_duty_cycle{namespace="training"}

# GPU memory usage
nvidia_gpu_memory_used_bytes{namespace="training"}
```

### Training Metrics (Custom)

These are sent by TrainingLogger to Backend API and can be exposed via Prometheus:

```promql
# Training loss by job
training_loss{job_id="123"}

# Training accuracy
training_accuracy{job_id="123"}

# Epoch duration
training_epoch_duration_seconds{job_id="123"}
```

## Grafana Dashboards

### Pre-installed Dashboard

Navigate to:
- Grafana → Dashboards → "Training Jobs Monitoring"

**Panels**:
1. Active Training Jobs (stat)
2. GPU Utilization (graph)
3. Memory Usage (graph)
4. CPU Usage (graph)
5. Training Status (table)

### Import Additional Dashboards

**Kubernetes Cluster Monitoring**:
- Dashboard ID: 6417
- URL: https://grafana.com/grafana/dashboards/6417

**Node Exporter Full**:
- Dashboard ID: 1860
- URL: https://grafana.com/grafana/dashboards/1860

**Steps**:
1. Go to Grafana → Dashboards → Import
2. Enter Dashboard ID
3. Select Prometheus datasource
4. Click Import

## Custom Metrics from Backend

### Add Prometheus Exporter to Backend

**Install**:
```bash
pip install prometheus-fastapi-instrumentator==6.1.0
```

**Update main.py**:
```python
from prometheus_fastapi_instrumentator import Instrumentator
from fastapi import FastAPI

app = FastAPI()

# Add Prometheus metrics
Instrumentator().instrument(app).expose(app, endpoint="/metrics")
```

**Metrics exposed at**: `http://backend:8000/metrics`

### Custom Training Metrics

**Add to TrainingLogger** (`app/utils/training_logger.py`):

```python
from prometheus_client import Counter, Gauge, Histogram

# Define metrics
training_jobs_total = Counter(
    'training_jobs_total',
    'Total training jobs started',
    ['framework', 'task_type']
)

training_job_duration = Histogram(
    'training_job_duration_seconds',
    'Training job duration',
    ['job_id', 'status']
)

training_loss = Gauge(
    'training_loss',
    'Current training loss',
    ['job_id', 'epoch']
)

# Update metrics
class TrainingLogger:
    def start_job(self, job_id, framework, task_type):
        training_jobs_total.labels(
            framework=framework,
            task_type=task_type
        ).inc()

    def log_metrics(self, job_id, epoch, metrics):
        if 'loss' in metrics:
            training_loss.labels(
                job_id=str(job_id),
                epoch=str(epoch)
            ).set(metrics['loss'])
```

## Alerting

### Configure Alert Rules

**Create alert-rules.yaml**:
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: prometheus-alerts
  namespace: monitoring
data:
  alerts.yml: |
    groups:
      - name: training_alerts
        interval: 30s
        rules:
          # Alert if training job fails
          - alert: TrainingJobFailed
            expr: kube_pod_status_phase{namespace="training", phase="Failed"} > 0
            for: 1m
            labels:
              severity: warning
            annotations:
              summary: "Training job failed"
              description: "Pod {{ $labels.pod }} in namespace {{ $labels.namespace }} has failed"

          # Alert if GPU utilization is low
          - alert: LowGPUUtilization
            expr: nvidia_gpu_duty_cycle < 10
            for: 5m
            labels:
              severity: info
            annotations:
              summary: "Low GPU utilization"
              description: "GPU {{ $labels.gpu }} utilization is below 10% for 5 minutes"

          # Alert if memory usage is high
          - alert: HighMemoryUsage
            expr: container_memory_usage_bytes{namespace="training"} / container_spec_memory_limit_bytes{namespace="training"} > 0.9
            for: 2m
            labels:
              severity: warning
            annotations:
              summary: "High memory usage"
              description: "Pod {{ $labels.pod }} is using over 90% of memory limit"
```

**Apply**:
```bash
kubectl apply -f alert-rules.yaml
```

**Update Prometheus config** to include alert rules:
```yaml
rule_files:
  - '/etc/prometheus/alerts.yml'
```

## Troubleshooting

### Prometheus Not Scraping Pods

**Check ServiceAccount permissions**:
```bash
kubectl auth can-i list pods --as=system:serviceaccount:monitoring:prometheus -n training
```

Should return `yes`. If not, check RBAC configuration.

### No GPU Metrics

**Install NVIDIA Device Plugin**:
```bash
kubectl create -f https://raw.githubusercontent.com/NVIDIA/k8s-device-plugin/main/nvidia-device-plugin.yml
```

**Verify GPU nodes**:
```bash
kubectl get nodes -o json | jq '.items[].status.allocatable."nvidia.com/gpu"'
```

### Grafana Dashboard Not Loading

**Check Prometheus datasource**:
1. Grafana → Configuration → Data Sources
2. Click "Prometheus"
3. Click "Test" button
4. Should show "Data source is working"

**Check logs**:
```bash
kubectl logs -f deployment/grafana -n monitoring
```

## Example Queries

### Training Job Metrics

**Job success rate**:
```promql
sum(kube_pod_status_phase{namespace="training", phase="Succeeded"}) /
sum(kube_pod_status_phase{namespace="training"}) * 100
```

**Average job duration**:
```promql
avg(kube_pod_completion_time{namespace="training"} - kube_pod_start_time{namespace="training"})
```

**Jobs by framework**:
```promql
count by (label_framework) (kube_pod_labels{namespace="training"})
```

### Resource Usage

**Total GPU hours used**:
```promql
sum(nvidia_gpu_duty_cycle{namespace="training"} / 100) * (time() - min(kube_pod_start_time{namespace="training"}))
```

**Peak memory usage**:
```promql
max_over_time(container_memory_usage_bytes{namespace="training"}[24h])
```

## Cleanup

```bash
# Delete monitoring stack
kubectl delete namespace monitoring

# Delete just Prometheus
kubectl delete -f prometheus-config.yaml

# Delete just Grafana
kubectl delete -f grafana-config.yaml
```

## Production Considerations

1. **Persistent Storage**: Use PersistentVolumes for Prometheus and Grafana
   ```yaml
   volumeClaimTemplates:
     - metadata:
         name: prometheus-storage
       spec:
         accessModes: ["ReadWriteOnce"]
         resources:
           requests:
             storage: 50Gi
   ```

2. **High Availability**: Run multiple Prometheus replicas

3. **Security**:
   - Change default Grafana password
   - Enable authentication for Prometheus
   - Use TLS for external access
   - Restrict RBAC permissions

4. **Retention**: Configure data retention policy
   ```
   --storage.tsdb.retention.time=30d
   --storage.tsdb.retention.size=50GB
   ```

5. **Alerting**: Configure AlertManager for notifications
   - Email
   - Slack
   - PagerDuty
   - Webhook

## Next Steps

- Configure AlertManager for notifications
- Add custom training metrics
- Create team-specific dashboards
- Set up long-term metrics storage (Thanos)
