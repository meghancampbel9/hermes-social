#!/usr/bin/env bash
# provision-gcp.sh — Create 4 Hermes agent VMs on GCP
# No external IPs. SSH via IAP. Outbound via Cloud NAT.
#
# Usage:
#   export GCP_PROJECT=your-project-id
#   bash deploy/provision-gcp.sh

set -euo pipefail

PROJECT="${GCP_PROJECT:?Set GCP_PROJECT env var}"
REGION="europe-west3"
ZONE="europe-west3-a"
NETWORK="default"

echo "==> Enabling APIs..."
gcloud services enable compute.googleapis.com iap.googleapis.com \
  --project="$PROJECT"

echo "==> Creating firewall rule for IAP SSH..."
gcloud compute firewall-rules create allow-iap-ssh \
  --project="$PROJECT" \
  --allow=tcp:22 \
  --source-ranges=35.235.240.0/20 \
  --target-tags=hermes-agent \
  --description="SSH via IAP only — no public port 22" \
  --quiet || echo "Firewall rule already exists, skipping."

echo "==> Creating Cloud Router..."
gcloud compute routers create hermes-router \
  --project="$PROJECT" \
  --region="$REGION" \
  --network="$NETWORK" \
  --quiet || echo "Router already exists, skipping."

echo "==> Creating Cloud NAT (outbound internet for instances without external IP)..."
gcloud compute routers nats create hermes-nat \
  --project="$PROJECT" \
  --router=hermes-router \
  --region="$REGION" \
  --auto-allocate-nat-external-ips \
  --nat-all-subnet-ip-ranges \
  --quiet || echo "NAT already exists, skipping."

echo "==> Granting IAP Tunnel User role to current account..."
ACCOUNT=$(gcloud config get-value account)
gcloud projects add-iam-policy-binding "$PROJECT" \
  --member="user:$ACCOUNT" \
  --role="roles/iap.tunnelResourceAccessor" \
  --quiet

echo "==> Creating 4 Hermes agent instances..."
for i in 1 2 3 4; do
  echo "  -> hermes-agent-$i"
  gcloud compute instances create "hermes-agent-$i" \
    --project="$PROJECT" \
    --zone="$ZONE" \
    --machine-type=e2-standard-2 \
    --image-family=ubuntu-2204-lts \
    --image-project=ubuntu-os-cloud \
    --boot-disk-size=20GB \
    --boot-disk-type=pd-ssd \
    --no-address \
    --tags=hermes-agent \
    --scopes=cloud-platform \
    --quiet || echo "  hermes-agent-$i already exists, skipping."
done

echo ""
echo "Done. SSH into any instance with:"
echo "  gcloud compute ssh hermes-agent-1 --project=$PROJECT --zone=$ZONE --tunnel-through-iap"