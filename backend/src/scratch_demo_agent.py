import asyncio
from app.core.db.database import AsyncSessionLocal
from app.models.agent import Agent
from app.models.user import User
from app.core.enums import StatusEnum
from sqlalchemy.future import select

async def main():
    async with AsyncSessionLocal() as session:
        # Get first user
        stmt = select(User).limit(1)
        result = await session.execute(stmt)
        user = result.scalars().first()
        
        if not user:
            print("No users found in database.")
            return

        # Check existing agent to see the format
        stmt_agent = select(Agent).limit(1)
        res_agent = await session.execute(stmt_agent)
        existing_agent = res_agent.scalars().first()
        if existing_agent:
            print(f"Existing Agent: ID={existing_agent.id}, LLM={existing_agent.LLM}, TTS={existing_agent.TTS}")

        print("Done")

if __name__ == "__main__":
    asyncio.run(main())
