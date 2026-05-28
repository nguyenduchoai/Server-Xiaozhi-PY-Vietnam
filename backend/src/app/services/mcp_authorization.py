"""MCP tool authorization layer (INT-C2 hardening).

Centralised access-control decisions for MCP tool invocations.

Default policy:
    - Tools listed in DEFAULT_PUBLIC_TOOLS may be called by any authenticated agent.
    - Tools listed in SENSITIVE_TOOLS require explicit per-agent grant.
    - All other tools default-deny when ``strict_mode=True``.

The grant store is intentionally minimal — it can be backed by Redis or DB; for
now we expose a pluggable in-memory store so callers (agent service / endpoint
handlers) can override the resolver via DI.

Audit logging: every authorize() call emits a structured log line with
agent_id, device_id, tool_name and result. Hook this into your central log
pipeline / SIEM.

Usage:
    from app.services.mcp_authorization import (
        McpAuthorizer, McpAuthorizationDenied, mcp_authorizer,
    )

    mcp_authorizer.authorize(
        agent_id=agent.id, device_id=device.id, tool_name="self.camera.take_photo",
    )
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Optional, Set

from app.core.logger import setup_logging

TAG = __name__


class McpAuthorizationDenied(Exception):
    """Raised when an MCP tool invocation fails the authorization check."""


# Tools considered safe enough to allow by default for any authenticated agent.
DEFAULT_PUBLIC_TOOLS: Set[str] = {
    "self.get_device_status",
    "self.get_battery_level",
    "self.get_volume",
    "self.get_brightness",
}

# Tools that touch user-private state (camera, microphone, screen capture,
# firmware upgrade, file system, network reconfig). Always require explicit
# grant — never allow by default.
SENSITIVE_TOOLS: Set[str] = {
    "self.camera.take_photo",
    "self.camera.start_stream",
    "self.camera.stop_stream",
    "self.screen.set_brightness",
    "self.screen.capture",
    "self.audio.start_recording",
    "self.audio.stop_recording",
    "self.system.factory_reset",
    "self.system.upgrade_firmware",
    "self.network.set_wifi",
    "self.fs.read_file",
    "self.fs.write_file",
}


# Capability gating: each tool requires the device's BoardCapability JSON
# to satisfy the predicate(s) listed here. If the device hasn't reported
# a capability profile yet (caps == None), the tool is allowed (legacy FW
# compat). Once a profile is present, predicates must pass.
#
# Keys here can be:
#   - exact tool name: "self.camera.take_photo"
#   - prefix wildcard: "self.camera.*" (matches any tool starting with prefix)
#
# The value is a callable taking the capability dict and returning True if
# the tool is supported on this hardware.
CAPABILITY_REQUIREMENTS = {
    "self.camera.*":   lambda c: bool(c.get("can_camera")),
    "self.vision.*":   lambda c: bool(c.get("can_vision")),
    "self.video.*":    lambda c: bool(c.get("can_video")),
    "self.meeting.*":  lambda c: bool(c.get("can_meeting")),
    "self.sales.*":    lambda c: bool(c.get("can_sales")),
    "self.sd.*":       lambda c: bool(c.get("has_sd")),
    "self.touch.*":    lambda c: bool(c.get("has_touch")),
    "self.screen.set_brightness": lambda c: bool(c.get("has_backlight")),
}


def _capability_check(tool_name: str, caps: Optional[dict]) -> bool:
    """Return True if the device hardware supports this tool.

    None caps == legacy FW that doesn't report capabilities → allow (caller
    can layer a stricter check upstream). Match exact name first, then
    prefix wildcards.
    """
    if not caps:
        return True
    if tool_name in CAPABILITY_REQUIREMENTS:
        return bool(CAPABILITY_REQUIREMENTS[tool_name](caps))
    for pattern, predicate in CAPABILITY_REQUIREMENTS.items():
        if pattern.endswith(".*"):
            prefix = pattern[:-2]  # drop ".*"
            if tool_name.startswith(prefix + ".") or tool_name == prefix:
                return bool(predicate(caps))
    return True


@dataclass
class _GrantStore:
    """In-memory grant store. Replace with Redis/DB in production."""

    # Map (agent_id, tool_name) -> True if explicitly granted.
    grants: dict = field(default_factory=dict)

    def grant(self, agent_id: str, tool_name: str) -> None:
        self.grants[(str(agent_id), tool_name)] = True

    def revoke(self, agent_id: str, tool_name: str) -> None:
        self.grants.pop((str(agent_id), tool_name), None)

    def has(self, agent_id: str, tool_name: str) -> bool:
        return self.grants.get((str(agent_id), tool_name), False)


class McpAuthorizer:
    """Authorize MCP tool calls. Default-deny for sensitive tools."""

    def __init__(
        self,
        public_tools: Optional[Iterable[str]] = None,
        sensitive_tools: Optional[Iterable[str]] = None,
        strict_mode: bool = False,
        store: Optional[_GrantStore] = None,
    ) -> None:
        self.public_tools: Set[str] = set(public_tools or DEFAULT_PUBLIC_TOOLS)
        self.sensitive_tools: Set[str] = set(sensitive_tools or SENSITIVE_TOOLS)
        self.strict_mode = strict_mode
        self.store = store or _GrantStore()
        self.logger = setup_logging()

    def grant(self, agent_id: str, tool_name: str) -> None:
        """Explicitly allow ``agent_id`` to call ``tool_name``."""
        self.store.grant(agent_id, tool_name)

    def revoke(self, agent_id: str, tool_name: str) -> None:
        self.store.revoke(agent_id, tool_name)

    def is_allowed(
        self,
        agent_id: Optional[str],
        tool_name: str,
        device_capabilities: Optional[dict] = None,
    ) -> bool:
        """Pure check (no exception). Useful for UI to render disabled state.

        Combines two gates:
          (1) policy gate (public / sensitive grant store)
          (2) hardware capability gate (e.g., self.camera.* requires can_camera)
        """
        if not tool_name:
            return False
        # Hardware gate first — even a granted tool can't run on a device
        # whose hardware doesn't support it.
        if not _capability_check(tool_name, device_capabilities):
            return False
        if tool_name in self.public_tools:
            return True
        if tool_name in self.sensitive_tools:
            return bool(agent_id) and self.store.has(agent_id, tool_name)
        # Unknown tool: strict mode denies, otherwise allow
        return not self.strict_mode

    def authorize(
        self,
        *,
        agent_id: Optional[str],
        device_id: Optional[str],
        tool_name: str,
        device_capabilities: Optional[dict] = None,
    ) -> None:
        """Authorize or raise McpAuthorizationDenied. Always emits audit log."""
        # Compute reason for richer audit
        cap_ok = _capability_check(tool_name, device_capabilities)
        allowed = self.is_allowed(agent_id, tool_name, device_capabilities)
        reason = "allow" if allowed else (
            "deny:capability" if not cap_ok else "deny:policy"
        )
        self.logger.bind(tag=TAG).info(
            "mcp_call agent_id=%s device_id=%s tool=%s result=%s",
            agent_id, device_id, tool_name, reason,
        )
        if not allowed:
            if not cap_ok:
                raise McpAuthorizationDenied(
                    f"Tool {tool_name!r} not supported by device hardware "
                    f"(capabilities mismatch)"
                )
            raise McpAuthorizationDenied(
                f"Agent {agent_id!r} not authorized to invoke MCP tool {tool_name!r}"
            )

    def filter_tools_for_device(
        self,
        agent_id: Optional[str],
        tool_names: list[str],
        device_capabilities: Optional[dict],
    ) -> list[str]:
        """Return only tools allowed for this (agent, device) combo.

        Use this when advertising the tool list to the LLM — never list a
        tool the LLM might call which the device hardware can't fulfill.
        """
        return [
            t for t in tool_names
            if self.is_allowed(agent_id, t, device_capabilities)
        ]


# Default singleton — strict mode off so existing tools keep working until
# explicit grants are migrated. Flip to True after migration.
mcp_authorizer = McpAuthorizer(strict_mode=False)
