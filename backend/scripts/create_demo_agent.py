import sys
import uuid
from datetime import datetime
sys.path.append('./src')
from app.core.db.database import local_session
from sqlalchemy import text
import asyncio

async def main():
    async with local_session() as db:
        user_id = 'c7f2efd9-35ee-4321-86d3-960e2e11f6aa'
        llm_id = '019df356-ceb4-74df-a2e9-fee526e92135'
        tts_id = '019c5a0a-5875-710e-97cf-1414b1ea2256'
        
        agent_id = str(uuid.uuid7()) if hasattr(uuid, 'uuid7') else '019df356-xxxx-xxxx-xxxx-xxxxxxxxxxxx' # just generate a string, but PostgreSQL might need UUID. Let's use uuid.uuid4() for now but it's v7 in DB? Actually UUID v4 is fine.
        agent_id = str(uuid.uuid4())
        
        sql = text("""
            INSERT INTO agent (id, agent_name, prompt, "LLM", "TTS", "ASR", user_id, created_at, updated_at)
            VALUES (:id, :name, :prompt, :llm, :tts, :asr, :user_id, :now, :now)
        """)
        
        await db.execute(sql, {
            "id": agent_id,
            "name": "Bizgenie Demo MiniMax",
            "prompt": "Bạn là Bizgenie, trợ lý ảo thông minh.",
            "llm": f"db:{llm_id}",
            "tts": f"db:{tts_id}",
            "asr": "",
            "user_id": user_id,
            "now": datetime.utcnow()
        })
        await db.commit()
        print(f"Created agent: {agent_id}")

asyncio.run(main())
