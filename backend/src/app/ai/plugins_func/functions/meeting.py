"""
Meeting Assistant Plugin Functions — Voice Commands

Voice-first meeting management through AI Assistant.
Features:
- Start/stop meeting recording
- List recent meetings
- Get meeting summary
- Ask about meetings (RAG query)
- Check assigned tasks
"""
from __future__ import annotations

import re
from datetime import datetime, date
from typing import Optional

from app.ai.plugins_func.register import (
    register_function,
    ToolType,
    ActionResponse,
    Action,
)
from app.core.db.database import local_session
from app.core.logger import setup_logging

TAG = __name__
logger = setup_logging()


# ============================================================================
# FUNCTION DESCRIPTIONS
# ============================================================================



list_meetings_function_desc = {
    "type": "function",
    "function": {
        "name": "list_meetings",
        "description": "Xem danh sách cuộc họp gần đây. Dùng khi người dùng nói 'xem cuộc họp', 'danh sách cuộc họp', 'list meetings'.",
        "parameters": {
            "type": "object",
            "properties": {
                "count": {
                    "type": "integer",
                    "description": "Số cuộc họp muốn xem (mặc định 5)",
                },
            },
            "required": [],
        },
    },
}

meeting_summary_function_desc = {
    "type": "function",
    "function": {
        "name": "meeting_summary",
        "description": "Đọc tóm tắt cuộc họp gần nhất hoặc một cuộc họp cụ thể. Dùng khi người dùng nói 'tóm tắt cuộc họp', 'meeting summary', 'cuộc họp nói gì', 'cuộc họp hôm nay nói về gì'.",
        "parameters": {
            "type": "object",
            "properties": {
                "meeting_title": {
                    "type": "string",
                    "description": "Tên cuộc họp muốn xem (nếu không chỉ rõ, lấy cuộc họp gần nhất)",
                },
            },
            "required": [],
        },
    },
}

ask_meeting_function_desc = {
    "type": "function",
    "function": {
        "name": "ask_meeting",
        "description": "Hỏi AI về nội dung cuộc họp. Dùng khi người dùng hỏi BẤT KỲ câu hỏi nào liên quan đến cuộc họp, ví dụ: 'trong cuộc họp ai được giao việc gì', 'quyết định gì trong cuộc họp', 'deadline dự án X', 'cuộc họp bàn về vấn đề gì', 'ai nói gì trong cuộc họp'.",
        "parameters": {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "Câu hỏi của người dùng về cuộc họp",
                },
                "meeting_title": {
                    "type": "string",
                    "description": "Tên cuộc họp cụ thể (nếu có). Nếu không chỉ rõ, tìm trong tất cả cuộc họp gần nhất.",
                },
            },
            "required": ["question"],
        },
    },
}

my_tasks_function_desc = {
    "type": "function",
    "function": {
        "name": "my_tasks",
        "description": "Xem các công việc được giao từ cuộc họp. Dùng khi người dùng nói 'xem công việc', 'task của tôi', 'my tasks', 'việc gì cần làm'.",
        "parameters": {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "enum": ["pending", "in_progress", "done", "all"],
                    "description": "Lọc theo trạng thái (mặc định: pending)",
                },
            },
            "required": [],
        },
    },
}


# ============================================================================
# FUNCTION IMPLEMENTATIONS
# ============================================================================




@register_function(
    "list_meetings",
    list_meetings_function_desc,
    ToolType.SYSTEM_CTL,
)
def list_meetings(conn, count: int = 5, **kwargs):
    """List recent meetings."""
    try:
        from app.crud.crud_meeting import get_meetings_by_user
        import asyncio

        user_id = _get_user_id(conn)
        if not user_id:
            return ActionResponse(
                action=Action.RESPONSE,
                result="Không tìm thấy thông tin người dùng.",
                response="Không tìm thấy thông tin người dùng.",
            )

        async def _list():
            async with local_session() as db:
                meetings, total = await get_meetings_by_user(
                    db=db, user_id=user_id, page=1, page_size=min(count, 10)
                )
                return meetings, total

        loop = asyncio.new_event_loop()
        try:
            meetings, total = loop.run_until_complete(_list())
        finally:
            loop.close()

        if not meetings:
            return ActionResponse(
                action=Action.RESPONSE,
                result="Bạn chưa có cuộc họp nào.",
                response="Bạn chưa có cuộc họp nào được ghi lại.",
            )

        lines = [f"Bạn có {total} cuộc họp. Đây là {len(meetings)} cuộc họp gần nhất:"]
        for i, m in enumerate(meetings, 1):
            status_icons = {
                "recording": "🔴", "processing": "⏳",
                "completed": "✅", "failed": "❌",
            }
            icon = status_icons.get(m.status.value if hasattr(m.status, 'value') else str(m.status), "📋")
            lines.append(f"{i}. {icon} {m.title} — {m.meeting_date}")

        result = "\n".join(lines)
        return ActionResponse(
            action=Action.RESPONSE,
            result=result,
            response=result,
        )

    except Exception as e:
        logger.bind(tag=TAG).error(f"list_meetings error: {e}")
        return ActionResponse(
            action=Action.RESPONSE,
            result=f"Lỗi: {str(e)}",
            response="Xin lỗi, không thể xem danh sách cuộc họp.",
        )


@register_function(
    "meeting_summary",
    meeting_summary_function_desc,
    ToolType.SYSTEM_CTL,
)
def meeting_summary(conn, meeting_title: str = None, **kwargs):
    """Get summary of a meeting."""
    try:
        from app.crud.crud_meeting import get_meetings_by_user, get_tasks_by_meeting
        from sqlalchemy import select
        from app.models.meeting import Meeting
        import asyncio

        user_id = _get_user_id(conn)
        if not user_id:
            return ActionResponse(
                action=Action.RESPONSE,
                result="Không tìm thấy thông tin người dùng.",
                response="Không tìm thấy thông tin người dùng.",
            )

        async def _get_summary():
            async with local_session() as db:
                if meeting_title:
                    # Search by title — escape SQL LIKE wildcards from voice input
                    from sqlalchemy import and_
                    safe_title = re.sub(r'[%_\\]', '', meeting_title.strip())
                    result = await db.execute(
                        select(Meeting).where(
                            and_(
                                Meeting.user_id == user_id,
                                Meeting.is_deleted == False,
                                Meeting.title.ilike(f"%{safe_title}%"),
                            )
                        ).order_by(Meeting.created_at.desc()).limit(1)
                    )
                    meeting = result.scalar_one_or_none()
                else:
                    # Get latest completed meeting
                    meetings, _ = await get_meetings_by_user(
                        db=db, user_id=user_id, page=1, page_size=1
                    )
                    meeting = meetings[0] if meetings else None

                if not meeting:
                    return None, []

                tasks = await get_tasks_by_meeting(db, meeting.id)
                return meeting, tasks

        loop = asyncio.new_event_loop()
        try:
            meeting, tasks = loop.run_until_complete(_get_summary())
        finally:
            loop.close()

        if not meeting:
            return ActionResponse(
                action=Action.RESPONSE,
                result="Không tìm thấy cuộc họp.",
                response="Không tìm thấy cuộc họp nào phù hợp.",
            )

        lines = [f"Cuộc họp: {meeting.title} — Ngày: {meeting.meeting_date}"]

        if meeting.summary:
            lines.append(f"\nTóm tắt: {meeting.summary}")
        else:
            lines.append("\nChưa có tóm tắt. Cần upload audio để xử lý.")

        if tasks:
            lines.append(f"\nCông việc ({len(tasks)}):")
            for t in tasks[:5]:
                assignee = f" giao cho {t.assignee_name}" if t.assignee_name else ""
                deadline_str = f" hạn {t.deadline}" if t.deadline else ""
                status_str = t.status.value if hasattr(t.status, 'value') else str(t.status)
                lines.append(f"- {t.title}{assignee}{deadline_str} ({status_str})")

        result = "\n".join(lines)
        # Use REQLLM so LLM generates a natural voice-friendly summary
        return ActionResponse(
            action=Action.REQLLM,
            result=f"Hãy tóm tắt ngắn gọn cuộc họp này cho người nghe bằng giọng nói, dưới 100 từ:\n\n{result}",
            response=None,
        )

    except Exception as e:
        logger.bind(tag=TAG).error(f"meeting_summary error: {e}")
        return ActionResponse(
            action=Action.RESPONSE,
            result=f"Lỗi: {str(e)}",
            response="Xin lỗi, không thể đọc tóm tắt cuộc họp.",
        )


@register_function(
    "ask_meeting",
    ask_meeting_function_desc,
    ToolType.SYSTEM_CTL,
)
def ask_meeting(conn, question: str = "", meeting_title: str = None, **kwargs):
    """Ask AI about meetings — RAG query over transcripts."""
    try:
        from app.crud.crud_meeting import get_meetings_by_user, get_transcript_by_meeting, get_tasks_by_meeting
        from sqlalchemy import select, and_
        from app.models.meeting import Meeting
        import asyncio

        user_id = _get_user_id(conn)
        if not user_id:
            return ActionResponse(
                action=Action.RESPONSE,
                result="Không tìm thấy thông tin người dùng.",
                response="Không tìm thấy thông tin người dùng.",
            )

        if not question:
            return ActionResponse(
                action=Action.RESPONSE,
                result="Bạn muốn hỏi gì về cuộc họp?",
                response="Bạn muốn hỏi gì về cuộc họp?",
            )

        # Build context from recent meetings
        async def _build_context():
            async with local_session() as db:
                # If specific meeting title, search by title
                if meeting_title:
                    safe_title = re.sub(r'[%_\\]', '', meeting_title.strip())
                    result = await db.execute(
                        select(Meeting).where(
                            and_(
                                Meeting.user_id == user_id,
                                Meeting.is_deleted == False,
                                Meeting.title.ilike(f"%{safe_title}%"),
                            )
                        ).order_by(Meeting.created_at.desc()).limit(3)
                    )
                    meetings = result.scalars().all()
                else:
                    meetings, _ = await get_meetings_by_user(
                        db=db, user_id=user_id, page=1, page_size=5
                    )

                context_parts = []
                for meeting in meetings:
                    parts = [f"--- Cuộc họp: {meeting.title} ({meeting.meeting_date}) ---"]
                    
                    if meeting.summary:
                        parts.append(f"Tóm tắt: {meeting.summary}")

                    # Include transcript segments for RAG
                    segments = await get_transcript_by_meeting(db, meeting.id)
                    if segments:
                        transcript = "\n".join([
                            f"[{s.speaker_label or '?'}]: {s.text}" for s in segments[:50]
                        ])
                        parts.append(f"Nội dung:\n{transcript[:3000]}")

                    # Include tasks
                    tasks = await get_tasks_by_meeting(db, meeting.id)
                    if tasks:
                        task_lines = []
                        for t in tasks:
                            assignee = f" → {t.assignee_name}" if t.assignee_name else ""
                            deadline = f" (hạn {t.deadline})" if t.deadline else ""
                            task_lines.append(f"- {t.title}{assignee}{deadline}")
                        parts.append(f"Công việc:\n" + "\n".join(task_lines))

                    context_parts.append("\n".join(parts))

                return "\n\n".join(context_parts)

        loop = asyncio.new_event_loop()
        try:
            context = loop.run_until_complete(_build_context())
        finally:
            loop.close()

        if not context:
            return ActionResponse(
                action=Action.RESPONSE,
                result="Chưa có dữ liệu cuộc họp nào. Hãy ghi âm và xử lý cuộc họp trước.",
                response="Bạn chưa có dữ liệu cuộc họp nào để tìm kiếm.",
            )

        # Use REQLLM: pass data to LLM which generates voice-friendly answer
        enhanced_prompt = (
            f"Dựa trên thông tin các cuộc họp dưới đây, hãy trả lời câu hỏi NGẮN GỌN "
            f"(dưới 80 từ, phù hợp nghe bằng giọng nói). "
            f"CHÚ Ý TUYỆT ĐỐI: CHỈ trả lời dựa trên thông tin có trong đoạn nội dung cuộc họp này. "
            f"Nếu thông tin không có trong cuộc họp, HÃY TỪ CHỐI trả lời và nói rằng 'Tôi không tìm thấy thông tin này trong cuộc họp', KHÔNG ĐƯỢC tự bịa ra câu trả lời hay nói linh tinh.\n\n"
            f"NỘI DUNG CUỘC HỌP:\n{context[:6000]}\n\n"
            f"Câu hỏi: {question}"
        )

        return ActionResponse(
            action=Action.REQLLM,
            result=enhanced_prompt,
            response=None,
        )

    except Exception as e:
        logger.bind(tag=TAG).error(f"ask_meeting error: {e}")
        return ActionResponse(
            action=Action.RESPONSE,
            result=f"Lỗi: {str(e)}",
            response="Xin lỗi, không thể trả lời câu hỏi về cuộc họp.",
        )


@register_function(
    "my_tasks",
    my_tasks_function_desc,
    ToolType.SYSTEM_CTL,
)
def my_tasks(conn, status: str = "pending", **kwargs):
    """Get user's tasks from meetings."""
    try:
        from app.crud.crud_meeting import get_tasks_by_user
        import asyncio

        user_id = _get_user_id(conn)
        if not user_id:
            return ActionResponse(
                action=Action.RESPONSE,
                result="Không tìm thấy thông tin người dùng.",
                response="Không tìm thấy thông tin người dùng.",
            )

        status_filter = status if status != "all" else None

        async def _get_tasks():
            async with local_session() as db:
                return await get_tasks_by_user(
                    db=db, user_id=user_id, status=status_filter
                )

        loop = asyncio.new_event_loop()
        try:
            tasks = loop.run_until_complete(_get_tasks())
        finally:
            loop.close()

        if not tasks:
            msg = "Không có công việc nào" + (f" với trạng thái '{status}'." if status != "all" else ".")
            return ActionResponse(
                action=Action.RESPONSE,
                result=msg,
                response=msg,
            )

        lines = [f"Bạn có {len(tasks)} công việc từ cuộc họp:"]
        for i, t in enumerate(tasks[:10], 1):
            status_str = t.status.value if hasattr(t.status, 'value') else str(t.status)
            priority_str = t.priority.value if hasattr(t.priority, 'value') else str(t.priority)
            deadline_str = f" hạn {t.deadline}" if t.deadline else ""
            meeting_ref = ""
            lines.append(f"{i}. {t.title}{deadline_str} — {status_str}, ưu tiên {priority_str}{meeting_ref}")

        result = "\n".join(lines)
        # Use REQLLM so LLM reads the task list naturally for voice
        return ActionResponse(
            action=Action.REQLLM,
            result=f"Hãy đọc danh sách công việc sau cho người nghe, ngắn gọn tự nhiên:\n\n{result}",
            response=None,
        )

    except Exception as e:
        logger.bind(tag=TAG).error(f"my_tasks error: {e}")
        return ActionResponse(
            action=Action.RESPONSE,
            result=f"Lỗi: {str(e)}",
            response="Xin lỗi, không thể xem danh sách công việc.",
        )


# ============================================================================
# HELPERS
# ============================================================================

def _get_user_id(conn) -> Optional[str]:
    """Extract user_id from connection."""
    try:
        if hasattr(conn, 'user_id') and conn.user_id:
            return conn.user_id
        if hasattr(conn, 'headers') and conn.headers:
            return conn.headers.get('user_id')
        return None
    except Exception:
        return None
