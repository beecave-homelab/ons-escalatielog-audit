"""Controleer de publicatiegrens en commitbinding van de Pages-workflow."""

import os
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
APP = "escalatielog-audit-webui.html"
WORKFLOW = yaml.load(
    (ROOT / ".github/workflows/deploy-pages.yml").read_text(), Loader=yaml.BaseLoader
)


def run_step(step, directory, **env):
    return subprocess.run(
        ["bash", "-e", "-o", "pipefail", "-c", step["run"]],
        cwd=directory,
        env={**os.environ, **env},
        capture_output=True,
        text=True,
        check=False,
    )


def test_deployment_requires_ci_and_the_same_commit():
    assert set(WORKFLOW["on"]) == {"push", "workflow_dispatch"}
    assert WORKFLOW["on"]["push"]["branches"] == ["main"]
    assert WORKFLOW["permissions"] == {"contents": "read"}
    assert "concurrency" not in WORKFLOW
    jobs = WORKFLOW["jobs"]
    verify, deploy = jobs["verify"], jobs["deploy"]
    assert deploy["concurrency"] == {
        "group": "pages",
        "queue": "max",
        "cancel-in-progress": "false",
    }
    assert verify["needs"] == "pin"
    assert verify["uses"] == "./.github/workflows/ci.yml"
    revision = verify["with"]["revision"]
    assert revision == "${{ needs.pin.outputs.sha }}"
    assert set(deploy["needs"]) == {"pin", "verify"}
    assert "if" not in deploy  # Default success() blocks failed/skipped verification.
    assert deploy["permissions"] == {
        "contents": "read",
        "pages": "write",
        "id-token": "write",
    }
    assert deploy["environment"]["name"] == "github-pages"
    steps = deploy["steps"]
    assert steps[0]["uses"] == "actions/checkout@v4"
    assert steps[0]["with"]["ref"] == revision
    assert steps[0]["with"]["persist-credentials"] == "false"
    assert steps[1]["uses"] == "actions/configure-pages@v5"
    assert "enablement" not in steps[1].get("with", {})
    assert steps[-3]["uses"] == "actions/upload-pages-artifact@v4"
    assert steps[-3]["with"]["path"] == "${{ steps.stage.outputs.path }}"
    assert steps[-2]["id"] == "current"
    assert steps[-2]["env"]["START_SHA"] == revision
    assert steps[-1]["uses"] == "actions/deploy-pages@v4"


@pytest.fixture
def github_cli(tmp_path):
    cli = tmp_path / "gh"
    cli.write_text(
        "#!/usr/bin/env python3\n"
        "import os, sys\n"
        "assert sys.argv[1:] == ['api', 'repos/example/repo/git/ref/heads/main', "
        "'--jq', '.object.sha']\n"
        "print(os.environ['GH_TEST_SHA'])\n"
        "sys.exit(int(os.environ['GH_TEST_STATUS']))\n"
    )
    cli.chmod(0o755)
    return {
        "PATH": f"{tmp_path}{os.pathsep}{os.environ['PATH']}",
        "GH_REPO": "example/repo",
        "GH_TOKEN": "test-token",
    }


@pytest.mark.parametrize("step_id", ["pin", "current"])
@pytest.mark.parametrize(
    "ref,sha,current,status,accepted",
    [
        ("refs/heads/main", "a" * 40, "a" * 40, "0", True),
        ("refs/heads/dev", "a" * 40, "a" * 40, "0", False),
        ("refs/tags/0.14.0", "a" * 40, "a" * 40, "0", False),
        ("refs/pull/20/merge", "a" * 40, "a" * 40, "0", False),
        ("refs/heads/main", "main", "a" * 40, "0", False),
        ("refs/heads/main", "a" * 40, "b" * 40, "0", False),
        ("refs/heads/main", "a" * 40, "", "0", False),
        ("refs/heads/main", "a" * 40, "a" * 40, "1", False),
    ],
)
def test_only_current_main_can_pass_both_gates(
    tmp_path, github_cli, step_id, ref, sha, current, status, accepted
):
    output = tmp_path / "output"
    job = "pin" if step_id == "pin" else "deploy"
    step = next(s for s in WORKFLOW["jobs"][job]["steps"] if s.get("id") == step_id)
    assert step["shell"] == "bash"
    assert step["env"]["START_REF"] == "${{ github.ref }}"
    assert step["env"]["GH_REPO"] == "${{ github.repository }}"
    assert step["env"]["GH_TOKEN"] == "${{ github.token }}"
    if step_id == "pin":
        assert step["env"]["START_SHA"] == "${{ github.sha }}"
    assert WORKFLOW["jobs"]["pin"]["outputs"]["sha"] == "${{ steps.pin.outputs.sha }}"
    result = run_step(
        step,
        tmp_path,
        **github_cli,
        START_REF=ref,
        START_SHA=sha,
        GH_TEST_SHA=current,
        GH_TEST_STATUS=status,
        GITHUB_OUTPUT=str(output),
    )
    assert (result.returncode == 0) is accepted
    if accepted and step_id == "pin":
        assert output.read_text() == f"sha={sha}\n"
    else:
        assert not output.exists()


def test_main_advancing_after_pin_blocks_publication(tmp_path, github_cli):
    output = tmp_path / "output"
    env = {
        **github_cli,
        "START_REF": "refs/heads/main",
        "START_SHA": "a" * 40,
        "GH_TEST_SHA": "a" * 40,
        "GH_TEST_STATUS": "0",
        "GITHUB_OUTPUT": str(output),
    }
    pin = WORKFLOW["jobs"]["pin"]["steps"][0]
    assert run_step(pin, tmp_path, **env).returncode == 0
    env["GH_TEST_SHA"] = "b" * 40
    current = WORKFLOW["jobs"]["deploy"]["steps"][-2]
    assert run_step(current, tmp_path, **env).returncode != 0
    assert output.read_text() == f"sha={'a' * 40}\n"


@pytest.mark.parametrize("source", ["regular", "missing", "symlink"])
def test_artifact_contains_only_unchanged_html(tmp_path, source):
    checkout = tmp_path / "checkout"
    checkout.mkdir()
    for name in ("escalatielogs/private.xlsx", "exports/private.html", "docs/note.md"):
        path = checkout / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("Do not publish")
    app = checkout / APP
    if source == "regular":
        app.write_bytes((ROOT / APP).read_bytes())
    elif source == "symlink":
        app.symlink_to(checkout / "exports/private.html")
    runner = tmp_path / "runner"
    runner.mkdir()
    (runner / "old-private-file").write_text("Not part of the artifact")
    output = tmp_path / "output"
    step = next(s for s in WORKFLOW["jobs"]["deploy"]["steps"] if s.get("id") == "stage")
    result = run_step(step, checkout, RUNNER_TEMP=str(runner), GITHUB_OUTPUT=str(output))
    if source == "regular":
        assert result.returncode == 0, result.stderr
        artifact = Path(output.read_text().strip().removeprefix("path="))
        assert artifact.parent == runner
        assert [p.name for p in artifact.iterdir()] == [APP]
        assert (artifact / APP).read_bytes() == app.read_bytes()
    else:
        assert result.returncode != 0
        assert not output.exists()
