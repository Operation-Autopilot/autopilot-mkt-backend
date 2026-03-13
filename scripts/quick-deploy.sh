#!/bin/bash
# Quick deploy to Cloud Run using local Docker build (leverages layer cache)
# ~30-40 seconds for code-only changes vs ~5 minutes with Cloud Build
#
# Usage: ./scripts/quick-deploy.sh [SERVICE_NAME] [REGION] [PROJECT_ID]

set -e

# Configuration (same defaults as deploy-cloud-run.sh)
SERVICE_NAME="${1:-autopilot-api}"
REGION="${2:-us-central1}"
PROJECT_ID="${3:-$(gcloud config get-value project)}"
REPOSITORY="${REPOSITORY:-docker-repo}"
IMAGE_NAME="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/${SERVICE_NAME}"
TAG="${TAG:-latest}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${PROJECT_ROOT}"

echo "⚡ Quick deploy to Cloud Run (local build)"
echo "   Service: ${SERVICE_NAME}"
echo "   Image:   ${IMAGE_NAME}:${TAG}"
echo ""

# Ensure Docker is authenticated with Artifact Registry (idempotent, ~1s)
gcloud auth configure-docker "${REGION}-docker.pkg.dev" --quiet 2>/dev/null

# Step 1: Build locally (cached layers make this ~2s for code-only changes)
echo "📦 Building Docker image locally..."
BUILD_START=$(date +%s)
docker build --platform linux/amd64 -t "${IMAGE_NAME}:${TAG}" .
BUILD_END=$(date +%s)
echo "   ✓ Built in $((BUILD_END - BUILD_START))s"

# Step 2: Push to Artifact Registry
echo "🔼 Pushing to Artifact Registry..."
PUSH_START=$(date +%s)
docker push "${IMAGE_NAME}:${TAG}"
PUSH_END=$(date +%s)
echo "   ✓ Pushed in $((PUSH_END - PUSH_START))s"

# Step 3: Deploy to Cloud Run (just swaps the image, keeps existing env vars/secrets)
echo "🚢 Deploying to Cloud Run..."
DEPLOY_START=$(date +%s)
gcloud run deploy "${SERVICE_NAME}" \
  --image "${IMAGE_NAME}:${TAG}" \
  --region "${REGION}" \
  --project "${PROJECT_ID}" \
  --platform managed \
  --allow-unauthenticated
DEPLOY_END=$(date +%s)
echo "   ✓ Deployed in $((DEPLOY_END - DEPLOY_START))s"

TOTAL=$((DEPLOY_END - BUILD_START))
echo ""
echo "✅ Done in ${TOTAL}s"
echo ""
echo "🌐 Service URL:"
gcloud run services describe "${SERVICE_NAME}" --region "${REGION}" --project "${PROJECT_ID}" --format="value(status.url)"
