"""Non-destructive HTTPS smoke checks against the deployed academic demo.

Uses only GET requests; no login, production account, salary, or invitation.
Invoked by GitHub Actions, where outbound HTTPS is available.
"""
import os
import sys
import time
import urllib.error
import urllib.request

ORIGIN = os.environ.get("VEILBENCH_SMOKE_ORIGIN", "https://veilbench-poc-go1d.onrender.com").rstrip("/")

# Route, required status. Swagger/OpenAPI must not be available in demo mode.
CHECKS = [
    ("/health/ready", 200),
    ("/party/0/health", 200),
    ("/party/1/health", 200),
    ("/party/2/health", 200),
    ("/docs", 404),
    ("/redoc", 404),
    ("/openapi.json", 404),
    *[(f"/party/{i}/{path}", 404) for i in range(3) for path in ("docs", "redoc", "openapi.json")],
    ("/api/v1/accounts/assignment", 401),
    ("/party/0/sessions/nonexistent/status", 401),
]


def check(path: str, expected: int) -> bool:
    url = ORIGIN + path
    request = urllib.request.Request(
        url, headers={"User-Agent": "VEILBENCH-academic-security-smoke/1.0"}
    )
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=100 if path == "/health/ready" else 25) as response:
                actual = response.status
        except urllib.error.HTTPError as error:
            actual = error.code
            error.close()
        except (urllib.error.URLError, TimeoutError) as error:
            print(f"ATTEMPT {attempt + 1}: {path} network error: {type(error).__name__}", flush=True)
            if attempt < 2:
                time.sleep(4)
                continue
            return False
        print(f"{'PASS' if actual == expected else 'FAIL'} {path}: HTTP {actual}, expected {expected}", flush=True)
        return actual == expected
    return False


def main() -> int:
    if not ORIGIN.startswith("https://"):
        print("Refusing non-HTTPS smoke target", file=sys.stderr)
        return 2
    passed = sum(check(path, expected) for path, expected in CHECKS)
    print(f"Live non-destructive endpoint checks: {passed}/{len(CHECKS)} passed")
    return 0 if passed == len(CHECKS) else 1


if __name__ == "__main__":
    raise SystemExit(main())
