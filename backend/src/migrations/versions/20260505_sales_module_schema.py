"""Add complete Sales module schema.

Revision ID: 20260505_sales_module_schema
Revises: None
Create Date: 2026-05-05 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op

revision: str = "20260505_sales_module_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS sales_program (
            id VARCHAR(36) PRIMARY KEY,
            user_id VARCHAR(36) NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
            name VARCHAR(255) NOT NULL,
            description TEXT,
            mode VARCHAR(20) NOT NULL DEFAULT 'sales',
            system_prompt TEXT,
            welcome_message VARCHAR(500),
            knowledge_base_id VARCHAR(36),
            business_name VARCHAR(255),
            business_address VARCHAR(500),
            business_phone VARCHAR(20),
            logo_url VARCHAR(500),
            banner_url VARCHAR(500),
            display_config JSONB,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """
    )
    op.execute("ALTER TABLE sales_program ADD COLUMN IF NOT EXISTS logo_url VARCHAR(500);")
    op.execute("ALTER TABLE sales_program ADD COLUMN IF NOT EXISTS banner_url VARCHAR(500);")
    op.execute("ALTER TABLE sales_program ADD COLUMN IF NOT EXISTS system_prompt TEXT;")
    op.execute("ALTER TABLE sales_program ADD COLUMN IF NOT EXISTS welcome_message VARCHAR(500);")
    op.execute("ALTER TABLE sales_program ADD COLUMN IF NOT EXISTS knowledge_base_id VARCHAR(36);")
    op.execute("ALTER TABLE sales_program ADD COLUMN IF NOT EXISTS display_config JSONB;")
    op.execute("CREATE INDEX IF NOT EXISTS ix_sales_program_user_id ON sales_program(user_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_sales_program_is_active ON sales_program(is_active);")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS product (
            id VARCHAR(36) PRIMARY KEY,
            sales_program_id VARCHAR(36) NOT NULL REFERENCES sales_program(id) ON DELETE CASCADE,
            name VARCHAR(255) NOT NULL,
            description TEXT,
            price INTEGER NOT NULL DEFAULT 0,
            original_price INTEGER,
            image_url VARCHAR(500),
            images JSONB,
            category VARCHAR(100),
            sku VARCHAR(50),
            sort_order INTEGER NOT NULL DEFAULT 0,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            extra_info JSONB,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """
    )
    op.execute("ALTER TABLE product ADD COLUMN IF NOT EXISTS images JSONB;")
    op.execute("ALTER TABLE product ADD COLUMN IF NOT EXISTS extra_info JSONB;")
    op.execute("ALTER TABLE product ADD COLUMN IF NOT EXISTS original_price INTEGER;")
    op.execute("ALTER TABLE product ADD COLUMN IF NOT EXISTS sort_order INTEGER NOT NULL DEFAULT 0;")
    op.execute("ALTER TABLE product ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE;")
    op.execute("CREATE INDEX IF NOT EXISTS ix_product_sales_program_id ON product(sales_program_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_product_category ON product(category);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_product_is_active ON product(is_active);")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS sales_lead (
            id VARCHAR(36) PRIMARY KEY,
            user_id VARCHAR(36) NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
            product_name VARCHAR(255) NOT NULL,
            agent_id VARCHAR(36) REFERENCES agent(id) ON DELETE SET NULL,
            customer_name VARCHAR(255),
            customer_phone VARCHAR(50),
            customer_email VARCHAR(255),
            product_id VARCHAR(36) REFERENCES product(id) ON DELETE SET NULL,
            inquiry_text TEXT,
            ai_response TEXT,
            source VARCHAR(50) NOT NULL DEFAULT 'voice',
            device_id VARCHAR(100),
            session_id VARCHAR(100),
            status VARCHAR(20) NOT NULL DEFAULT 'new',
            priority INTEGER NOT NULL DEFAULT 0,
            notes TEXT,
            notified BOOLEAN NOT NULL DEFAULT FALSE,
            notified_at TIMESTAMPTZ,
            extra_data JSONB,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """
    )
    op.execute("ALTER TABLE sales_lead ADD COLUMN IF NOT EXISTS extra_data JSONB;")
    op.execute("ALTER TABLE sales_lead ADD COLUMN IF NOT EXISTS notified BOOLEAN NOT NULL DEFAULT FALSE;")
    op.execute("ALTER TABLE sales_lead ADD COLUMN IF NOT EXISTS notified_at TIMESTAMPTZ;")
    op.execute("CREATE INDEX IF NOT EXISTS ix_sales_lead_user_id ON sales_lead(user_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_sales_lead_agent_id ON sales_lead(agent_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_sales_lead_product_id ON sales_lead(product_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_sales_lead_status ON sales_lead(status);")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS sales_session (
            id VARCHAR(36) PRIMARY KEY,
            user_id VARCHAR(36) NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
            state VARCHAR(40) NOT NULL DEFAULT 'idle',
            agent_id VARCHAR(36) REFERENCES agent(id) ON DELETE SET NULL,
            sales_program_id VARCHAR(36) REFERENCES sales_program(id) ON DELETE SET NULL,
            device_id VARCHAR(100),
            session_id VARCHAR(100),
            source VARCHAR(50) NOT NULL DEFAULT 'voice',
            last_product_id VARCHAR(36) REFERENCES product(id) ON DELETE SET NULL,
            last_product_name VARCHAR(255),
            lead_id VARCHAR(36) REFERENCES sales_lead(id) ON DELETE SET NULL,
            score INTEGER NOT NULL DEFAULT 0,
            needs JSONB,
            objections JSONB,
            extra_data JSONB,
            started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            last_event_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            captured_at TIMESTAMPTZ
        );
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_sales_session_user_id ON sales_session(user_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_sales_session_state ON sales_session(state);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_sales_session_agent_id ON sales_session(agent_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_sales_session_sales_program_id ON sales_session(sales_program_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_sales_session_device_id ON sales_session(device_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_sales_session_session_id ON sales_session(session_id);")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS sales_analytics_event (
            id VARCHAR(36) PRIMARY KEY,
            user_id VARCHAR(36) NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
            event_type VARCHAR(50) NOT NULL,
            agent_id VARCHAR(36) REFERENCES agent(id) ON DELETE SET NULL,
            sales_program_id VARCHAR(36) REFERENCES sales_program(id) ON DELETE SET NULL,
            product_id VARCHAR(36) REFERENCES product(id) ON DELETE SET NULL,
            lead_id VARCHAR(36) REFERENCES sales_lead(id) ON DELETE SET NULL,
            device_id VARCHAR(100),
            session_id VARCHAR(100),
            display_message_id VARCHAR(100),
            payload JSONB,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_sales_analytics_event_user_id ON sales_analytics_event(user_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_sales_analytics_event_event_type ON sales_analytics_event(event_type);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_sales_analytics_event_agent_id ON sales_analytics_event(agent_id);")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_sales_analytics_event_sales_program_id ON sales_analytics_event(sales_program_id);"
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_sales_analytics_event_product_id ON sales_analytics_event(product_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_sales_analytics_event_lead_id ON sales_analytics_event(lead_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_sales_analytics_event_device_id ON sales_analytics_event(device_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_sales_analytics_event_session_id ON sales_analytics_event(session_id);")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_sales_analytics_event_display_message_id ON sales_analytics_event(display_message_id);"
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS sales_display_ack (
            id VARCHAR(36) PRIMARY KEY,
            user_id VARCHAR(36) NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
            device_id VARCHAR(100) NOT NULL,
            message_id VARCHAR(100) NOT NULL,
            status VARCHAR(40) NOT NULL DEFAULT 'rendered',
            session_id VARCHAR(100),
            media_type VARCHAR(30),
            product_id VARCHAR(36) REFERENCES product(id) ON DELETE SET NULL,
            banner_id VARCHAR(100),
            error_message VARCHAR(500),
            payload JSONB,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_sales_display_ack_user_id ON sales_display_ack(user_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_sales_display_ack_device_id ON sales_display_ack(device_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_sales_display_ack_message_id ON sales_display_ack(message_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_sales_display_ack_status ON sales_display_ack(status);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_sales_display_ack_session_id ON sales_display_ack(session_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_sales_display_ack_product_id ON sales_display_ack(product_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_sales_display_ack_banner_id ON sales_display_ack(banner_id);")

    op.execute("ALTER TABLE agent ADD COLUMN IF NOT EXISTS enable_sales BOOLEAN NOT NULL DEFAULT FALSE;")
    op.execute("ALTER TABLE agent ADD COLUMN IF NOT EXISTS sales_program_ids JSONB DEFAULT '[]'::jsonb;")
    op.execute("ALTER TABLE agent ADD COLUMN IF NOT EXISTS banner_images JSONB DEFAULT '[]'::jsonb;")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS sales_display_ack;")
    op.execute("DROP TABLE IF EXISTS sales_analytics_event;")
    op.execute("DROP TABLE IF EXISTS sales_session;")
    op.execute("ALTER TABLE agent DROP COLUMN IF EXISTS banner_images;")
    op.execute("ALTER TABLE agent DROP COLUMN IF EXISTS sales_program_ids;")
    op.execute("ALTER TABLE agent DROP COLUMN IF EXISTS enable_sales;")
    op.execute("DROP TABLE IF EXISTS sales_lead;")
    op.execute("DROP TABLE IF EXISTS product;")
    op.execute("DROP TABLE IF EXISTS sales_program;")
