"""Mark Beetle and Omnie as inactive in robot_catalog."""

from src.core.supabase import get_supabase_client


def main():
    client = get_supabase_client()
    for name in ("Beetle", "Omnie"):
        result = (
            client.table("robot_catalog")
            .update({"active": False})
            .eq("name", name)
            .execute()
        )
        if result.data:
            print(f"✓ {name} set to inactive")
        else:
            print(f"✗ {name} not found")


if __name__ == "__main__":
    main()
