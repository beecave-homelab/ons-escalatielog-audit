"""Controleer de SVG-tekstcontrole in root-coördinaten met tijdelijke SVG's."""

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "check-svg-text-bounds.sh"


def write_svg(tmp_path, name, inner, attrs='viewBox="0 0 200 100"'):
    svg = tmp_path / name
    svg.write_text(
        f'<svg xmlns="http://www.w3.org/2000/svg" {attrs}>{inner}</svg>',
        encoding="utf-8",
    )
    return svg


def run(*svgs):
    return subprocess.run(
        ["bash", str(SCRIPT), *(str(svg) for svg in svgs)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )


def test_plain_text_inside_passes(tmp_path):
    svg = write_svg(tmp_path, "binnen.svg", '<text x="10" y="50">ok</text>')
    assert run(svg).returncode == 0


def test_transform_pushed_outside_fails(tmp_path):
    svg = write_svg(
        tmp_path,
        "buiten.svg",
        '<g transform="translate(300,0)"><text x="10" y="50">buiten</text></g>',
    )
    result = run(svg)
    assert result.returncode == 1
    assert "buiten" in result.stdout


def test_transform_bringing_text_inside_passes(tmp_path):
    svg = write_svg(
        tmp_path,
        "verschoven.svg",
        '<g transform="translate(-400,0)"><text x="420" y="50">binnen</text></g>',
    )
    assert run(svg).returncode == 0


def test_negative_viewbox_offset_passes(tmp_path):
    svg = write_svg(
        tmp_path,
        "negatief.svg",
        '<text x="-90" y="50">ok</text>',
        attrs='viewBox="-100 0 200 100"',
    )
    assert run(svg).returncode == 0


def test_positive_viewbox_offset_fails(tmp_path):
    svg = write_svg(
        tmp_path,
        "positief.svg",
        '<text x="20" y="50">buiten</text>',
        attrs='viewBox="100 0 200 100"',
    )
    assert run(svg).returncode == 1


def test_missing_viewbox_fails(tmp_path):
    svg = write_svg(tmp_path, "zonder.svg", '<text x="10" y="50">ok</text>', attrs="")
    result = run(svg)
    assert result.returncode == 1
    assert "geen viewBox" in result.stdout
