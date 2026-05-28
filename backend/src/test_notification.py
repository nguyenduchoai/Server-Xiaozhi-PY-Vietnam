import asyncio
import os
from sqlalchemy import select
from app.core.db.database import async_session_maker
from app.models.user import User

async def get_token():
    async with async_session_maker() as db:
        user = (await db.execute(select(User))).scalars().first()
        from app.core.auth import create_access_token
        from datetime import timedelta
        token = create_access_token(
            data={"sub": user.id}, expires_delta=timedelta(minutes=15)
        )
        print(f"export TOKEN='{token}'")

asyncio.run(get_token())
