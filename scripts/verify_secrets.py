"""
Verify that GCP Secret Manager values match local .env values.
Compares SHA-256 hashes — never prints actual secret content.
"""

import hashlib
import subprocess
import sys
from pathlib import Path
from typing import Optional

# Mapping: GCP secret name → .env key name
SECRET_MAP = {
    "gynger-api-key": "GYNGER_API_KEY",
    "gynger-checkout-base-url": "GYNGER_CHECKOUT_BASE_URL",
    "gynger-webhook-secret": "GYNGER_WEBHOOK_SECRET",
    "hubspot-access-token": "HUBSPOT_ACCESS_TOKEN",
    "openai-api-key": "OPENAI_API_KEY",
    "pinecone-api-key": "PINECONE_API_KEY",
    "pinecone-environment": "PINECONE_ENVIRONMENT",
    "resend-api-key": "RESEND_API_KEY",
    "stripe-secret-key": "STRIPE_SECRET_KEY",
    "stripe-secret-key-test": "STRIPE_SECRET_KEY_TEST",
    "stripe-webhook-secret": "STRIPE_WEBHOOK_SECRET",
    "stripe-webhook-secret-test": "STRIPE_WEBHOOK_SECRET_TEST",
    "supabase-secret-key": "SUPABASE_SECRET_KEY",
    "supabase-signing-key-jwk": "SUPABASE_SIGNING_KEY_JWK",
    "supabase-url": "SUPABASE_URL",
}


def sha256(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def load_env(env_path: Path) -> dict[str, str]:
    """Parse .env file into dict (keys only for mapped secrets)."""
    env = {}
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip("'\"")
        env[key] = value
    return env


def fetch_gcp_secret(name: str) -> Optional[str]:
    """Fetch latest version of a GCP secret."""
    try:
        result = subprocess.run(
            ["gcloud", "secrets", "versions", "access", "latest", f"--secret={name}"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode == 0:
            return result.stdout.rstrip("\n")
        return None
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None


def main():
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.exists():
        print(f"ERROR: .env not found at {env_path}")
        sys.exit(1)

    env = load_env(env_path)
    matches = 0
    mismatches = 0
    skipped = 0

    print(f"{'GCP Secret':<30} {'Status':<12} {'Detail'}")
    print("-" * 72)

    for gcp_name, env_key in sorted(SECRET_MAP.items()):
        env_value = env.get(env_key)
        if not env_value:
            print(f"{gcp_name:<30} {'SKIP':<12} .env key {env_key} not set")
            skipped += 1
            continue

        gcp_value = fetch_gcp_secret(gcp_name)
        if gcp_value is None:
            print(f"{gcp_name:<30} {'GCP ERROR':<12} could not fetch from Secret Manager")
            skipped += 1
            continue

        env_hash = sha256(env_value)
        gcp_hash = sha256(gcp_value)

        if env_hash == gcp_hash:
            print(f"{gcp_name:<30} {'MATCH':<12} sha256: ...{env_hash[-8:]}")
            matches += 1
        else:
            print(f"{gcp_name:<30} {'MISMATCH':<12} .env ...{env_hash[-8:]} ≠ gcp ...{gcp_hash[-8:]}")
            mismatches += 1

    print("-" * 72)
    print(f"Results: {matches} match, {mismatches} mismatch, {skipped} skipped")

    if mismatches > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
