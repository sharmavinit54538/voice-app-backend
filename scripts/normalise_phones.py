"""
One-off Python script to scan database for duplicate lead phone numbers,
report duplicates without deleting them, and optionally normalise all rows.

Usage:
    python -m scripts.normalise_phones --dry-run
    python -m scripts.normalise_phones --apply
"""

import argparse
import asyncio
from collections import defaultdict
from sqlalchemy.future import select
from app.core.database import AsyncSessionLocal
from app.core.phone import normalize_phone_number
from app.models.lead import Lead


async def check_and_normalise_leads(apply_changes: bool = False):
    print("Connecting to database and scanning leads...")
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Lead))
        leads = result.scalars().all()
        print(f"Total leads found: {len(leads)}")

        phone_groups = defaultdict(list)
        invalid_phones = []

        for lead in leads:
            try:
                norm = normalize_phone_number(lead.phone)
                phone_groups[norm].append(lead)
            except Exception as e:
                invalid_phones.append((lead.id, lead.name, lead.phone, str(e)))

        duplicates = {p: items for p, items in phone_groups.items() if len(items) > 1}

        if invalid_phones:
            print("\n[!] WARNING: Found leads with un-parseable phone numbers:")
            for lid, name, phone, err in invalid_phones:
                print(f"    - Lead ID={lid}, Name='{name}', Phone='{phone}' -> Error: {err}")

        if duplicates:
            print("\n[!] DUPLICATES DETECTED:")
            print(f"Found {len(duplicates)} phone numbers with multiple lead records:\n")
            for norm_phone, items in duplicates.items():
                print(f"  Normalized Phone: {norm_phone} ({len(items)} records)")
                for item in items:
                    print(f"    - ID: {item.id}, Name: {item.name}, Original Phone: '{item.phone}', Created: {item.created_at}")
            print("\n[!] Cannot automatically resolve duplicates. Please resolve conflicting records manually before applying unique constraints.")
            return

        print("\n[✓] No duplicate lead phone numbers detected!")

        if apply_changes:
            print("\nNormalising lead phone numbers in database...")
            updated_count = 0
            for norm_phone, items in phone_groups.items():
                for item in items:
                    if item.phone != norm_phone:
                        item.phone = norm_phone
                        updated_count += 1
            await session.commit()
            print(f"[✓] Successfully updated and normalised {updated_count} lead phone numbers.")
        else:
            print("\nRun with '--apply' to update rows in the database once verified.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Normalise lead phone numbers and report duplicates.")
    parser.add_argument("--apply", action="store_true", help="Apply normalization updates to the database")
    args = parser.parse_args()

    asyncio.run(check_and_normalise_leads(apply_changes=args.apply))
