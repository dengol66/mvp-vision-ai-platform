# PowerShell build script for training Docker images (Windows)
# Usage: .\build.ps1 -Target [base|ultralytics|timm|all] -Push -Tag VERSION

param(
    [string]$Target = "all",
    [switch]$Push = $false,
    [string]$Tag = "v1.0",
    [string]$Registry = "ghcr.io/myorg"
)

$ErrorActionPreference = "Stop"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Building Training Docker Images" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Registry: $Registry"
Write-Host "Version: $Tag"
Write-Host "Target: $Target"
Write-Host "Push: $Push"
Write-Host "==========================================" -ForegroundColor Cyan

# Function to build image
function Build-Image {
    param(
        [string]$Name,
        [string]$Dockerfile
    )

    $ImageName = "${Registry}/trainer-${Name}:${Tag}"
    $LatestName = "${Registry}/trainer-${Name}:latest"

    Write-Host ""
    Write-Host "Building $Name..." -ForegroundColor Yellow
    Write-Host "Image: $ImageName"

    # Build from project root
    Push-Location "$PSScriptRoot\..\..\..\"

    try {
        docker build `
            -f "mvp/training/docker/$Dockerfile" `
            -t $ImageName `
            -t $LatestName `
            .

        if ($LASTEXITCODE -eq 0) {
            Write-Host "✓ Successfully built $ImageName" -ForegroundColor Green
        } else {
            throw "Failed to build $Name"
        }

        # Push if requested
        if ($Push) {
            Write-Host "Pushing $ImageName..." -ForegroundColor Yellow
            docker push $ImageName
            docker push $LatestName
            Write-Host "✓ Pushed $ImageName" -ForegroundColor Green
        }
    } finally {
        Pop-Location
    }
}

# Build base image
if ($Target -eq "base" -or $Target -eq "all") {
    Build-Image -Name "base" -Dockerfile "Dockerfile.base"
}

# Build ultralytics image
if ($Target -eq "ultralytics" -or $Target -eq "all") {
    Build-Image -Name "ultralytics" -Dockerfile "Dockerfile.ultralytics"
}

# Build timm image
if ($Target -eq "timm" -or $Target -eq "all") {
    Build-Image -Name "timm" -Dockerfile "Dockerfile.timm"
}

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Build Complete!" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Built images:"
docker images | Select-String "trainer-" | Select-Object -First 10

Write-Host ""
Write-Host "To test an image locally:"
Write-Host "  docker run --rm ${Registry}/trainer-ultralytics:${Tag} --help"
Write-Host ""
Write-Host "To load into Kind cluster:"
Write-Host "  kind load docker-image ${Registry}/trainer-ultralytics:${Tag}"
Write-Host ""
