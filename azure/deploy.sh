#!/usr/bin/env bash
# Panna — deploy the API to Azure Container Apps (event-driven, autoscaling).
#
# This is the "Best Azure Cloud Native Integration" artifact: a real, reproducible
# deploy that produces a public endpoint, not a slide.
#
# Prereqs (one-time):
#   az login
#   az extension add --name azd     # optional
#
# Per-deploy:
#   export AZURE_LOCATION="westeurope"
#   export FOUNDRY_ENDPOINT="https://<project>.services.ai.azure.com"
#   export FOUNDRY_API_KEY="<key>"          # never commit / never echo
#   export FOUNDRY_DEPLOYMENT="gpt-5.4"
#
# Run:
#   ./azure/deploy.sh
#
# It builds the API image, pushes to a (created) ACR, and deploys
# azure/panna-aca.bicep into a new resource group. Prints the public endpoint.
set -euo pipefail

cd "$(dirname "$0")/.."

: "${AZURE_LOCATION:=westeurope}"
: "${FOUNDRY_ENDPOINT:}"
: "${FOUNDRY_DEPLOYMENT:=gpt-5.4}"

ENV_NAME="panna$(date +%s | tail -c 6)"
RG="rg-${ENV_NAME}"
ACR="acr${ENV_NAME}"
IMAGE="${ACR}.azurecr.io/panna-api:latest"

if ! command -v az >/dev/null 2>&1; then
  echo "az CLI not found. Install: https://learn.microsoft.com/azure/cli/"
  exit 1
fi

echo "==> Provisioning resource group ${RG} in ${AZURE_LOCATION}"
az group create -n "${RG}" -l "${AZURE_LOCATION}" --output none

echo "==> Creating container registry ${ACR}"
az acr create -n "${ACR}" -g "${RG}" --sku Basic --admin-enabled true --output none
ACR_PAT="$(az acr credential show -n "${ACR}" -g "${RG}" --query password --output tsv)"

echo "==> Building API image (Dockerfile)"
docker build -t "${IMAGE}" .

echo "==> Pushing image to ACR"
docker push "${IMAGE}" >/dev/null

# secret value is passed on the CLI only (never written to a file / repo)
SECRET_ARG=""
if [ -n "${FOUNDRY_API_KEY:-}" ]; then
  SECRET_ARG="--parameters foundryApiKey=@$(printf '%s' "${FOUNDRY_API_KEY}")"
fi

echo "==> Deploying azure/panna-aca.bicep"
az deployment group create \
  -g "${RG}" \
  -n "panna-${ENV_NAME}" \
  -f azure/panna-aca.bicep \
  --parameters \
    environmentName="${ENV_NAME}" \
    image="${IMAGE}" \
    foundryEndpoint="${FOUNDRY_ENDPOINT}" \
    foundryDeployment="${FOUNDRY_DEPLOYMENT}" \
    ${SECRET_ARG:-foundryApiKey=none} \
  --output table

echo
echo "==> Done."
az deployment group show -g "${RG}" -n "panna-${ENV_NAME}" \
  --query properties.outputs.apiEndpoint.value --output tsv
echo
echo "Clean up:  az group delete -n ${RG} --yes --no-wait"
