# SPDX-License-Identifier: AGPL-3.0-only
"""Render recorded mechanics benchmarks and upstream blockers as a local HTML page."""

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path
from typing import Any


def _escape(value: Any) -> str:
    return html.escape(str(value), quote=True)


def _number(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.10g}"
    return _escape(value)


def render_html(mechanics: dict[str, Any], upstream: dict[str, Any]) -> str:
    """Produce a self-contained page; all recorded values remain in the JSON reports."""
    cases = mechanics["cases"]
    analytical = [case for case in cases if case["verification_type"] == "analytical"]
    relative_errors = [
        100 * check["relative_error"]
        for case in analytical
        for check in case.get("checks", [])
        if check.get("relative_error") is not None and check["expected"] != 0
    ]
    checks = sum(len(case.get("checks", [])) for case in cases)
    maximum = max(relative_errors, default=0)
    aggregate = mechanics["aggregate"]
    content = [
        "<!doctype html><html lang='en'><meta charset='utf-8'>",
        "<meta name='viewport' content='width=device-width,initial-scale=1'>",
        "<title>EngCalcs concrete section verification</title>",
        "<style>body{margin:0;background:#f4f6f8;color:#182b3a;font:16px/1.5 system-ui}",
        "main{max-width:1200px;margin:auto;padding:32px}h1{line-height:1.15}",
        ".cards{display:flex;gap:16px;flex-wrap:wrap}.card,details{background:white;",
        "border:1px solid #d7dfe5;border-radius:8px;padding:18px;margin:14px 0}",
        ".card{flex:1;min-width:180px}.card strong{display:block;font-size:28px}",
        ".pass{color:#086d46}.failed,.blocked{color:#a32a20}.scope{border-left:5px solid #d98b20;",
        "background:#fff8eb;padding:16px}summary{cursor:pointer;font-weight:650}",
        "table{border-collapse:collapse;width:100%;font-size:14px}td,th{padding:10px;",
        "border-bottom:1px solid #d7dfe5;text-align:left;vertical-align:top}",
        "th{background:#f0f4f7}.scroll{overflow:auto}code{white-space:nowrap}",
        "pre{white-space:pre-wrap;overflow-wrap:anywhere}input{font:inherit;padding:10px;",
        "width:100%;box-sizing:border-box;border:1px solid #b4c3ce;border-radius:5px}",
        "@media print{input,button{display:none}details{break-inside:avoid}}</style>",
        "<main><p>EngCalcs · concrete sections</p><h1>Verification results</h1>",
        "<p>Repeatable comparisons with original independent mechanics references.</p>",
        "<p class='scope'><strong>AS 3600 design compliance is not evaluated.</strong> ",
        "Passing mechanics cases do not establish design compliance. The upstream AS3600 ",
        "design adapter is disabled and its unresolved integration findings are shown below.</p>",
        "<div class='cards'>",
        f"<div class='card'><strong>{aggregate['passed']}/{aggregate['case_count']}</strong>",
        "mechanics cases passed</div>",
        f"<div class='card'><strong>{checks}</strong>individual comparisons</div>",
        f"<div class='card'><strong>{maximum:.6g}%</strong>",
        "largest analytical relative difference (nonzero references)</div>",
        f"<div class='card blocked'><strong>{upstream['aggregate']['blocked']}</strong>",
        "upstream design integration blockers</div></div>",
        "<h2>Methodology</h2><p>Analytical references use equilibrium, strain compatibility ",
        "and transformed section properties calculated independently of the solver. ",
        "Rotation invariance is labeled as a metamorphic check. Invalid-input cases test ",
        "the rejection contract. Each comparison has its own units, tolerance and outcome. ",
        "Zero references use absolute error; a percentage is not meaningful for them.</p>",
        "<p>These fixtures are not published textbook design examples. Future normative ",
        "checks need named worked-example references and separate applicability review.</p>",
        f"<p>Runtime versions: {_escape(mechanics['versions'])}</p>",
        "<label for='search'>Filter cases</label><input id='search' type='search' ",
        "placeholder='Case ID, description or method'>",
        "<p><button type='button' id='expand'>Expand all results</button></p>",
        "<section id='cases'>",
    ]
    for case in cases:
        status = case["status"]
        content.extend(
            [
                f"<details data-case='{_escape(case['id'])}'>",
                f"<summary>{_escape(case['id'])} · {_escape(case['title'])} · ",
                f"<span class='{_escape(status)}'>{_escape(status)}</span></summary>",
                f"<p>Method: {_escape(case['verification_type'])}. ",
                f"{_escape(case.get('reference', 'Execution/reference failure'))}</p>",
                "<div class='scroll'><table><thead><tr><th>Quantity</th><th>Unit</th>",
                "<th>Expected</th><th>Calculated</th><th>Difference</th><th>Abs. error</th>",
                "<th>Tolerance: abs. / rel.</th><th>Outcome</th></tr></thead><tbody>",
            ]
        )
        for check in case.get("checks", []):
            error = check.get("relative_error")
            difference = "—" if error is None else f"{100 * error:.6g}%"
            outcome = "passed" if check["passed"] else "failed"
            content.append(
                f"<tr><td>{_escape(check['metric'])}</td><td>{_escape(check['units'])}</td>"
                f"<td>{_number(check['expected'])}</td><td>{_number(check['actual'])}</td>"
                f"<td>{difference}</td><td>{_number(check.get('absolute_error'))}</td>"
                f"<td>{_number(check['absolute_tolerance'])} / "
                f"{_number(check['relative_tolerance'])}</td>"
                f"<td class='{outcome}'>{outcome}</td></tr>"
            )
        content.append("</tbody></table></div>")
        for assumption in case.get("assumption_checks", []):
            content.append(f"<p>{_escape(assumption)}</p>")
        if "error" in case:
            content.append(f"<p class='failed'>{_escape(case['error'])}</p>")
        for warning in case.get("warnings", []):
            content.append(f"<p>{_escape(warning)}</p>")
        content.append(
            "<details><summary>Inputs</summary><pre>"
            + _escape(json.dumps(case["inputs"], indent=2))
            + "</pre></details></details>"
        )
    content.extend(
        [
            "</section><h2>Upstream design adapter review</h2>",
            "<p>Adapter not enabled by this plugin. These diagnostics retain discrepancies ",
            "against reviewed references; they are not included in mechanics pass totals.</p>",
            "<div class='scroll'><table><tr><th>Diagnostic / reference</th><th>Expected</th>",
            "<th>Observed</th><th>Unit</th><th>Finding</th><th>Status</th></tr>",
        ]
    )
    for case in upstream["cases"]:
        content.append(
            f"<tr><td>{_escape(case['id'])}<br>{_escape(case['reference'])}</td>"
            f"<td>{_number(case['expected'])}</td><td>{_number(case['actual'])}</td>"
            f"<td>{_escape(case['units'])}</td><td>{_escape(case['finding'])}</td>"
            f"<td class='{_escape(case['status'])}'>{_escape(case['status'])}</td></tr>"
        )
    content.extend(
        [
            "</table></div><p>Use the accompanying JSON reports for full precision and inputs. ",
            "See docs/amendment-review.md for the amendment coverage matrix.</p></main>",
            "<script>document.querySelector('#search').addEventListener('input',event=>{",
            "const query=event.target.value.toLowerCase();",
            "document.querySelectorAll('[data-case]').forEach(item=>{",
            "item.hidden=!item.textContent.toLowerCase().includes(query);});});",
            "document.querySelector('#expand').addEventListener('click',()=>{",
            "document.querySelectorAll('#cases details').forEach(item=>item.open=true);});",
            "</script>",
            "</html>",
        ]
    )
    return "\n".join(content)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mechanics", type=Path, required=True)
    parser.add_argument("--upstream", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    mechanics = json.loads(args.mechanics.read_text(encoding="utf-8"))
    upstream = json.loads(args.upstream.read_text(encoding="utf-8"))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render_html(mechanics, upstream), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
