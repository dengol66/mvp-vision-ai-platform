# PowerShell setup script for Kubernetes resources (Windows)
# Creates namespace, secrets, and configmaps for training jobs

param(
    [string]$Namespace = "training",
    [string]$BackendUrl = "http://backend-api:8000"
)

$ErrorActionPreference = "Stop"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Setting up Kubernetes Resources" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Namespace: $Namespace"
Write-Host "Backend URL: $BackendUrl"
Write-Host "==========================================" -ForegroundColor Cyan

# Create namespace
Write-Host ""
Write-Host "Creating namespace..." -ForegroundColor Yellow
kubectl create namespace $Namespace --dry-run=client -o yaml | kubectl apply -f -
Write-Host "✓ Namespace created/updated" -ForegroundColor Green

# Create R2 credentials secret
Write-Host ""
Write-Host "Creating R2 credentials secret..." -ForegroundColor Yellow

$endpoint = $env:AWS_S3_ENDPOINT_URL
$accessKey = $env:AWS_ACCESS_KEY_ID
$secretKey = $env:AWS_SECRET_ACCESS_KEY

if (-not $endpoint -or -not $accessKey -or -not $secretKey) {
    Write-Host "⚠ R2 credentials not found in environment variables" -ForegroundColor Yellow
    Write-Host "Please set: AWS_S3_ENDPOINT_URL, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY"
    Write-Host ""
    Write-Host "Creating placeholder secret (you can update later)" -ForegroundColor Yellow

    # Create placeholder secret
    kubectl create secret generic r2-credentials `
        --from-literal=endpoint=https://placeholder.r2.cloudflarestorage.com `
        --from-literal=access-key=placeholder `
        --from-literal=secret-key=placeholder `
        --namespace=$Namespace `
        --dry-run=client -o yaml | kubectl apply -f -
} else {
    kubectl create secret generic r2-credentials `
        --from-literal=endpoint=$endpoint `
        --from-literal=access-key=$accessKey `
        --from-literal=secret-key=$secretKey `
        --namespace=$Namespace `
        --dry-run=client -o yaml | kubectl apply -f -
    Write-Host "✓ R2 credentials secret created/updated" -ForegroundColor Green
}

# Create backend config configmap
Write-Host ""
Write-Host "Creating backend config..." -ForegroundColor Yellow
kubectl create configmap backend-config `
    --from-literal=api-url=$BackendUrl `
    --namespace=$Namespace `
    --dry-run=client -o yaml | kubectl apply -f -
Write-Host "✓ Backend config created/updated" -ForegroundColor Green

# Verify resources
Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Verifying Resources" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

Write-Host ""
Write-Host "Namespace:"
kubectl get namespace $Namespace

Write-Host ""
Write-Host "Secrets:"
kubectl get secrets -n $Namespace

Write-Host ""
Write-Host "ConfigMaps:"
kubectl get configmaps -n $Namespace

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Setup Complete!" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "To update R2 credentials later:"
Write-Host "  kubectl create secret generic r2-credentials \"
Write-Host "    --from-literal=endpoint=YOUR_ENDPOINT \"
Write-Host "    --from-literal=access-key=YOUR_ACCESS_KEY \"
Write-Host "    --from-literal=secret-key=YOUR_SECRET_KEY \"
Write-Host "    --namespace=$Namespace --dry-run=client -o yaml | kubectl apply -f -"
Write-Host ""
