#!/bin/bash
# Setup script for Kubernetes resources
# Creates namespace, secrets, and configmaps for training jobs

set -e

# Configuration
NAMESPACE="${K8S_NAMESPACE:-training}"
BACKEND_URL="${BACKEND_API_URL:-http://backend-api:8000}"

echo "=========================================="
echo "Setting up Kubernetes Resources"
echo "=========================================="
echo "Namespace: $NAMESPACE"
echo "Backend URL: $BACKEND_URL"
echo "=========================================="

# Create namespace
echo ""
echo "Creating namespace..."
kubectl create namespace $NAMESPACE --dry-run=client -o yaml | kubectl apply -f -
echo "✓ Namespace created/updated"

# Create R2 credentials secret
echo ""
echo "Creating R2 credentials secret..."

if [ -z "$AWS_S3_ENDPOINT_URL" ] || [ -z "$AWS_ACCESS_KEY_ID" ] || [ -z "$AWS_SECRET_ACCESS_KEY" ]; then
    echo "⚠ R2 credentials not found in environment variables"
    echo "Please set: AWS_S3_ENDPOINT_URL, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY"
    echo ""
    echo "Creating empty secret (you can update later with:"
    echo "  kubectl create secret generic r2-credentials \\"
    echo "    --from-literal=endpoint=YOUR_ENDPOINT \\"
    echo "    --from-literal=access-key=YOUR_ACCESS_KEY \\"
    echo "    --from-literal=secret-key=YOUR_SECRET_KEY \\"
    echo "    --namespace=$NAMESPACE --dry-run=client -o yaml | kubectl apply -f -"
    echo ")"

    # Create placeholder secret
    kubectl create secret generic r2-credentials \
        --from-literal=endpoint=https://placeholder.r2.cloudflarestorage.com \
        --from-literal=access-key=placeholder \
        --from-literal=secret-key=placeholder \
        --namespace=$NAMESPACE \
        --dry-run=client -o yaml | kubectl apply -f -
else
    kubectl create secret generic r2-credentials \
        --from-literal=endpoint=$AWS_S3_ENDPOINT_URL \
        --from-literal=access-key=$AWS_ACCESS_KEY_ID \
        --from-literal=secret-key=$AWS_SECRET_ACCESS_KEY \
        --namespace=$NAMESPACE \
        --dry-run=client -o yaml | kubectl apply -f -
    echo "✓ R2 credentials secret created/updated"
fi

# Create backend config configmap
echo ""
echo "Creating backend config..."
kubectl create configmap backend-config \
    --from-literal=api-url=$BACKEND_URL \
    --namespace=$NAMESPACE \
    --dry-run=client -o yaml | kubectl apply -f -
echo "✓ Backend config created/updated"

# Verify resources
echo ""
echo "=========================================="
echo "Verifying Resources"
echo "=========================================="

echo ""
echo "Namespace:"
kubectl get namespace $NAMESPACE

echo ""
echo "Secrets:"
kubectl get secrets -n $NAMESPACE

echo ""
echo "ConfigMaps:"
kubectl get configmaps -n $NAMESPACE

echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "To update R2 credentials later:"
echo "  kubectl create secret generic r2-credentials \\"
echo "    --from-literal=endpoint=YOUR_ENDPOINT \\"
echo "    --from-literal=access-key=YOUR_ACCESS_KEY \\"
echo "    --from-literal=secret-key=YOUR_SECRET_KEY \\"
echo "    --namespace=$NAMESPACE --dry-run=client -o yaml | kubectl apply -f -"
echo ""
echo "To update backend URL:"
echo "  kubectl create configmap backend-config \\"
echo "    --from-literal=api-url=YOUR_BACKEND_URL \\"
echo "    --namespace=$NAMESPACE --dry-run=client -o yaml | kubectl apply -f -"
echo ""
