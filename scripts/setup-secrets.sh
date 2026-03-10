#!/bin/bash
# Setup secrets in Google Cloud Secret Manager for Cloud Run
# Usage: ./scripts/setup-secrets.sh [PROJECT_ID]

set -e

PROJECT_ID="${1:-$(gcloud config get-value project)}"

echo "🔐 Setting up secrets in Secret Manager for project: ${PROJECT_ID}"
echo ""

# Check if .env file exists
if [ ! -f .env ]; then
    echo "⚠️  Warning: .env file not found. You'll need to provide values manually."
    echo ""
fi

# Resolve the compute service account (project-number-compute@developer.gserviceaccount.com)
PROJECT_NUMBER=$(gcloud projects describe "${PROJECT_ID}" --format='value(projectNumber)' 2>/dev/null)
COMPUTE_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

# Function to create or update a secret and grant Cloud Run access
create_secret() {
    local secret_name=$1
    local description=$2
    local env_var=$3

    if [ -f .env ] && grep -q "^${env_var}=" .env; then
        local secret_value=$(grep "^${env_var}=" .env | cut -d '=' -f2- | sed 's/#.*//' | tr -d '"' | tr -d "'" | xargs)
        echo "📝 Creating/updating secret: ${secret_name}"
        echo "${secret_value}" | gcloud secrets create "${secret_name}" \
            --data-file=- \
            --project="${PROJECT_ID}" \
            --replication-policy="automatic" \
            2>/dev/null || \
        echo "${secret_value}" | gcloud secrets versions add "${secret_name}" \
            --data-file=- \
            --project="${PROJECT_ID}"
    else
        echo "⚠️  Secret ${secret_name} not found in .env. Creating empty secret."
        echo "   Please update it manually:"
        echo "   echo -n 'your-value' | gcloud secrets versions add ${secret_name} --data-file=- --project=${PROJECT_ID}"
        echo ""
    fi

    # Grant Cloud Run compute service account access (idempotent)
    if [ -n "${PROJECT_NUMBER}" ]; then
        gcloud secrets add-iam-policy-binding "${secret_name}" \
            --member="serviceAccount:${COMPUTE_SA}" \
            --role="roles/secretmanager.secretAccessor" \
            --project="${PROJECT_ID}" \
            > /dev/null 2>&1 && echo "   ✓ IAM granted to ${COMPUTE_SA}" || \
            echo "   ⚠️  IAM grant failed for ${secret_name} (may need secretmanager.admin role)"
    fi
}

# Create secrets
create_secret "supabase-url" "Supabase project URL" "SUPABASE_URL"
create_secret "supabase-secret-key" "Supabase secret key" "SUPABASE_SECRET_KEY"
create_secret "supabase-signing-key-jwk" "Supabase signing key JWK" "SUPABASE_SIGNING_KEY_JWK"
create_secret "openai-api-key" "OpenAI API key" "OPENAI_API_KEY"
create_secret "pinecone-api-key" "Pinecone API key" "PINECONE_API_KEY"
create_secret "pinecone-environment" "Pinecone environment" "PINECONE_ENVIRONMENT"
create_secret "stripe-secret-key" "Stripe secret API key" "STRIPE_SECRET_KEY"
create_secret "stripe-webhook-secret" "Stripe webhook signing secret" "STRIPE_WEBHOOK_SECRET"
create_secret "stripe-publishable-key" "Stripe publishable key" "STRIPE_PUBLISHABLE_KEY"
create_secret "gynger-api-key" "Gynger vendor API key" "GYNGER_API_KEY"
create_secret "gynger-webhook-secret" "Gynger webhook secret" "GYNGER_WEBHOOK_SECRET"
create_secret "gynger-checkout-base-url" "Gynger checkout redirect base URL" "GYNGER_CHECKOUT_BASE_URL"
create_secret "hubspot-access-token" "HubSpot Private App access token" "HUBSPOT_ACCESS_TOKEN"

echo ""
echo "✅ Secrets setup complete!"
echo ""
echo "📋 Next step: deploy with USE_SECRETS=true ./scripts/deploy-cloud-run.sh"

