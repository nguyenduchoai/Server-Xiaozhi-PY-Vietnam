"""
Weather Plugin using Open-Meteo API (Free, no API key required)

Provides current weather and 7-day forecast for any location worldwide.
Uses Open-Meteo geocoding to convert city names to coordinates.
"""

import requests
from app.core.logger import setup_logging
from app.ai.plugins_func.register import (
    register_function,
    ToolType,
    ActionResponse,
    Action,
)

TAG = __name__
logger = setup_logging()

GET_WEATHER_OPENMETEO_DESC = {
    "type": "function",
    "function": {
        "name": "get_weather_openmeteo",
        "description": (
            "Lấy thông tin thời tiết miễn phí từ Open-Meteo API. "
            "Người dùng cung cấp tên thành phố hoặc địa điểm, ví dụ 'Hà Nội', 'Tokyo', 'New York'. "
            "Trả về thời tiết hiện tại và dự báo 7 ngày."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "Tên thành phố hoặc địa điểm, ví dụ 'Hanoi' hoặc 'Ho Chi Minh City'",
                },
            },
            "required": ["location"],
        },
    },
}

# Weather code mapping from Open-Meteo
WEATHER_CODE_MAP = {
    0: "Trời quang",
    1: "Hầu hết quang",
    2: "Một phần mây",
    3: "U ám",
    45: "Sương mù",
    48: "Sương mù đóng băng",
    51: "Mưa phùn nhẹ",
    53: "Mưa phùn vừa",
    55: "Mưa phùn dày",
    56: "Mưa phùn đóng băng nhẹ",
    57: "Mưa phùn đóng băng dày",
    61: "Mưa nhẹ",
    63: "Mưa vừa",
    65: "Mưa to",
    66: "Mưa đóng băng nhẹ",
    67: "Mưa đóng băng nặng",
    71: "Tuyết nhẹ",
    73: "Tuyết vừa",
    75: "Tuyết dày",
    77: "Hạt tuyết",
    80: "Mưa rào nhẹ",
    81: "Mưa rào vừa",
    82: "Mưa rào mạnh",
    85: "Tuyết rơi nhẹ",
    86: "Tuyết rơi nặng",
    95: "Dông",
    96: "Dông kèm mưa đá nhỏ",
    99: "Dông kèm mưa đá lớn",
}


def get_weather_description(code: int) -> str:
    """Get Vietnamese weather description from code."""
    return WEATHER_CODE_MAP.get(code, "Không xác định")


def geocode_location(location: str) -> dict | None:
    """
    Convert location name to coordinates using Open-Meteo Geocoding API.
    
    Returns: {"name": str, "latitude": float, "longitude": float, "country": str}
    """
    try:
        url = "https://geocoding-api.open-meteo.com/v1/search"
        params = {
            "name": location,
            "count": 1,
            "language": "vi",
            "format": "json",
        }
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if "results" in data and len(data["results"]) > 0:
            result = data["results"][0]
            return {
                "name": result.get("name", location),
                "latitude": result["latitude"],
                "longitude": result["longitude"],
                "country": result.get("country", ""),
                "admin1": result.get("admin1", ""),  # State/Province
            }
        return None
    except Exception as e:
        logger.bind(tag=TAG).error(f"Geocoding error: {e}")
        return None


def fetch_weather(latitude: float, longitude: float) -> dict | None:
    """
    Fetch weather data from Open-Meteo API.
    
    Returns current weather and 7-day forecast.
    """
    try:
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "current": [
                "temperature_2m",
                "relative_humidity_2m",
                "apparent_temperature",
                "weather_code",
                "wind_speed_10m",
                "precipitation",
            ],
            "daily": [
                "weather_code",
                "temperature_2m_max",
                "temperature_2m_min",
                "precipitation_probability_max",
            ],
            "timezone": "Asia/Ho_Chi_Minh",
            "forecast_days": 7,
        }
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.bind(tag=TAG).error(f"Weather API error: {e}")
        return None


def format_weather_report(location_info: dict, weather_data: dict) -> str:
    """Format weather data into a readable Vietnamese report."""
    
    location_name = location_info["name"]
    if location_info.get("admin1"):
        location_name = f"{location_name}, {location_info['admin1']}"
    if location_info.get("country"):
        location_name = f"{location_name}, {location_info['country']}"
    
    current = weather_data.get("current", {})
    daily = weather_data.get("daily", {})
    
    # Current weather
    current_temp = current.get("temperature_2m", "N/A")
    current_feel = current.get("apparent_temperature", "N/A")
    current_humidity = current.get("relative_humidity_2m", "N/A")
    current_wind = current.get("wind_speed_10m", "N/A")
    current_code = current.get("weather_code", 0)
    current_weather = get_weather_description(current_code)
    
    report = f"""📍 Địa điểm: {location_name}

🌤️ Thời tiết hiện tại: {current_weather}
🌡️ Nhiệt độ: {current_temp}°C (cảm giác như {current_feel}°C)
💧 Độ ẩm: {current_humidity}%
💨 Tốc độ gió: {current_wind} km/h

📅 Dự báo 7 ngày tới:
"""
    
    # Daily forecast
    if "time" in daily:
        days = daily.get("time", [])
        codes = daily.get("weather_code", [])
        max_temps = daily.get("temperature_2m_max", [])
        min_temps = daily.get("temperature_2m_min", [])
        rain_probs = daily.get("precipitation_probability_max", [])
        
        for i in range(min(7, len(days))):
            day_name = days[i] if i < len(days) else "N/A"
            weather_desc = get_weather_description(codes[i]) if i < len(codes) else "N/A"
            max_temp = max_temps[i] if i < len(max_temps) else "N/A"
            min_temp = min_temps[i] if i < len(min_temps) else "N/A"
            rain_prob = rain_probs[i] if i < len(rain_probs) else 0
            
            rain_str = f" 🌧️{rain_prob}%" if rain_prob and rain_prob > 20 else ""
            report += f"  • {day_name}: {weather_desc}, {min_temp}°C ~ {max_temp}°C{rain_str}\n"
    
    report += "\n(Dữ liệu từ Open-Meteo - cập nhật theo thời gian thực)"
    
    return report


@register_function("get_weather_openmeteo", GET_WEATHER_OPENMETEO_DESC, ToolType.SYSTEM_CTL)
async def get_weather_openmeteo(conn, location: str = "Hanoi"):
    """
    Get weather information using Open-Meteo API (free, no API key required).
    
    Args:
        conn: Connection handler
        location: City name or location string
    
    Returns:
        ActionResponse with weather report
    """
    if not location:
        location = "Hanoi"  # Default to Hanoi
    
    logger.bind(tag=TAG).info(f"Getting weather for: {location}")
    
    # Step 1: Geocode location to get coordinates
    location_info = geocode_location(location)
    if not location_info:
        return ActionResponse(
            Action.REQLLM,
            f"Không tìm thấy địa điểm '{location}'. Vui lòng kiểm tra lại tên thành phố.",
            None,
        )
    
    # Step 2: Fetch weather data
    weather_data = fetch_weather(location_info["latitude"], location_info["longitude"])
    if not weather_data:
        return ActionResponse(
            Action.REQLLM,
            "Không thể lấy dữ liệu thời tiết. Vui lòng thử lại sau.",
            None,
        )
    
    # Step 3: Format report
    report = format_weather_report(location_info, weather_data)
    
    logger.bind(tag=TAG).debug(f"Weather report generated for {location}")
    
    return ActionResponse(Action.REQLLM, report, None)
