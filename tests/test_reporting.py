# SPDX-License-Identifier: AGPL-3.0-only
from opencalcs_as3600.reporting import render_html


def test_report_labels_blockers_and_escapes_recorded_text() -> None:
    mechanics = {
        "versions": {"python": "3.12"},
        "aggregate": {"passed": 1, "case_count": 1},
        "cases": [
            {
                "id": "fixture",
                "title": "<script>bad()</script>",
                "verification_type": "analytical",
                "status": "passed",
                "inputs": {},
                "checks": [
                    {
                        "metric": "moment",
                        "units": "kN*m",
                        "expected": 10,
                        "actual": 10,
                        "relative_error": 0,
                        "absolute_error": 0,
                        "relative_tolerance": 1e-5,
                        "absolute_tolerance": 1e-6,
                        "passed": True,
                    }
                ],
            }
        ],
    }
    upstream = {"aggregate": {"blocked": 4}, "cases": []}
    rendered = render_html(mechanics, upstream)
    assert "AS 3600 design compliance is not evaluated" in rendered
    assert "<strong>4</strong>" in rendered
    assert "&lt;script&gt;bad()&lt;/script&gt;" in rendered
    assert "<script>bad()" not in rendered
    assert "data-case='fixture'" in rendered
    assert "metamorphic" in rendered
