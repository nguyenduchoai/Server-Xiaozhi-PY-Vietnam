#!/usr/bin/env python3
"""
Automated Health Check Script for Xiaozhi AI IoT Platform

Checks all critical service endpoints and logs results.
Designed to run via cron every 5 minutes.

Usage:
    python health_check.py              # Run all checks
    python health_check.py --verbose    # Verbose output

Exit codes:
    0 = All services healthy
    1 = One or more services unhealthy
"""

import asyncio
import logging
import sys
import time
from dataclasses import dataclass
from typing import Optional

import httpx

# ============ Configuration ============

BASE_URL = "https://xiaozhi-ai-iot.vn"
API_BASE = f"{BASE_URL}/api/v1"
TIMEOUT = 10  # seconds per request

CHECKS = [
    # (name, url, expected_status, description)
    ("Frontend", BASE_URL, 200, "Main website"),
    ("API Health", f"{API_BASE}/health", 200, "Backend API health"),
    ("Auth Login", f"{API_BASE}/auth/login", 405, "Auth endpoint exists (405 = no GET)"),
    ("Docs Guide", f"{API_BASE}/docs-guide/", 200, "Documentation page"),
    ("Board Registry", f"{API_BASE}/boards", 200, "Board info endpoint"),
    ("Theme Categories", f"{API_BASE}/themes/categories", 200, "Theme categories"),
    ("Subscription Plans", f"{API_BASE}/subscription/plans", 200, "Plan listing"),
    ("TTS Services", f"{API_BASE}/docs-guide/status/services", 200, "TTS service health"),
]

# Internal Docker services (only check if running inside Docker)
INTERNAL_CHECKS = [
    ("PostgreSQL", "http://xiaozhi-db:5432", None, "Database"),
    ("Redis", "http://xiaozhi-redis:6379", None, "Cache/Queue"),
    ("EMQX MQTT", "http://xiaozhi-emqx:18083/api/v5/status", 200, "MQTT Broker"),
]

# Logging setup
LOG_FILE = "/var/log/xiaozhi-health.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_FILE, mode="a"),
    ],
)
logger = logging.getLogger("health_check")


# ============ Models ============


@dataclass
class CheckResult:
    name: str
    url: str
    status: str  # "ok", "warn", "fail"
    response_time_ms: float = 0
    status_code: Optional[int] = None
    error: Optional[str] = None
    description: str = ""


# ============ Health Check Logic ============


async def check_endpoint(
    client: httpx.AsyncClient,
    name: str,
    url: str,
    expected_status: Optional[int],
    description: str,
) -> CheckResult:
    """Check a single endpoint."""
    start = time.monotonic()
    try:
        response = await client.get(url, follow_redirects=True)
        elapsed_ms = (time.monotonic() - start) * 1000

        if expected_status is None:
            # Just check connectivity
            status = "ok" if response.status_code < 500 else "fail"
        elif response.status_code == expected_status:
            status = "ok"
        elif response.status_code < 500:
            status = "warn"
        else:
            status = "fail"

        # Warn if response time > 3s
        if elapsed_ms > 3000 and status == "ok":
            status = "warn"

        return CheckResult(
            name=name,
            url=url,
            status=status,
            response_time_ms=round(elapsed_ms, 1),
            status_code=response.status_code,
            description=description,
        )

    except httpx.ConnectError as e:
        elapsed_ms = (time.monotonic() - start) * 1000
        return CheckResult(
            name=name,
            url=url,
            status="fail",
            response_time_ms=round(elapsed_ms, 1),
            error=f"Connection refused: {e}",
            description=description,
        )
    except httpx.TimeoutException:
        elapsed_ms = (time.monotonic() - start) * 1000
        return CheckResult(
            name=name,
            url=url,
            status="fail",
            response_time_ms=round(elapsed_ms, 1),
            error=f"Timeout after {TIMEOUT}s",
            description=description,
        )
    except Exception as e:
        elapsed_ms = (time.monotonic() - start) * 1000
        return CheckResult(
            name=name,
            url=url,
            status="fail",
            response_time_ms=round(elapsed_ms, 1),
            error=str(e),
            description=description,
        )


async def run_checks(verbose: bool = False) -> list[CheckResult]:
    """Run all health checks concurrently."""
    results = []

    async with httpx.AsyncClient(
        timeout=TIMEOUT,
        verify=False,  # Allow self-signed certs in dev
    ) as client:
        # Run public checks in parallel
        tasks = [
            check_endpoint(client, name, url, status, desc)
            for name, url, status, desc in CHECKS
        ]
        results = await asyncio.gather(*tasks)

        # Try internal checks (may not be accessible)
        if verbose:
            internal_tasks = [
                check_endpoint(client, name, url, status, desc)
                for name, url, status, desc in INTERNAL_CHECKS
            ]
            internal_results = await asyncio.gather(*internal_tasks)
            results = list(results) + list(internal_results)

    return list(results)


def print_results(results: list[CheckResult], verbose: bool = False):
    """Print results in a readable format."""
    status_icons = {"ok": "✅", "warn": "⚠️", "fail": "❌"}

    ok_count = sum(1 for r in results if r.status == "ok")
    warn_count = sum(1 for r in results if r.status == "warn")
    fail_count = sum(1 for r in results if r.status == "fail")
    total = len(results)

    logger.info(f"{'='*60}")
    logger.info(f"  Xiaozhi Health Check — {ok_count}/{total} passed")
    logger.info(f"{'='*60}")

    for r in results:
        icon = status_icons.get(r.status, "❓")
        time_str = f"{r.response_time_ms:.0f}ms"

        if r.status == "ok":
            logger.info(f"  {icon} {r.name:25s} {r.status_code or '-':>5}  {time_str:>8}")
        elif r.status == "warn":
            logger.warning(
                f"  {icon} {r.name:25s} {r.status_code or '-':>5}  {time_str:>8}  ← {r.error or 'unexpected status'}"
            )
        else:
            logger.error(
                f"  {icon} {r.name:25s} {'ERR':>5}  {time_str:>8}  ← {r.error or 'FAILED'}"
            )

    logger.info(f"{'='*60}")

    if fail_count > 0:
        logger.error(f"  ❌ {fail_count} service(s) DOWN")
    elif warn_count > 0:
        logger.warning(f"  ⚠️  {warn_count} warning(s)")
    else:
        logger.info(f"  ✅ All {total} services healthy")

    logger.info(f"{'='*60}")


# ============ Main ============


async def main():
    verbose = "--verbose" in sys.argv or "-v" in sys.argv

    results = await run_checks(verbose=verbose)
    print_results(results, verbose=verbose)

    # Exit code: 1 if any failures
    has_failures = any(r.status == "fail" for r in results)
    sys.exit(1 if has_failures else 0)


if __name__ == "__main__":
    asyncio.run(main())
