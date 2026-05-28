"""
Config Loader - Load config từ YAML files với multi-source merge support
"""

import os
import re
from copy import deepcopy
from pathlib import Path
from threading import RLock
from typing import Dict, Any, Iterable, Optional, Tuple

import yaml


# Expand ${VAR} and ${VAR:-default} placeholders in YAML string values.
# Required for the BE-C4 hardening migration where config.yml stores
# placeholders like "${SERVER_AUTH_KEY}" / "${OPENAI_API_KEY}" instead of
# real secrets. Without expansion, providers/firmware-auth would HMAC against
# the literal "${SERVER_AUTH_KEY}" → all device tokens fail verification.
_ENV_VAR_RE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)(?::-(.*?))?\}")


def _expand_env_in_value(value: Any) -> Any:
    """Recursively expand ${ENV_VAR} / ${ENV_VAR:-default} in strings."""
    if isinstance(value, str):
        def _sub(match: "re.Match[str]") -> str:
            name = match.group(1)
            default = match.group(2) or ""
            return os.environ.get(name, default)
        return _ENV_VAR_RE.sub(_sub, value)
    if isinstance(value, dict):
        return {k: _expand_env_in_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_expand_env_in_value(v) for v in value]
    return value

_BASE_DIR = Path(__file__).resolve().parents[2]
_BASE_CONFIG_PATH: Optional[Path] = None  # Base config: app/ai/config/config.yml
_OVERRIDE_CONFIG_PATH: Optional[Path] = None  # Override config: app/data/.config.yml
_CACHE_LOCK = RLock()
_CONFIG_CACHE: Optional[Dict[str, Any]] = None
ConfigSignature = Tuple[Tuple[str, int, int, bool], ...]
_CONFIG_SIGNATURE: Optional[ConfigSignature] = None


def _read_yaml(path: str) -> Dict[str, Any]:
    """Đọc YAML và trả về dict rỗng nếu file trống."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception as e:
        print(f"⚠️  Lỗi load config từ {path}: {e}")
        return {}


def _build_signature(paths: Iterable[Path]) -> ConfigSignature:
    signature = []
    for path in paths:
        try:
            stat = path.stat()
        except FileNotFoundError:
            signature.append((str(path), 0, 0, False))
        except OSError:
            signature.append((str(path), 0, 0, False))
        else:
            signature.append((str(path), int(stat.st_mtime_ns), stat.st_size, True))
    return tuple(signature)


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deep merge hai config dicts.
    Override config sẽ merge từng key với base, cho phép giữ lại items
    từ base mà không có trong override.

    Args:
        base: Config gốc (ưu tiên thấp)
        override: Config override (ưu tiên cao)

    Returns:
        Dict merged với deep merge strategy
    """
    result = deepcopy(base)
    
    for key, override_value in override.items():
        if key in result:
            base_value = result[key]
            # If both are dicts, recursively merge them
            if isinstance(base_value, dict) and isinstance(override_value, dict):
                result[key] = _deep_merge(base_value, override_value)
            else:
                # Otherwise, override wins
                result[key] = deepcopy(override_value)
        else:
            # Key only in override
            result[key] = deepcopy(override_value)
    
    return result


def _shallow_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """
    [DEPRECATED] Use _deep_merge instead.
    Shallow merge hai config dicts.
    Override config sẽ ghi đè toàn bộ top-level key của base.
    """
    result = deepcopy(base)
    result.update(override)
    return result


def load_config(force_reload: bool = False) -> Dict[str, Any]:
    """
    Load config từ 2 nguồn và merge với shallow merge strategy.

    Files:
        1. Base config: src/app/ai/config/config.yml (default settings)
        2. Override config: src/app/data/.config.yml (user overrides, ưu tiên cao)

    Merge behavior:
        - Shallow merge: override config ghi đè toàn bộ top-level key
        - Nếu cả 2 file có cùng key, override wins entire section
        - Cache được invalidate khi bất kỳ file nào thay đổi

    Args:
        force_reload: Bỏ qua cache và load lại từ files

    Returns:
        Dict[str, Any]: Merged config
    """
    global _BASE_CONFIG_PATH, _OVERRIDE_CONFIG_PATH

    # Lazy import để tránh circular dependency
    if _BASE_CONFIG_PATH is None or _OVERRIDE_CONFIG_PATH is None:
        from app.ai.utils.paths import get_base_config_file, get_config_file

        _BASE_CONFIG_PATH = get_base_config_file()
        _OVERRIDE_CONFIG_PATH = get_config_file()

    cache_paths = [_BASE_CONFIG_PATH, _OVERRIDE_CONFIG_PATH]
    current_signature = _build_signature(cache_paths)

    with _CACHE_LOCK:
        global _CONFIG_CACHE, _CONFIG_SIGNATURE

        if (
            not force_reload
            and _CONFIG_CACHE is not None
            and _CONFIG_SIGNATURE == current_signature
        ):
            return deepcopy(_CONFIG_CACHE)

        # Load base config
        base_config: Dict[str, Any] = {}
        if _BASE_CONFIG_PATH.exists():
            base_config = _read_yaml(str(_BASE_CONFIG_PATH))
            print(f"✅ Base config loaded từ: {_BASE_CONFIG_PATH}")

        # Load override config
        override_config: Dict[str, Any] = {}
        if _OVERRIDE_CONFIG_PATH.exists():
            override_config = _read_yaml(str(_OVERRIDE_CONFIG_PATH))
            print(f"✅ Override config loaded từ: {_OVERRIDE_CONFIG_PATH}")

        # Merge configs with deep merge (preserves nested keys from base)
        if base_config or override_config:
            config = _deep_merge(base_config, override_config)
            print(f"✅ Config merged (base + override) với deep merge")
        else:
            print("⚠️  Không tìm thấy config files, dùng default fallback")
            config = get_default_config()

        # Expand ${ENV_VAR} placeholders AFTER merge so user can override
        # via env without touching files (twelve-factor friendly).
        config = _expand_env_in_value(config)

        _CONFIG_CACHE = config
        _CONFIG_SIGNATURE = _build_signature(cache_paths)
        return deepcopy(config)


def get_default_config() -> Dict[str, Any]:
    """Get default config"""
    return {
        "server": {
            "ip": "0.0.0.0",
            "port": 8000,
            "http_port": 8003,
            "auth_key": "default-key",
            "auth": {
                "enabled": False,
                "allowed_devices": [],
            },
        },
        "log": {
            "log_level": "INFO",
            "log_dir": "logs",
            "log_file": "app.log",
            "log_format": "<green>{time:YYMMDD HH:mm:ss}</green>[{version}_{extra[selected_module]}][<light-blue>{extra[tag]}</light-blue>]-<level>{level}</level>-<light-green>{message}</light-green>",
            "log_format_file": "{time:YYYY-MM-DD HH:mm:ss} - {version}_{extra[selected_module]} - {name} - {level} - {extra[tag]} - {message}",
            "selected_module": "00000000000000",
        },
        "selected_module": {},
        "read_config_from_api": False,
        "exit_commands": ["exit", "quit"],
        "close_connection_no_voice_time": 120,
        "delete_audio": True,
        "message_welcome": {
            "type": "hello",
            "version": 1,
            "transport": "websocket",
            "audio_params": {
                "format": "opus",
                "sample_rate": 16000,
                "channels": 1,
                "frame_duration": 60,
            },
        },
    }


def get_project_dir():
    """
    Lấy thư mục gốc của dự án (nơi chứa run.py, data/, etc)
    Returns: /path/to/fastapi-server-v2/
    """
    return str(_BASE_DIR) + "/"


def get_data_dir():
    """
    Lấy thư mục data
    Returns: /path/to/fastapi-server-v2/data/
    """
    return str(_BASE_DIR / "data") + "/"
