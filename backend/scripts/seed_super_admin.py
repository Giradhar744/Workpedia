"""
Seed Super Admin Script
=======================
Run this ONCE after setting up the database to create the super admin user.

Usage (from backend/ folder with venv activated):
    python scripts/seed_super_admin.py

The super admin credentials are read from backend/.env:
    SUPER_ADMIN_EMAIL=admin@company.com
    SUPER_ADMIN_PASSWORD=YourStrongPassword123
    SUPER_ADMIN_NAME=Super Admin

Never run this twice — it checks if the super admin already exists.
"""

import asyncio
import sys
import os

# ── Make backend/ importable ─────────────────────────────────────────────────
# This script lives in backend/scripts/ so we need to add backend/ to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from core.database import AsyncSessionLocal, engine
from core.config import settings
from auth.models import User, UserRole
from auth.service import hash_password


async def seed_super_admin():
    """
    Creates the super admin user if one doesn't already exist.
    Safe to run multiple times — won't create duplicates.
    """
    async with AsyncSessionLocal() as db:
        try:
            # Step 1 — check if super admin already exists
            result = await db.execute(
                select(User).where(User.email == settings.SUPER_ADMIN_EMAIL)
            )
            existing = result.scalar_one_or_none()

            if existing:
                print(f"✅ Super admin already exists: {settings.SUPER_ADMIN_EMAIL}")
                print("   No changes made.")
                return

            # Step 2 — create super admin
            super_admin = User(
                email=settings.SUPER_ADMIN_EMAIL,
                hashed_password=hash_password(settings.SUPER_ADMIN_PASSWORD),
                name=settings.SUPER_ADMIN_NAME,
                role=UserRole.SUPER_ADMIN,
                is_active=True,
                is_suspended=False,
            )

            db.add(super_admin)
            await db.commit()
            await db.refresh(super_admin)

            # Step 3 — confirm success
            print("🎉 Super admin created successfully!")
            print(f"   Email   : {settings.SUPER_ADMIN_EMAIL}")
            print(f"   Name    : {settings.SUPER_ADMIN_NAME}")
            print(f"   Role    : {super_admin.role.value}")
            print(f"   ID      : {super_admin.id}")
            print()
            print("⚠️  Keep these credentials safe — store them in your password manager.")
            print("⚠️  Never commit your .env file to GitHub.")

        except Exception as e:
            await db.rollback()
            print(f"❌ Failed to create super admin: {e}")
            raise


async def main():
    print("─" * 50)
    print("  Workpedia — Seed Super Admin")
    print("─" * 50)
    print()

    await seed_super_admin()

    # always dispose the engine cleanly after script finishes
    # prevents hanging connections
    await engine.dispose()

    print()
    print("Done. You can now log in at POST /auth/login")


if __name__ == "__main__":
    asyncio.run(main())