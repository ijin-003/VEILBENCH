import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
FRONTEND = ROOT / "frontend"


def test_frontend_pins_supported_next16_security_stack():
    package = json.loads((FRONTEND / "package.json").read_text(encoding="utf-8"))

    assert package["dependencies"]["next"] == "16.4.6"
    assert package["dependencies"]["react"] == "19.3.1"
    assert package["dependencies"]["react-dom"] == "19.3.1"
    assert package["devDependencies"]["@types/react"] == "19.3.0"
    assert package["devDependencies"]["@types/react-dom"] == "19.3.0"
    assert package["devDependencies"]["eslint"] == "10.15.0"
    assert package["devDependencies"]["@eslint/js"] == "10.0.1"
    assert package["devDependencies"]["@next/eslint-plugin-next"] == "16.4.6"
    assert package["devDependencies"]["eslint-plugin-react-hooks"] == "7.1.1"
    assert package["devDependencies"]["typescript-eslint"] == "8.73.0"
    assert "eslint-config-next" not in package["devDependencies"]
    assert package["devDependencies"]["postcss"] == "8.5.33"
    assert package["engines"]["node"] == "^22.13.0 || ^24.0.0"
    assert package["scripts"]["lint"] == "eslint ."


def test_health_check_effect_uses_async_request_without_stateful_callback():
    source = (FRONTEND / "src/app/AdminDashboard.tsx").read_text(encoding="utf-8")
    request_start = source.index("const requestHealth = useCallback")
    check_start = source.index("const checkHealth = useCallback", request_start)
    effect_start = source.index("useEffect(() => {", check_start)
    effect_end = source.index("const managementRequest", effect_start)

    request_helper = source[request_start:check_start]
    manual_callback = source[check_start:effect_start]
    effect = source[effect_start:effect_end]

    assert "setHealth(" not in request_helper
    assert "setError(" not in request_helper
    assert "setHealthLoading(" not in request_helper
    assert "setHealthLoading(true)" in manual_callback
    assert "requestHealth()" in manual_callback
    assert "requestHealth(controller.signal)" in effect
    assert "void checkHealth()" not in effect
    # The callback parameter name is irrelevant to the async effect invariant.
    assert re.search(r"\.then\(\([a-zA-Z_$][\w$]*\)\s*=>", effect)
    assert "setHealth(" in effect
    assert "controller.abort()" in effect


def test_frontend_uses_eslint10_compatible_direct_plugins():
    config = (FRONTEND / "eslint.config.mjs").read_text(encoding="utf-8")

    assert '@next/eslint-plugin-next' in config
    assert 'eslint-plugin-react-hooks' in config
    assert 'typescript-eslint' in config
    assert 'js.configs.recommended' in config
    assert "eslint-config-next" not in config
    assert not (FRONTEND / ".eslintrc.json").exists()


def test_founder_route_uses_async_next_app_router_params():
    page = (FRONTEND / "src/app/submit/[sessionId]/[partyId]/page.tsx").read_text(encoding="utf-8")
    form = (FRONTEND / "src/app/submit/[sessionId]/[partyId]/FounderSubmissionForm.tsx").read_text(
        encoding="utf-8"
    )

    assert "params: Promise<FounderRouteParams>" in page
    assert "await params" in page
    assert "FounderSubmissionForm" in page
    assert '"use client"' in form
    assert "params.sessionId" not in form
    assert "params.partyId" not in form


def test_frontend_docker_uses_node22_for_all_stages():
    dockerfile = (ROOT / "infrastructure/Dockerfile.frontend").read_text(encoding="utf-8")
    assert dockerfile.count("FROM node:22-alpine") == 3
    assert "node:20-alpine" not in dockerfile
