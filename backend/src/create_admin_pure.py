import asyncio
import bcrypt
from sqlalchemy import text
from app.core.db.database import async_engine

def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

async def create():
    hashed = get_password_hash("1232123#12321")
    async with async_engine.begin() as conn:
        res = await conn.execute(text("SELECT id FROM \"user\" WHERE email = :email"), {"email": "nguyenduchoai@gmail.com"})
        if not res.first():
            import uuid
            from datetime import datetime
            user_id = str(uuid.uuid4())
            now = datetime.utcnow()
            await conn.execute(text("""
                INSERT INTO "user" (id, email, hashed_password, is_superuser, full_name, is_active, created_at, updated_at)
                VALUES (:id, :email, :pw, :super, :name, :active, :created, :updated)
            """), {"id": user_id, "email": "nguyenduchoai@gmail.com", "pw": hashed, "super": True, "name": "Admin", "active": True, "created": now, "updated": now})
            print("Admin user created successfully via pure SQL")
        else:
            print("Admin user already exists")

asyncio.run(create())
