"""
Mô-đun tiện ích thời gian
Cung cấp chức năng lấy thời gian thống nhất
"""

from datetime import datetime, timezone, timedelta

# Vietnam timezone (UTC+7)
VN_TIMEZONE = timezone(timedelta(hours=7))

WEEKDAY_MAP = {
    "Monday": "Thứ Hai",
    "Tuesday": "Thứ Ba",
    "Wednesday": "Thứ Tư",
    "Thursday": "Thứ Năm",
    "Friday": "Thứ Sáu",
    "Saturday": "Thứ Bảy",
    "Sunday": "Chủ Nhật",
}


def get_current_time() -> str:
    """
    Lấy chuỗi thời gian hiện tại (định dạng: HH:MM) theo múi giờ Việt Nam
    """
    return datetime.now(VN_TIMEZONE).strftime("%H:%M")


def get_current_date() -> str:
    """
    Lấy chuỗi ngày hôm nay (định dạng: YYYY-MM-DD) theo múi giờ Việt Nam
    """
    return datetime.now(VN_TIMEZONE).strftime("%Y-%m-%d")


def get_current_weekday() -> str:
    """
    Lấy hôm nay là thứ mấy theo múi giờ Việt Nam
    """
    now = datetime.now(VN_TIMEZONE)
    return WEEKDAY_MAP[now.strftime("%A")]


def get_current_datetime_iso() -> str:
    """
    Lấy datetime hiện tại ở định dạng ISO-8601 với timezone +07:00
    Ví dụ: 2026-01-24T11:03:14+07:00
    """
    return datetime.now(VN_TIMEZONE).isoformat()


def get_current_time_info() -> tuple:
    """
    Lấy thông tin thời gian hiện tại theo múi giờ Việt Nam
    Trả về: (chuỗi thời gian hiện tại, ngày hôm nay, thứ trong tuần)
    """
    current_time = get_current_time()
    today_date = get_current_date()
    today_weekday = get_current_weekday()
    
    return current_time, today_date, today_weekday

