import requests
from datetime import datetime
from dateutil import parser as date_parser
from pytz import timezone as tz_timezone
from app.core.logger import setup_logging
from app.ai.plugins_func.register import (
    register_function,
    ToolType,
    ActionResponse,
    Action,
)

TAG = __name__
logger = setup_logging()

# Default values (có thể override từ config)
DEFAULT_API_TIMEZONE = "Asia/Ho_Chi_Minh"  # GMT+7
DEFAULT_API_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"

GET_ECONOMIC_CALENDAR_FUNCTION_DESC = {
    "type": "function",
    "function": {
        "name": "get_economic_calendar",
        "description": (
            "Lấy sự kiện kinh tế trong tuần này từ nguồn dữ liệu ngoài. "
            "Hàm sẽ tự động lọc chỉ lấy các sự kiện có mức độ tác động cao (High) hoặc trung bình (Medium), "
            "và chỉ lấy những sự kiện trong tương lai (từ giờ trở đi). "
            "Trả về danh sách các sự kiện kinh tế với thông tin như tiêu đề, quốc gia, thời gian, mức tác động, dự báo, và dữ liệu trước đó."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
}

API_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36"
    )
}


def filter_calendar_events(events, api_timezone=DEFAULT_API_TIMEZONE):
    """
    Lọc dữ liệu lịch sự kiện theo tiêu chí:
    - date > now (chỉ lấy sự kiện trong tương lai)
    - impact in [High, Medium]
    - Loại bỏ field rỗng
    - Chuyển đổi múi giờ API (ET) → UTC để so sánh chính xác
    """
    if not events:
        return []

    # Tạo timezone objects
    api_tz = tz_timezone(api_timezone)
    utc_tz = tz_timezone("UTC")
    now = datetime.now(utc_tz)

    filtered_events = []

    for event in events:
        try:
            date_str = event.get("date", "").strip()
            if not date_str:
                continue

            # Parse date string - hỗ trợ cả ISO format và timezone
            try:
                event_date = date_parser.isoparse(date_str)
            except (ValueError, TypeError):
                logger.bind(tag=TAG).warning(f"Không thể parse date: {date_str}")
                continue

            # Nếu datetime không có timezone info, assume là múi giờ API (ET)
            if event_date.tzinfo is None:
                event_date = api_tz.localize(event_date)

            # Convert sang UTC để so sánh với now (UTC)
            event_date_utc = event_date.astimezone(utc_tz)

            if event_date_utc <= now:
                continue

            # Lọc theo impact: High hoặc Medium
            impact = event.get("impact", "").strip()
            if impact not in ["High", "Medium"]:
                continue

            # Loại bỏ field rỗng
            cleaned_event = {}
            for key, value in event.items():
                # Bỏ qua value rỗng (empty string, None)
                if value and (
                    isinstance(value, str)
                    and value.strip()
                    or not isinstance(value, str)
                ):
                    cleaned_event[key] = value

            if cleaned_event:  # Chỉ thêm nếu còn dữ liệu
                filtered_events.append(cleaned_event)

        except Exception as e:
            logger.bind(tag=TAG).warning(f"Lỗi khi xử lý event: {str(e)}")
            continue

    return filtered_events


def format_calendar_report(events):
    """Format dữ liệu sự kiện thành văn bản để LLM dễ xử lý"""
    if not events:
        return "Không có sự kiện kinh tế nào có mức độ tác động cao hoặc trung bình trong tuần này."

    report = "Lịch sự kiện kinh tế trong tuần này:\n\n"

    for idx, event in enumerate(events, 1):
        report += f"{idx}. {event.get('title', 'Không rõ')}\n"
        report += f"   • Quốc gia: {event.get('country', 'Không rõ')}\n"
        report += f"   • Thời gian: {event.get('date', 'Không rõ')}\n"
        report += f"   • Mức tác động: {event.get('impact', 'Không rõ')}\n"

        if "forecast" in event:
            report += f"   • Dự báo: {event['forecast']}\n"
        if "previous" in event:
            report += f"   • Dữ liệu trước: {event['previous']}\n"

        report += "\n"

    # Thêm prompt cho LLM hỏi user về việc đặt lời nhắc
    report += "\n📌 **Prompt cho LLM**: Sau khi chia sẻ lịch sự kiện kinh tế này, hãy hỏi user: "
    report += '"Bạn có muốn tôi đặt lời nhắc cho bất kỳ sự kiện nào trong danh sách này không? '
    report += 'Nếu có, vui lòng cho tôi biết tiêu đề sự kiện và thời gian nhắc (trước sự kiện bao lâu)."'

    return report


@register_function(
    "get_economic_calendar",
    GET_ECONOMIC_CALENDAR_FUNCTION_DESC,
    ToolType.WAIT,
)
def get_economic_calendar(conn=None):
    """
    Lấy lịch sự kiện kinh tế trong tuần này.
    Tự động lọc chỉ lấy các sự kiện:
    - Có mức độ tác động cao (High) hoặc trung bình (Medium)
    - Trong tương lai (date > now)
    - Loại bỏ các field không có dữ liệu
    - Xử lý timezone chính xác (ET → UTC)
    """
    try:
        # Lấy config từ conn
        api_timezone = DEFAULT_API_TIMEZONE
        api_url = DEFAULT_API_URL

        if conn and hasattr(conn, "config"):
            if "get_economic_calendar" in conn.config.get("plugins", {}):
                config = conn.config["plugins"]["get_economic_calendar"]
                api_timezone = config.get("api_timezone", DEFAULT_API_TIMEZONE)
                api_url = config.get("api_url", DEFAULT_API_URL)

        # Gọi API lấy dữ liệu
        response = requests.get(api_url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        raw_events = response.json()

        if raw_events is None:
            return ActionResponse(
                Action.REQLLM,
                None,
                "Không thể lấy dữ liệu lịch sự kiện kinh tế lúc này, vui lòng thử lại sau",
            )

        # Lọc dữ liệu với timezone từ config
        filtered_events = filter_calendar_events(raw_events, api_timezone=api_timezone)

        # Format thành report
        report = format_calendar_report(filtered_events)

        logger.bind(tag=TAG).debug(
            f"Lấy được {len(filtered_events)} sự kiện kinh tế có mức độ tác động cao/trung bình (Timezone: {api_timezone})"
        )

        return ActionResponse(Action.REQLLM, report, None)

    except requests.exceptions.RequestException as e:
        logger.bind(tag=TAG).error(f"Lỗi khi gọi API: {str(e)}")
        return ActionResponse(
            Action.REQLLM,
            None,
            "Không thể lấy dữ liệu lịch sự kiện kinh tế lúc này, vui lòng thử lại sau",
        )
    except Exception as e:
        logger.bind(tag=TAG).error(f"Lỗi không mong muốn: {str(e)}")
        return ActionResponse(
            Action.REQLLM,
            None,
            "Đã xảy ra lỗi khi lấy dữ liệu lịch sự kiện kinh tế",
        )
