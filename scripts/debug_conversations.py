"""Diagnostic script: check conversation ownership and chat history state."""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from src.core.supabase import get_supabase_client

client = get_supabase_client()

print("=" * 70)
print("PROFILES")
print("=" * 70)
profiles = client.table("profiles").select("id, user_id, email, created_at").execute()
for p in profiles.data:
    print(f"  profile_id={p['id'][:12]}...  email={p.get('email', 'N/A')}  created={p['created_at']}")

print()
print("=" * 70)
print("CONVERSATIONS (most recent 20)")
print("=" * 70)
convos = (
    client.table("conversations")
    .select("id, profile_id, session_id, title, phase, updated_at, created_at")
    .order("updated_at", desc=True)
    .limit(20)
    .execute()
)
for c in convos.data:
    pid = c.get("profile_id")
    sid = c.get("session_id")
    pid_str = pid[:12] + "..." if pid else "NULL"
    sid_str = sid[:12] + "..." if sid else "NULL"
    print(f"  conv_id={c['id'][:12]}...  profile_id={pid_str}  session_id={sid_str}  phase={c['phase']}  updated={c['updated_at']}")

print()
print("=" * 70)
print("MESSAGE COUNTS PER CONVERSATION")
print("=" * 70)
# Get all messages grouped by conversation
messages = (
    client.table("messages")
    .select("conversation_id, role")
    .execute()
)
from collections import Counter
conv_counts = Counter()
for m in messages.data:
    conv_counts[m["conversation_id"]] += 1

for conv_id, count in conv_counts.most_common(20):
    print(f"  conv_id={conv_id[:12]}...  messages={count}")

print()
print("=" * 70)
print("ORPHANED CONVERSATIONS (session_id set, no profile_id)")
print("=" * 70)
orphaned = [c for c in convos.data if c.get("session_id") and not c.get("profile_id")]
if orphaned:
    for c in orphaned:
        count = conv_counts.get(c["id"], 0)
        print(f"  conv_id={c['id'][:12]}...  session_id={c['session_id'][:12]}...  messages={count}  updated={c['updated_at']}")
else:
    print("  None found")

print()
print("=" * 70)
print("PROFILE → CONVERSATION MAPPING")
print("=" * 70)
profile_map = {}
for c in convos.data:
    pid = c.get("profile_id")
    if pid:
        profile_map.setdefault(pid, []).append(c)

for pid, cs in profile_map.items():
    email = next((p["email"] for p in profiles.data if p["id"] == pid), "unknown")
    print(f"  {email} (profile={pid[:12]}...):")
    for c in cs:
        count = conv_counts.get(c["id"], 0)
        print(f"    conv={c['id'][:12]}...  messages={count}  phase={c['phase']}  updated={c['updated_at']}")
