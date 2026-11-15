#!/usr/bin/env bash
# Deploys one image to one environment. Rolls back by itself if the rollout fails.
# Usage: deploy.sh <staging|production> <image> <tag>
set -euo pipefail

ENVIRONMENT="${1:?usage: deploy.sh <staging|production> <image> <tag>}"
IMAGE="${2:?image is required, for example lijo/shopledger}"
TAG="${3:?tag is required}"
OVERLAY="k8s/overlays/${ENVIRONMENT}"

[[ -d "${OVERLAY}" ]] || {
  echo "unknown environment: ${ENVIRONMENT}" >&2
  exit 2
}

# Only this workspace copy changes. Git still holds the placeholder.
sed -i -e "s|newName: .*|newName: ${IMAGE}|" -e "s|newTag: .*|newTag: ${TAG}|" \
  "${OVERLAY}/kustomization.yaml"

kubectl apply -k "${OVERLAY}"
kubectl -n "${ENVIRONMENT}" rollout status statefulset/postgres --timeout=120s

if ! kubectl -n "${ENVIRONMENT}" rollout status deployment/shopledger --timeout=180s; then
  echo "rollout of ${TAG} failed, rolling back" >&2
  kubectl -n "${ENVIRONMENT}" get pods -l app=shopledger >&2 || true
  kubectl -n "${ENVIRONMENT}" rollout undo deployment/shopledger || true
  kubectl -n "${ENVIRONMENT}" rollout status deployment/shopledger --timeout=120s || true
  exit 1
fi
echo "${ENVIRONMENT} is running ${IMAGE}:${TAG}"
