import asyncio
from app.core.db.database import async_get_db_session
from app.crud.crud_users import user as user_crud
from app.schemas.user import UserCreate
from app.core.security import get_password_hash

async def create():
    async with async_get_db_session() as db:
        user_in = UserCreate(email="nguyenduchoai@gmail.com", password="1232123#12321", is_superuser=True, full_name="Admin")
        existing_user = await user_crud.get_by_email(db, email=user_in.email)
        if not existing_user:
            await user_crud.create(db, obj_in=user_in)
            print("Admin user created successfully")
        else:
            print("Admin user already exists")

asyncio.run(create())
