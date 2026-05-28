"""
Seed Bizgenie Demo Agent.

Run on Server:
docker-compose exec backend python scripts/seed_bizgenie_demo.py
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from uuid6 import uuid7
from sqlalchemy import select
from app.core.db.database import local_session
from app.models.user import User
from app.models.agent import Agent
from app.core.enums import StatusEnum

async def seed_bizgenie_agent():
    async with local_session() as db:
        # Tìm user đầu tiên (thường là Admin)
        result = await db.execute(select(User).limit(1))
        user = result.scalars().first()
        
        if not user:
            print("❌ Không tìm thấy User nào trong database. Vui lòng tạo User trước.")
            return

        # Kiểm tra xem agent đã tồn tại chưa
        res = await db.execute(select(Agent).where(Agent.agent_name == "Bizgenie AI Robot - Demo"))
        existing = res.scalars().first()
        
        if existing:
            print("⏭ Demo Agent 'Bizgenie AI Robot - Demo' đã tồn tại. Đang cập nhật config...")
            existing.LLM = "config:minimax"
            existing.TTS = "config:valtec"  # Dùng Valtec để có giọng Việt tự nhiên, zero-cost
            existing.ASR = "config:sherpa_onnx"
            existing.status = StatusEnum.enabled
            await db.commit()
            print("✅ Đã cập nhật Agent với LLM=MiniMax và TTS=Valtec.")
            return

        demo_prompt = (
            "Bạn là trợ lý AI thông minh của Bizgenie, được tạo ra để đồng hành cùng học sinh và giáo viên Việt Nam. "
            "Bạn có kiến thức chuyên sâu về bộ Sách Giáo Khoa năm 2026 và các nghiệp vụ kế toán cơ bản. "
            "Hãy trả lời ngắn gọn, thân thiện, súc tích và dễ hiểu. Hạn chế sử dụng các câu dài dòng. "
            "Luôn xưng hô là 'mình' hoặc 'Bizgenie' và gọi người dùng là 'bạn'."
        )

        agent = Agent(
            id=str(uuid7()),
            user_id=user.id,
            agent_name="Bizgenie AI Robot - Demo",
            description="Agent Demo dùng MiniMax LLM (Não) + Valtec TTS (Miệng) cho dự án SGK 2026",
            avatar_url="https://ui-avatars.com/api/?name=Bizgenie&background=0D8ABC&color=fff",
            status=StatusEnum.enabled,
            prompt=demo_prompt,
            LLM="config:minimax",
            TTS="config:valtec", # Valtec cho giọng tiếng Việt nhẹ và hay
            ASR="config:sherpa_onnx", # STT local (free)
            enable_memory=True,
            enable_knowledge_base=True
        )

        db.add(agent)
        await db.commit()
        print(f"✅ Đã tạo thành công Bizgenie Demo Agent: ID={agent.id}")
        print("👉 Vui lòng vào Admin Dashboard > Agents để kiểm tra và lấy Pair Code gắn vào Robot ESP32.")

if __name__ == "__main__":
    print("🤖 Seeding Bizgenie Demo Agent...")
    asyncio.run(seed_bizgenie_agent())
