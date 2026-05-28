from __future__ import annotations

import json
from typing import TYPE_CHECKING

from app.ai.plugins_func.register import (
    register_function,
    ToolType,
    ActionResponse,
    Action,
)
from app.core.logger import setup_logging
from app.core.db.database import local_session

if TYPE_CHECKING:
    from app.ai.connection import (
        ConnectionHandler,
    )  # chỉ dùng cho hint, không chạy lúc runtime


TAG = __name__
logger = setup_logging()

# NOTE: Old change_role function was removed (deprecated)
# Use get_list_agent + change_agent instead for template switching


get_list_agent_function_desc = {
    "type": "function",
    "function": {
        "name": "get_list_agent",
        "description": "Lấy danh sách các vai trò/agent có thể chuyển đổi. Trả về agent_id và agent_name.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
}


change_agent_function_desc = {
    "type": "function",
    "function": {
        "name": "change_agent",
        "description": "Chuyển đổi sang vai trò/agent khác. IMPORTANT: Khi user yêu cầu thay đổi vai trò, chỉ cần gọi tool này mà không cần trả lời hay giải thích gì với user.",
        "parameters": {
            "type": "object",
            "properties": {
                "template_id": {
                    "type": "string",
                    "description": "UUID của agent cần chuyển sang (agent_id từ get_list_agent)",
                },
            },
            "required": ["template_id"],
        },
    },
}


@register_function(
    "get_list_agent",
    get_list_agent_function_desc,
    ToolType.SYSTEM_CTL,
)
async def get_list_agent(conn):
    """
    Lấy danh sách các agent/vai trò có thể chuyển đổi.

    Sử dụng AgentService.get_available_templates_for_ws() để lấy danh sách
    agents với lọc exclude agent hiện tại ở database level.

    Args:
        conn: Connection object chứa agent_info (agent_id, user_id)

    Returns:
        ActionResponse với list gồm agent_id và agent_name
    """
    logger.bind(tag=TAG).info("Yêu cầu lấy danh sách agents có thể chuyển đổi")

    # Resolve agent context từ connection
    current_agent_info = getattr(conn, "agent", {})
    agent_id = current_agent_info.get("id")

    if not agent_id:
        logger.bind(tag=TAG).warning("Không tìm thấy agent_id trong connection")
        return ActionResponse(
            action=Action.REQLLM,
            result=json.dumps(
                {
                    "message": "lay_that_bai",
                    "reason": "thieu_agent_id",
                    "detail": "Không xác định được agent trong kết nối",
                },
                ensure_ascii=False,
            ),
            response=None,
        )

    # Convert IDs to string
    agent_id_str = str(agent_id) if agent_id else None

    if not agent_id_str:
        logger.bind(tag=TAG).warning("Không tìm thấy agent_id trong connection")
        return ActionResponse(
            action=Action.REQLLM,
            result=json.dumps(
                {
                    "message": "lay_that_bai",
                    "reason": "thieu_agent_id",
                    "detail": "Không xác định được agent trong kết nối",
                },
                ensure_ascii=False,
            ),
            response=None,
        )

    logger.bind(tag=TAG).debug(f"Agent ID từ connection: {agent_id_str}")

    try:
        from app.services import agent_service

        async with local_session() as db:
            # Lấy danh sách templates của agent, exclude template hiện tại
            templates_list = await agent_service.get_available_templates_for_ws(
                db=db,
                agent_id=agent_id_str,
                offset=0,
                limit=100,  # Lấy tối đa 100 templates
            )

            logger.bind(tag=TAG).debug(
                f"Tìm thấy {len(templates_list)} templates cho agent {agent_id_str}"
            )

            response_payload = {
                "message": (
                    "lay_thanh_cong" if templates_list else "khong_co_agent"
                ),
                "agent_id": agent_id_str,
                "agents": templates_list,
                "total": len(templates_list),
            }

            return ActionResponse(
                action=Action.REQLLM,
                result=json.dumps(response_payload, ensure_ascii=False),
                response=None,
            )

    except Exception as exc:
        logger.bind(tag=TAG).exception(f"Lỗi khi lấy danh sách templates: {exc}")
        return ActionResponse(
            action=Action.REQLLM,
            result=json.dumps(
                {
                    "message": "lay_that_bai",
                    "reason": "loi_noi_bo",
                    "detail": "Không thể lấy danh sách templates",
                },
                ensure_ascii=False,
            ),
            response=None,
        )


@register_function(
    "change_agent",
    change_agent_function_desc,
    ToolType.SYSTEM_CTL,
)
async def change_agent(conn: ConnectionHandler, template_id: str):
    """
    Chuyển đổi sang agent/vai trò khác bằng cách hot-reload config.

    Triggers hot-reload operation trong ConnectionHandler, cho phép switch
    AI module configuration trong real-time mà không gián đoạn conversation.

    Args:
        conn: Connection object chứa device_id và agent_info
        template_id: UUID của agent cần chuyển sang

    Returns:
        ActionResponse với thông tin kết quả thay đổi
    """
    logger.bind(tag=TAG).info(f"LLM triggered agent change: template_id={template_id}")

    try:
        # Resolve agent context từ connection
        current_agent_info = getattr(conn, "agent", {})
        agent_id = current_agent_info.get("id")

        if not agent_id:
            logger.bind(tag=TAG).warning("Không tìm thấy agent_id trong connection")
            return ActionResponse(
                action=Action.REQLLM,
                result=json.dumps(
                    {
                        "message": "thay_doi_that_bai",
                        "reason": "thieu_agent_id",
                        "detail": "Không xác định được agent trong kết nối",
                    },
                    ensure_ascii=False,
                ),
                response=None,
            )

        # Convert agent_id to string
        agent_id_str = str(agent_id) if agent_id else None

        if not agent_id_str:
            logger.bind(tag=TAG).warning("Không tìm thấy agent_id trong connection")
            return ActionResponse(
                action=Action.REQLLM,
                result=json.dumps(
                    {
                        "message": "thay_doi_that_bai",
                        "reason": "thieu_agent_id",
                        "detail": "Không xác định được agent trong kết nối",
                    },
                    ensure_ascii=False,
                ),
                response=None,
            )

        logger.bind(tag=TAG).debug(f"Agent ID từ connection: {agent_id_str}")

        from app.services import agent_service

        async with local_session() as db:
            # 1. Kiểm tra template có tồn tại và thuộc về agent không
            is_valid = await agent_service.validate_template_belongs_to_agent(
                db=db,
                agent_id=agent_id_str,
                template_id=template_id,
            )

            if not is_valid:
                logger.bind(tag=TAG).warning(
                    f"Template {template_id} không thuộc agent {agent_id_str} hoặc không tồn tại"
                )
                return ActionResponse(
                    action=Action.REQLLM,
                    result=json.dumps(
                        {
                            "message": "thay_doi_that_bai",
                            "reason": "template_khong_hop_le",
                            "detail": "Template không thuộc agent hoặc không tồn tại",
                        },
                        ensure_ascii=False,
                    ),
                    response=None,
                )

            # 2. Lấy template data và transform cho WebSocket
            transformed_template = await agent_service.get_transformed_template(
                db=db,
                template_id=template_id,
            )

            if not transformed_template:
                logger.bind(tag=TAG).error(f"Không tìm thấy template {template_id}")
                return ActionResponse(
                    action=Action.REQLLM,
                    result=json.dumps(
                        {
                            "message": "thay_doi_that_bai",
                            "reason": "template_khong_tim_thay",
                            "detail": "Template không tìm thấy trong database",
                        },
                        ensure_ascii=False,
                    ),
                    response=None,
                )

            # 3. Thay đổi template của agent
            await agent_service.change_agent_template(
                db=db,
                agent_id=agent_id_str,
                template_id=template_id,
            )
            try:
                await conn.reload_agent_template(transformed_template)
            except Exception as change_error:
                logger.bind(tag=TAG).error(
                    f"Agent change failed: {change_error}", exc_info=True
                )
                return ActionResponse(
                    action=Action.REQLLM,
                    result=json.dumps(
                        {
                            "message": "thay_doi_that_bai",
                            "reason": "loi_khi_thay_doi",
                            "detail": f"Lỗi khi thay đổi cấu hình: {str(change_error)}",
                        },
                        ensure_ascii=False,
                    ),
                    response=None,
                )

            response_payload = {
                "message": "thay_doi_thanh_cong",
                "detail": "Cấu hình agent đã được cập nhật thành công",
            }

            return ActionResponse(
                action=Action.REQLLM,
                result=json.dumps(response_payload, ensure_ascii=False),
                response=None,
            )

    except Exception as exc:
        logger.bind(tag=TAG).exception(f"Unexpected error in change_agent: {exc}")
        return ActionResponse(
            action=Action.REQLLM,
            result=json.dumps(
                {
                    "message": "thay_doi_that_bai",
                    "reason": "loi_noi_bo",
                    "detail": "Lỗi không mong đợi khi thay đổi cấu hình",
                },
                ensure_ascii=False,
            ),
            response=None,
        )
