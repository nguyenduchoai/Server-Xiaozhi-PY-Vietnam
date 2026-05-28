"""
Agent Message Columns Migration Script

Adds the `device_id` and `audio_path` columns to the existing `agent_message`
table so chat history can record which device sent a message and where the
saved utterance audio (chat_history_conf=2) lives on disk.

SAFE MIGRATION: Only ADDs columns if they do not already exist.

Usage:
    python -m app.migrations.add_agent_message_columns

Or via Docker:
    docker exec xiaozhi-backend python -m app.migrations.add_agent_message_columns
"""

import asyncio

from sqlalchemy import text
from app.core.db.database import local_session
from app.core.logger import get_logger

logger = get_logger(__name__)
TAG = "AddAgentMessageColumns"


async def check_column_exists(db, table: str, column: str) -> bool:
    """Check if a column exists in a table."""
    result = await db.execute(
        text("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = :table AND column_name = :column
            )
        """),
        {"table": table, "column": column},
    )
    return result.scalar()


async def run_migration():
    """Add device_id and audio_path columns to agent_message."""
    print(f"\n{'='*60}")
    print("🔄 Agent Message Columns Migration")
    print(f"{'='*60}\n")

    async with local_session() as db:
        print("📌 Adding new columns to agent_message table...")

        new_columns = {
            "device_id": "VARCHAR(64)",
            "audio_path": "VARCHAR(255)",
        }

        added = 0
        skipped = 0
        for col_name, col_type in new_columns.items():
            exists = await check_column_exists(db, "agent_message", col_name)
            if not exists:
                await db.execute(
                    text(f"ALTER TABLE agent_message ADD COLUMN {col_name} {col_type}")
                )
                print(f"  ✅ Added: agent_message.{col_name} ({col_type})")
                added += 1
            else:
                print(f"  ⏭️  Skipped: agent_message.{col_name} (already exists)")
                skipped += 1

        await db.commit()
        print(f"  → Added {added} columns, skipped {skipped} (already exist)\n")

        # Index for device_id lookups (idempotent)
        try:
            await db.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_agent_message_device_id "
                    "ON agent_message (device_id)"
                )
            )
            print("  ✅ Index: idx_agent_message_device_id")
        except Exception as e:
            print(f"  ⚠️ Index idx_agent_message_device_id skipped: {e}")

        await db.commit()

        print(f"\n{'='*60}")
        print("🎉 Migration completed successfully!")
        print(f"{'='*60}\n")


if __name__ == "__main__":
    asyncio.run(run_migration())
