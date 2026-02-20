"""
Locust load-test scenarios for the FreeCAD AI Designer API.

Run with:
    locust -f tests/load/locustfile.py --host http://localhost:8000

Or headless:
    locust -f tests/load/locustfile.py \
           --host http://localhost:8000 \
           --headless -u 50 -r 5 --run-time 2m \
           --html tests/load/report.html

Scenarios
---------
APIUser          — standard REST workflow (create → poll → export)
HeavyAPIUser     — high-load variant with refinement + delete
ReadOnlyUser     — read-only polling (simulates monitoring dashboards)
WebSocketUser    — WebSocket streaming connection (requires ``locust-plugins``)

Environment variables
---------------------
LOAD_TEST_TOKEN    Bearer token to include in every request (optional).
LOAD_TEST_TIMEOUT  Per-request timeout in seconds (default: 30).
"""

from __future__ import annotations

import json
import logging
import os
import random
import string
import time
from typing import Any

from locust import HttpUser, SequentialTaskSet, TaskSet, between, events, task

logger = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────
_TOKEN: str = os.getenv("LOAD_TEST_TOKEN", "")
_TIMEOUT: float = float(os.getenv("LOAD_TEST_TIMEOUT", "30"))

_HEADERS: dict[str, str] = {"Content-Type": "application/json"}
if _TOKEN:
    _HEADERS["Authorization"] = f"Bearer {_TOKEN}"

# Sample design prompts to spread load across realistic payloads
_PROMPTS = [
    "Create a simple box 50x30x20mm with a 10mm hole",
    "Design a cylindrical bracket with bolt holes",
    "Make a flat plate 100x80mm with 4 corner holes",
    "Create a gear-like disc with 12 teeth",
    "Build a T-shaped extrusion 60x40x5mm",
    "Design a hollow cylinder outer diameter 40mm inner 30mm height 50mm",
    "Create a mounting flange with 6-hole bolt pattern",
    "Make a rectangular enclosure 120x80x40mm with a lid",
]

_EXPORT_FORMATS = ["step", "stl", "obj"]


def _random_prompt() -> str:
    return random.choice(_PROMPTS)


def _random_export() -> str:
    return random.choice(_EXPORT_FORMATS)


def _random_id(length: int = 8) -> str:
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=length))


# ── Shared helpers ────────────────────────────────────────────────────────────


def create_design(client: Any, prompt: str | None = None) -> str | None:
    """POST /api/v1/design — returns request_id or None on failure."""
    payload = {
        "prompt": prompt or _random_prompt(),
        "quality": random.choice(["draft", "standard"]),
        "output_formats": [_random_export()],
    }
    with client.post(
        "/api/v1/design",
        json=payload,
        headers=_HEADERS,
        timeout=_TIMEOUT,
        catch_response=True,
        name="POST /api/v1/design",
    ) as resp:
        if resp.status_code in (200, 201, 202):
            try:
                data = resp.json()
                request_id = data.get("request_id") or data.get("id")
                resp.success()
                return request_id
            except (json.JSONDecodeError, KeyError):
                resp.failure(f"Unexpected response body: {resp.text[:200]}")
                return None
        elif resp.status_code == 401:
            resp.failure("401 Unauthorized — set LOAD_TEST_TOKEN")
            return None
        else:
            resp.failure(f"HTTP {resp.status_code}: {resp.text[:200]}")
            return None


def poll_design(client: Any, request_id: str, max_polls: int = 5) -> dict | None:
    """GET /api/v1/design/{id} — poll until terminal status or max_polls."""
    for _ in range(max_polls):
        with client.get(
            f"/api/v1/design/{request_id}",
            headers=_HEADERS,
            timeout=_TIMEOUT,
            catch_response=True,
            name="GET /api/v1/design/{id}",
        ) as resp:
            if resp.status_code == 200:
                data = resp.json()
                resp.success()
                status = data.get("status", "")
                if status in ("completed", "failed", "error"):
                    return data
                time.sleep(0.5)
            elif resp.status_code == 404:
                resp.success()  # expected for non-existent designs in warm-up
                return None
            else:
                resp.failure(f"HTTP {resp.status_code}")
                return None
    return None


def export_design(client: Any, request_id: str, fmt: str | None = None) -> None:
    """GET /api/v1/design/{id}/export?format=step"""
    export_fmt = fmt or _random_export()
    with client.get(
        f"/api/v1/design/{request_id}/export",
        params={"format": export_fmt},
        headers=_HEADERS,
        timeout=_TIMEOUT,
        catch_response=True,
        name="GET /api/v1/design/{id}/export",
    ) as resp:
        if resp.status_code in (200, 202, 404):
            resp.success()
        else:
            resp.failure(f"HTTP {resp.status_code}")


def refine_design(client: Any, request_id: str) -> None:
    """POST /api/v1/design/{id}/refine"""
    payload = {
        "feedback": random.choice(
            [
                "Make it slightly larger",
                "Add chamfers to the edges",
                "Increase wall thickness to 3mm",
                "Change the hole diameter to 12mm",
            ]
        )
    }
    with client.post(
        f"/api/v1/design/{request_id}/refine",
        json=payload,
        headers=_HEADERS,
        timeout=_TIMEOUT,
        catch_response=True,
        name="POST /api/v1/design/{id}/refine",
    ) as resp:
        if resp.status_code in (200, 202, 404):
            resp.success()
        else:
            resp.failure(f"HTTP {resp.status_code}")


def delete_design(client: Any, request_id: str) -> None:
    """DELETE /api/v1/design/{id}"""
    with client.delete(
        f"/api/v1/design/{request_id}",
        headers=_HEADERS,
        timeout=_TIMEOUT,
        catch_response=True,
        name="DELETE /api/v1/design/{id}",
    ) as resp:
        if resp.status_code in (200, 204, 404):
            resp.success()
        else:
            resp.failure(f"HTTP {resp.status_code}")


# ── Task sets ─────────────────────────────────────────────────────────────────


class DesignWorkflow(SequentialTaskSet):
    """
    Full create → poll → export sequential workflow.
    Simulates a typical end-to-end user session.
    """

    @task
    def step_create(self) -> None:
        self._request_id = create_design(self.client)

    @task
    def step_poll(self) -> None:
        if not getattr(self, "_request_id", None):
            return
        poll_design(self.client, self._request_id)

    @task
    def step_export(self) -> None:
        if not getattr(self, "_request_id", None):
            return
        export_design(self.client, self._request_id)

    @task
    def step_done(self) -> None:
        self._request_id = None
        self.interrupt()


class ReadOnlyBrowsingTasks(TaskSet):
    """
    Read-only tasks: health + polling non-existent IDs.
    Simulates monitoring or dashboard clients.
    """

    @task(3)
    def health_check(self) -> None:
        self.client.get(
            "/health",
            headers=_HEADERS,
            timeout=_TIMEOUT,
            name="GET /health",
        )

    @task(1)
    def poll_nonexistent(self) -> None:
        fake_id = _random_id()
        with self.client.get(
            f"/api/v1/design/{fake_id}",
            headers=_HEADERS,
            timeout=_TIMEOUT,
            catch_response=True,
            name="GET /api/v1/design/{id} [miss]",
        ) as resp:
            if resp.status_code in (200, 404):
                resp.success()
            else:
                resp.failure(f"HTTP {resp.status_code}")


# ── User classes ──────────────────────────────────────────────────────────────


class APIUser(HttpUser):
    """
    Standard user: runs the full design workflow sequentially.

    Weight 6 — represents the majority of real traffic.
    """

    weight = 6
    wait_time = between(1, 4)
    tasks = [DesignWorkflow]


class HeavyAPIUser(HttpUser):
    """
    Heavy user: creates a design, refines it, exports, then deletes.

    Weight 2 — power users / automation scripts.
    """

    weight = 2
    wait_time = between(2, 6)

    @task
    def full_workflow_with_refine(self) -> None:
        request_id = create_design(self.client)
        if not request_id:
            return
        poll_design(self.client, request_id, max_polls=3)
        refine_design(self.client, request_id)
        poll_design(self.client, request_id, max_polls=2)
        export_design(self.client, request_id)
        delete_design(self.client, request_id)


class ReadOnlyUser(HttpUser):
    """
    Read-only monitoring/polling user.

    Weight 2 — represents monitoring dashboards and health checkers.
    """

    weight = 2
    wait_time = between(0.5, 2)
    tasks = [ReadOnlyBrowsingTasks]


# ── WebSocket user (optional — requires locust-plugins) ───────────────────────
try:
    from locust_plugins import run_single_user  # type: ignore[import]
    from locust_plugins.users import WebsocketUser  # type: ignore[import]

    _WS_AVAILABLE = True
except ImportError:
    _WS_AVAILABLE = False


if _WS_AVAILABLE:

    class WebSocketStreamUser(WebsocketUser):  # type: ignore[misc]
        """
        WebSocket streaming scenario.
        Requires ``pip install locust-plugins``.

        Connects to ``/ws/{request_id}`` and listens for SSE-style messages.
        """

        weight = 1
        wait_time = between(3, 8)

        @task
        def stream_design_updates(self) -> None:
            request_id = _random_id()
            self.connect(f"/ws/{request_id}")
            # Listen briefly then disconnect
            time.sleep(random.uniform(1.0, 3.0))
            self.disconnect()


# ── Locust event hooks ─────────────────────────────────────────────────────────


@events.test_start.add_listener
def on_test_start(environment: Any, **kwargs: Any) -> None:
    logger.info(
        "Load test starting — host: %s, token: %s",
        environment.host,
        "set" if _TOKEN else "not set",
    )


@events.test_stop.add_listener
def on_test_stop(environment: Any, **kwargs: Any) -> None:
    stats = environment.stats
    logger.info(
        "Load test finished — total requests: %d, failures: %d",
        stats.total.num_requests,
        stats.total.num_failures,
    )
