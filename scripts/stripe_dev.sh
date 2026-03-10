#!/bin/bash
# stripe_dev.sh — Forward Stripe test webhooks to the local backend.
#
# Usage:
#   ./scripts/stripe_dev.sh
#
# Prerequisites:
#   - Stripe CLI installed (https://stripe.com/docs/stripe-cli#install)
#   - STRIPE_SECRET_KEY_TEST set in your .env (or exported in the shell)
#   - Backend running at localhost:8080
#
# After starting, copy the "whsec_..." value printed by the CLI and set it as:
#   STRIPE_WEBHOOK_SECRET_TEST=whsec_... in your .env file

set -e

# ---------------------------------------------------------------------------
# Load .env if it exists so STRIPE_SECRET_KEY_TEST is available
# ---------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$SCRIPT_DIR/../.env"
if [ -f "$ENV_FILE" ]; then
  # shellcheck disable=SC2046
  export $(grep -v '^#' "$ENV_FILE" | grep -v '^$' | xargs)
fi

# ---------------------------------------------------------------------------
# Check that stripe CLI is installed
# ---------------------------------------------------------------------------
if ! command -v stripe &> /dev/null; then
  echo ""
  echo "❌  Stripe CLI not found."
  echo ""
  echo "Install it:"
  echo "  macOS:   brew install stripe/stripe-cli/stripe"
  echo "  Linux:   https://stripe.com/docs/stripe-cli#install"
  echo "  Windows: https://stripe.com/docs/stripe-cli#install"
  echo ""
  exit 1
fi

# ---------------------------------------------------------------------------
# Require test key
# ---------------------------------------------------------------------------
if [ -z "$STRIPE_SECRET_KEY_TEST" ]; then
  echo ""
  echo "❌  STRIPE_SECRET_KEY_TEST is not set."
  echo ""
  echo "Add it to your .env file:"
  echo "  STRIPE_SECRET_KEY_TEST=sk_test_..."
  echo ""
  exit 1
fi

if [[ "$STRIPE_SECRET_KEY_TEST" != sk_test_* ]]; then
  echo ""
  echo "❌  STRIPE_SECRET_KEY_TEST does not look like a test key (expected sk_test_...)."
  echo ""
  exit 1
fi

# ---------------------------------------------------------------------------
# Start forwarding
# ---------------------------------------------------------------------------
echo ""
echo "🔗  Starting Stripe CLI webhook forwarding..."
echo "    → Local backend: http://localhost:8080/api/v1/webhooks/stripe"
echo ""
echo "📋  After startup, copy the 'whsec_...' value and set it in your .env:"
echo "    STRIPE_WEBHOOK_SECRET_TEST=whsec_..."
echo ""
echo "Press Ctrl+C to stop."
echo ""

stripe listen \
  --api-key "$STRIPE_SECRET_KEY_TEST" \
  --forward-to "localhost:8080/api/v1/webhooks/stripe"
