# Load tests

This directory contains [Locust](https://locust.io/) load-test scenarios for the FreeCAD AI Designer API.

## Quick start

```bash
# Install locust (already in requirements-dev.txt)
pip install locust

# Run interactive web UI (open http://localhost:8089)
locust -f tests/load/locustfile.py --host http://localhost:8000

# Headless run — 50 users, ramp 5/s, 2 minutes
locust -f tests/load/locustfile.py \
       --host http://localhost:8000 \
       --headless -u 50 -r 5 --run-time 2m \
       --html tests/load/report.html
```

## Scenarios

| User class | Weight | Description |
|---|---|---|
| `APIUser` | 6 | Full create → poll → export sequential workflow |
| `HeavyAPIUser` | 2 | Create → refine → export → delete |
| `ReadOnlyUser` | 2 | Health checks + polling (monitoring dashboards) |
| `WebSocketStreamUser` | 1 | WebSocket streaming (requires `locust-plugins`) |

## Auth

Set `LOAD_TEST_TOKEN` to include a Bearer token in every request:

```bash
export LOAD_TEST_TOKEN="your-jwt-here"
locust -f tests/load/locustfile.py --host http://localhost:8000
```

## WebSocket scenario

```bash
pip install locust-plugins
locust -f tests/load/locustfile.py --host http://localhost:8000
```
