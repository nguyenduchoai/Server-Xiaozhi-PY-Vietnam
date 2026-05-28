"""
Migration v006: Agent Feature Modules

Adds:
1. sales_program table - Chương trình bán hàng
2. meeting_room table - Phòng họp / Phòng ban
3. Agent fields: enable_education, enable_sales, enable_meeting, 
   course_ids, sales_program_ids, meeting_room_ids
"""

import asyncio
from app.core.db.database import async_get_db_session
from app.core.logger import setup_logging

logger = setup_logging()
TAG = "migration_v006"


async def run_migration():
    """Run the Feature Modules migration."""
    async with async_get_db_session() as db:
        conn = await db.connection()
        raw = conn.connection  # underlying asyncpg connection
        
        # 1. Create sales_program table
        await raw.execute("""
            CREATE TABLE IF NOT EXISTS sales_program (
                id VARCHAR(36) PRIMARY KEY,
                user_id VARCHAR(36) NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
                name VARCHAR(255) NOT NULL,
                description TEXT,
                mode VARCHAR(20) NOT NULL DEFAULT 'sales',
                system_prompt TEXT,
                knowledge_base_id VARCHAR(36),
                welcome_message VARCHAR(500),
                business_name VARCHAR(255),
                business_address VARCHAR(500),
                business_phone VARCHAR(20),
                display_config JSONB,
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
            CREATE INDEX IF NOT EXISTS idx_sales_program_user_id ON sales_program(user_id);
            CREATE INDEX IF NOT EXISTS idx_sales_program_is_active ON sales_program(is_active);
        """)
        logger.bind(tag=TAG).info("✅ Created sales_program table")
        
        # 2. Create meeting_room table
        await raw.execute("""
            CREATE TABLE IF NOT EXISTS meeting_room (
                id VARCHAR(36) PRIMARY KEY,
                user_id VARCHAR(36) NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
                name VARCHAR(255) NOT NULL,
                department VARCHAR(100),
                description TEXT,
                default_language VARCHAR(10) NOT NULL DEFAULT 'vi',
                auto_extract_tasks BOOLEAN NOT NULL DEFAULT TRUE,
                auto_summarize BOOLEAN NOT NULL DEFAULT TRUE,
                notification_config JSONB,
                members JSONB,
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
            CREATE INDEX IF NOT EXISTS idx_meeting_room_user_id ON meeting_room(user_id);
            CREATE INDEX IF NOT EXISTS idx_meeting_room_is_active ON meeting_room(is_active);
        """)
        logger.bind(tag=TAG).info("✅ Created meeting_room table")
        
        # 3. Add feature module columns to agent table
        feature_columns = [
            ("enable_education", "BOOLEAN NOT NULL DEFAULT FALSE"),
            ("enable_sales", "BOOLEAN NOT NULL DEFAULT FALSE"),
            ("enable_meeting", "BOOLEAN NOT NULL DEFAULT FALSE"),
            ("course_ids", "JSONB DEFAULT '[]'"),
            ("sales_program_ids", "JSONB DEFAULT '[]'"),
            ("meeting_room_ids", "JSONB DEFAULT '[]'"),
        ]
        
        for col_name, col_type in feature_columns:
            try:
                await raw.execute(f"""
                    ALTER TABLE agent ADD COLUMN IF NOT EXISTS {col_name} {col_type};
                """)
                logger.bind(tag=TAG).info(f"✅ Added agent.{col_name}")
            except Exception as e:
                logger.bind(tag=TAG).debug(f"Column agent.{col_name} may already exist: {e}")
        
        await db.commit()
        logger.bind(tag=TAG).info("🎉 Migration v006 complete: Feature Modules")


if __name__ == "__main__":
    asyncio.run(run_migration())
