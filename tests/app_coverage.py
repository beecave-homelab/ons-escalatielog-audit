"""Summarize V8 function coverage without counting source data or JavaScript evaluations."""

from __future__ import annotations

from typing import Any

import pytest

APP_COVERAGE = pytest.StashKey[dict[str, Any]]()


def summarize_functions(scripts: list[dict[str, Any]], url: str) -> dict[str, Any]:
    """Select only the application document and named functions with a root range."""
    functions = []
    for script in scripts:
        if script["url"] != url:
            continue
        for function in script["functions"]:
            if not function["functionName"] or not function["ranges"]:
                continue
            root = function["ranges"][0]
            functions.append(
                {
                    "name": function["functionName"],
                    "start": root["startOffset"],
                    "end": root["endOffset"],
                    "called": root["count"] > 0,
                }
            )
    if not functions:
        raise ValueError("Geen benoemde applicatiefuncties gemeten; CDP-resultaat is onvolledig.")
    called = sum(function["called"] for function in functions)
    return {
        "called": called,
        "total": len(functions),
        "percentage": round(100 * called / len(functions), 2),
        "uncalled": sorted({function["name"] for function in functions if not function["called"]}),
    }
