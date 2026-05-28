import asyncio
from app.core.security import get_password_hash
from app.core.db.database import async_engine
from sqlalchemy import text

async def create():
    hashed = get_password_hash("1232123#12321")
    async with async_engine.begin() as conn:
        res = await conn.execute(text("SELECT id FROM \"user\" WHERE email = 'nguyenduchoai@gmail.com'"))
        if not res.first():
            import uuid
            user_id = str(uuid.uuid4())
            from datetime import datetime
            now = datetime.utcnow()
            await conn.execute(text("""
                INSERT INTO "user" (id, email, hashed_password, is_superuser, full_name, is_active, created_at, updated_at)
                VALUES (:id, :email, :pw, :super, :name, :active, :created, :updated)
            """), {"id": user_id, "email": "nguyenduchoai@gmail.com", "pw": hashed, "super": True, "name": "Admin", "active": True, "created": now, "updated": now})
            print("Admin user created successfully via SQL")
        else:
            print("Admin user already exists")

asyncio.run(create())
