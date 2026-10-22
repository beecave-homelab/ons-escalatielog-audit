"""Check the hardening of the GitHub Actions workflows and the shared checklist."""

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = sorted((ROOT / ".github/workflows").glob("*.yml"))
PINNED = re.compile(r"^[\w.-]+/[\w.-]+@[0-9a-f]{40}$")
VERSION_COMMENT = re.compile(r"# v\d+\.\d+\.\d+\s*$")


def load(path):
    return yaml.load(path.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)


def iter_uses(node):
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "uses":
                yield value
            else:
                yield from iter_uses(value)
    elif isinstance(node, list):
        for item in node:
            yield from iter_uses(item)


def iter_steps(workflow):
    for job in workflow["jobs"].values():
        yield from job.get("steps") or []


def test_actions_are_pinned_to_full_sha_with_version_comment():
    for path in WORKFLOWS:
        for use in iter_uses(load(path)):
            if use.startswith("./"):
                continue
            assert PINNED.fullmatch(use), f"{path.name}: {use}"
        for line in path.read_text(encoding="utf-8").splitlines():
            if "uses:" in line and "./." not in line:
                assert VERSION_COMMENT.search(line), f"{path.name}: {line.strip()}"


def test_every_workflow_has_explicit_permissions():
    for path in WORKFLOWS:
        workflow = load(path)
        if "permissions" in workflow:
            continue
        assert workflow["jobs"], path.name
        assert all("permissions" in job for job in workflow["jobs"].values()), path.name


def test_checkout_never_persists_credentials():
    for path in WORKFLOWS:
        for step in iter_steps(load(path)):
            if step.get("uses", "").startswith("actions/checkout@"):
                assert step.get("with", {}).get("persist-credentials") == "false", (
                    f"{path.name}: checkout zonder persist-credentials: false"
                )


def test_uv_version_pin_matches_install_script():
    script = (ROOT / "scripts/install-dependencies.sh").read_text(encoding="utf-8")
    pinned = re.search(r'UV_VERSION="([^"]+)"', script)[1]
    for path in WORKFLOWS:
        for step in iter_steps(load(path)):
            if step.get("uses", "").startswith("astral-sh/setup-uv@"):
                assert step["with"]["version"] == pinned, path.name


def test_ci_checks_job_runs_shared_check_list():
    workflow = load(ROOT / ".github/workflows/ci.yml")
    runs = [step.get("run", "") for step in workflow["jobs"]["checks"]["steps"]]
    assert "scripts/run-checks.sh" in runs


def test_install_dependencies_calls_shared_check_list():
    script = (ROOT / "scripts/install-dependencies.sh").read_text(encoding="utf-8")
    assert "scripts/run-checks.sh" in script
