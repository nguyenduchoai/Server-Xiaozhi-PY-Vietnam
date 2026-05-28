"""
Agent-Centric Architecture Migration Script

This script adds new AI configuration columns to the agent table,
copies data from agent_template to agent, and prepares for the
removal of the agent_template table.

SAFE MIGRATION: Only ADDs columns, never removes existing ones.

Usage:
    python -m app.migrations.agent_centric_migration
    
Or via Docker:
    docker exec xiaozhi-backend python -m app.migrations.agent_centric_migration
"""

import asyncio

from sqlalchemy import text
from app.core.db.database import local_session
from app.core.logger import get_logger

logger = get_logger(__name__)
TAG = "AgentCentricMigration"


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
    """Run the agent-centric migration."""
    print(f"\n{'='*60}")
    print("🔄 Agent-Centric Architecture Migration")
    print(f"{'='*60}\n")
    
    async with local_session() as db:
        # ============ PHASE A: ADD COLUMNS ============
        print("📌 Phase A: Adding new columns to agent table...")
        
        new_columns = {
            "prompt": "TEXT",
            "ASR": "VARCHAR(100)",
            "LLM": "VARCHAR(100)", 
            "VLLM": "VARCHAR(100)",
            "TTS": "VARCHAR(100)",
            "tts_voice": "VARCHAR(100)",
            "Memory": "VARCHAR(100)",
            "Intent": "VARCHAR(100)",
            "tools": "JSON",
            "summary_memory": "TEXT",
            "enable_memory": "BOOLEAN DEFAULT TRUE",
            "enable_knowledge_base": "BOOLEAN DEFAULT TRUE",
            "knowledge_base_ids": "JSON",
            "notebook_ids": "JSON",
            "source_template_id": "VARCHAR(36)",
        }
        
        added = 0
        skipped = 0
        for col_name, col_type in new_columns.items():
            exists = await check_column_exists(db, "agent", col_name.lower())
            if not exists:
                # Quote column names that are SQL reserved or uppercase
                quoted_col = f'"{col_name}"' if col_name[0].isupper() else col_name
                await db.execute(
                    text(f'ALTER TABLE agent ADD COLUMN {quoted_col} {col_type}')
                )
                print(f"  ✅ Added: agent.{col_name} ({col_type})")
                added += 1
            else:
                skipped += 1
        
        await db.commit()
        print(f"  → Added {added} columns, skipped {skipped} (already exist)\n")
        
        # ============ PHASE B: MIGRATE DATA ============
        print("📌 Phase B: Migrating data from agent_template → agent...")
        
        # Check if agent_template table exists
        result = await db.execute(
            text("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables 
                    WHERE table_name = 'agent_template'
                )
            """)
        )
        has_agent_template = result.scalar()
        
        if has_agent_template:
            # Count agents with empty config (need migration)
            count_result = await db.execute(
                text("""
                    SELECT COUNT(*) FROM agent a
                    WHERE a."LLM" IS NULL 
                    AND a.active_template_id IS NOT NULL
                """)
            )
            agents_to_migrate = count_result.scalar()
            print(f"  Found {agents_to_migrate} agents needing migration")
            
            if agents_to_migrate > 0:
                # Check which columns exist in agent_template
                at_columns_check = await db.execute(
                    text("""
                        SELECT column_name FROM information_schema.columns 
                        WHERE table_name = 'agent_template'
                    """)
                )
                at_columns = {row[0] for row in at_columns_check}
                
                # Build dynamic update query based on available columns
                set_clauses = []
                mappable_cols = [
                    ("prompt", "prompt"),
                    ("ASR", "ASR"),
                    ("LLM", "LLM"),
                    ("VLLM", "VLLM"),
                    ("TTS", "TTS"),
                    ("Memory", "Memory"),
                    ("Intent", "Intent"),
                    ("tools", "tools"),
                    ("summary_memory", "summary_memory"),
                    ("enable_memory", "enable_memory"),
                    ("enable_knowledge_base", "enable_knowledge_base"),
                ]
                
                for agent_col, at_col in mappable_cols:
                    if at_col.lower() in at_columns:
                        quoted_a = f'"{agent_col}"' if agent_col[0].isupper() else agent_col
                        quoted_at = f'"{at_col}"' if at_col[0].isupper() else at_col
                        set_clauses.append(f'{quoted_a} = at.{quoted_at}')
                
                if set_clauses:
                    update_sql = f"""
                        UPDATE agent a SET 
                            {', '.join(set_clauses)}
                        FROM agent_template at
                        WHERE at.agent_id = a.id
                        AND at.is_active = true
                        AND a."LLM" IS NULL
                    """
                    result = await db.execute(text(update_sql))
                    print(f"  ✅ Migrated {result.rowcount} agents from agent_template")
                else:
                    print("  ⚠️ No matching columns found in agent_template")
                
                # Also try to copy KB IDs from template
                try:
                    kb_result = await db.execute(
                        text("""
                            UPDATE agent a SET
                                knowledge_base_ids = t.knowledge_base_ids,
                                notebook_ids = t.notebook_ids
                            FROM template t
                            WHERE t.id = a.active_template_id
                            AND a.knowledge_base_ids IS NULL
                            AND t.knowledge_base_ids IS NOT NULL
                        """)
                    )
                    if kb_result.rowcount > 0:
                        print(f"  ✅ Copied KB/Notebook IDs for {kb_result.rowcount} agents")
                except Exception as e:
                    print(f"  ⚠️ KB migration skipped: {e}")
                
                await db.commit()
        else:
            print("  ℹ️ No agent_template table found, skipping data migration")
        
        # ============ PHASE C: ADD INDEXES ============
        print("\n📌 Phase C: Adding indexes...")
        
        indexes = [
            ("idx_agent_llm", "agent", '"LLM"'),
            ("idx_agent_tts", "agent", '"TTS"'),
            ("idx_agent_asr", "agent", '"ASR"'),
            ("idx_agent_source_template", "agent", "source_template_id"),
        ]
        
        for idx_name, table, column in indexes:
            try:
                await db.execute(
                    text(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table} ({column})")
                )
                print(f"  ✅ Index: {idx_name}")
            except Exception as e:
                print(f"  ⚠️ Index {idx_name} skipped: {e}")
        
        await db.commit()
        
        # ============ VERIFICATION ============
        print(f"\n{'='*60}")
        print("✅ VERIFICATION")
        print(f"{'='*60}")
        
        # Count agents with populated config
        result = await db.execute(
            text("""
                SELECT 
                    COUNT(*) as total,
                    COUNT("LLM") as with_llm,
                    COUNT("TTS") as with_tts,
                    COUNT(prompt) as with_prompt,
                    COUNT(source_template_id) as with_source
                FROM agent 
                WHERE is_deleted = false
            """)
        )
        row = result.fetchone()
        print(f"  Total agents: {row[0]}")
        print(f"  With LLM config: {row[1]}")
        print(f"  With TTS config: {row[2]}")
        print(f"  With prompt: {row[3]}")
        print(f"  With source_template: {row[4]}")
        
        print(f"\n{'='*60}")
        print("🎉 Migration completed successfully!")
        print(f"{'='*60}\n")


if __name__ == "__main__":
    asyncio.run(run_migration())
