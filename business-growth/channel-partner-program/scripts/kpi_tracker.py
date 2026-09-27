#!/usr/bin/env python3
"""Channel KPI Tracker - Score channel program health against benchmarks and flag at-risk partners.

Reads a partner KPI CSV and computes the seven channel KPIs (partner-sourced revenue share,
influenced revenue, pipeline, enablement completion, portal engagement, time to first deal,
retention), compares each to benchmark, produces a 0-100 program health score and lists
partners needing intervention.

Usage:
    python kpi_tracker.py partner_kpis.csv --total-revenue 4200000
    python kpi_tracker.py partner_kpis.csv --total-revenue 4200000 --as-of 2026-09-30 --format json
"""

import argparse
import csv
import json
import sys
from datetime import date, datetime
from typing import Any

BELOW_TARGET_FACTOR = 0.75

BENCHMARKS = {
    "partner_sourced_share_pct": {"target": 25, "weight": 25, "label": "Partner-sourced revenue share (%)"},
    "enablement_completion_pct": {"target": 80, "weight": 20, "label": "Enablement completion, active partners (%)"},
    "time_to_first_deal_days": {"target": 90, "weight": 20, "label": "Median time to first deal (days)", "lower_is_better": True},
    "partner_retention_pct": {"target": 80, "weight": 15, "label": "Partner retention (%)"},
    "portal_engaged_pct": {"target": 80, "weight": 10, "label": "Partners with portal activity in 30 days (%)"},
    "pipeline_coverage_x": {"target": 4, "weight": 10, "label": "Partner pipeline coverage of partner quota (x)"},
}


def _date(v: str) -> date | None:
    v = (v or "").strip()
    return datetime.strptime(v, "%Y-%m-%d").date() if v else None


def _truthy(v: Any) -> bool:
    return str(v).strip().lower() in ("1", "true", "yes", "y")


def load(path: str) -> list[dict[str, Any]]:
    with open(path, encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    if not rows:
        raise ValueError("No partners in KPI file")
    out = []
    for r in rows:
        out.append({
            "partner_name": r.get("partner_name", "").strip(),
            "tier": r.get("tier", "").strip(),
            "onboarded": _date(r.get("onboarded", "")),
            "first_deal": _date(r.get("first_deal", "")),
            "sourced_revenue": float(r.get("sourced_revenue") or 0),
            "influenced_revenue": float(r.get("influenced_revenue") or 0),
            "pipeline": float(r.get("pipeline") or 0),
            "quota": float(r.get("quota") or 0),
            "enablement_completion_pct": float(r.get("enablement_completion_pct") or 0),
            "portal_logins_30d": int(float(r.get("portal_logins_30d") or 0)),
            "active": _truthy(r.get("active", "yes")),
        })
    return out


def median(vals: list[float]) -> float | None:
    if not vals:
        return None
    s = sorted(vals)
    n = len(s)
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2


def compute(partners: list[dict[str, Any]], total_revenue: float, as_of: date) -> dict[str, Any]:
    active = [p for p in partners if p["active"]]
    sourced = sum(p["sourced_revenue"] for p in partners)
    influenced = sum(p["influenced_revenue"] for p in partners)
    pipeline = sum(p["pipeline"] for p in active)
    quota = sum(p["quota"] for p in active)
    ttfd = [(p["first_deal"] - p["onboarded"]).days for p in partners if p["first_deal"] and p["onboarded"]]
    metrics = {
        "partner_sourced_share_pct": round(sourced / total_revenue * 100, 1) if total_revenue else 0.0,
        "partner_influenced_share_pct": round(influenced / total_revenue * 100, 1) if total_revenue else 0.0,
        "partner_pipeline": round(pipeline),
        "pipeline_coverage_x": round(pipeline / quota, 2) if quota else None,
        "enablement_completion_pct": round(sum(p["enablement_completion_pct"] for p in active) / len(active), 1) if active else 0.0,
        "time_to_first_deal_days": median(ttfd),
        "partner_retention_pct": round(len(active) / len(partners) * 100, 1),
        "portal_engaged_pct": round(sum(1 for p in active if p["portal_logins_30d"] > 0) / len(active) * 100, 1) if active else 0.0,
        "partners_total": len(partners),
        "partners_active": len(active),
        "partners_with_first_deal": len(ttfd),
    }

    scorecard, health = [], 0.0
    for key, b in BENCHMARKS.items():
        val = metrics.get(key)
        if val is None:
            attainment = 0.0
            status = "NO DATA"
        elif b.get("lower_is_better"):
            attainment = min(1.0, b["target"] / val) if val > 0 else 1.0
            status = "ON TARGET" if val <= b["target"] else "BELOW"
        else:
            attainment = min(1.0, val / b["target"]) if b["target"] else 0.0
            status = "ON TARGET" if val >= b["target"] else "BELOW"
        # Full points only when the benchmark is met; a miss earns proportional
        # credit discounted by BELOW_TARGET_FACTOR so a program cannot grade GREEN
        # while most KPIs are below benchmark.
        if status == "BELOW":
            attainment *= BELOW_TARGET_FACTOR
        health += attainment * b["weight"]
        scorecard.append({"kpi": key, "label": b["label"], "value": val, "benchmark": b["target"],
                          "status": status, "weight": b["weight"], "points": round(attainment * b["weight"], 1)})

    flags = []
    for p in partners:
        reasons = []
        if not p["active"]:
            reasons.append("inactive")
        else:
            if p["onboarded"] and not p["first_deal"] and (as_of - p["onboarded"]).days > 90:
                reasons.append(f"no first deal after {(as_of - p['onboarded']).days} days")
            if p["enablement_completion_pct"] < 80:
                reasons.append(f"enablement {p['enablement_completion_pct']:.0f}% < 80%")
            if p["portal_logins_30d"] == 0:
                reasons.append("no portal activity in 30 days")
            if p["onboarded"] and (as_of - p["onboarded"]).days > 60 and p["pipeline"] == 0:
                reasons.append("no registered pipeline after day 60")
        if reasons:
            flags.append({"partner_name": p["partner_name"], "tier": p["tier"], "reasons": reasons,
                          "action": "Re-activation call within 5 working days; re-run 90-day plan phase Pipeline"
                          if p["active"] else "Confirm churn reason; remove from active roster"})

    grade = "GREEN" if health >= 80 else "AMBER" if health >= 60 else "RED"
    return {"as_of": as_of.isoformat(), "total_revenue": total_revenue,
            "health": {"score": round(health, 1), "grade": grade},
            "metrics": metrics, "scorecard": scorecard, "flags": flags}


def render_text(r: dict[str, Any]) -> str:
    m = r["metrics"]
    lines = ["CHANNEL PROGRAM HEALTH", "=" * 78,
             f"As of {r['as_of']}   Health {r['health']['score']}/100 ({r['health']['grade']})   "
             f"Partners {m['partners_active']}/{m['partners_total']} active, {m['partners_with_first_deal']} with a first deal", "",
             f"{'KPI':<46}{'Value':>10}{'Target':>10}  Status"]
    lines.append("-" * 78)
    for s in r["scorecard"]:
        val = "-" if s["value"] is None else s["value"]
        lines.append(f"{s['label']:<46}{str(val):>10}{str(s['benchmark']):>10}  {s['status']}")
    lines += ["", f"Partner-influenced share: {m['partner_influenced_share_pct']}%   "
                  f"Partner pipeline: {m['partner_pipeline']:,.0f}", ""]
    if r["flags"]:
        lines.append(f"AT-RISK PARTNERS ({len(r['flags'])})")
        for f in r["flags"]:
            lines.append(f"- {f['partner_name']} [{f['tier'] or '-'}]: {'; '.join(f['reasons'])}")
            lines.append(f"    Action: {f['action']}")
    else:
        lines.append("No at-risk partners.")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Score channel program KPIs against benchmarks and flag at-risk partners.")
    parser.add_argument("input", help="Partner KPI CSV (see assets/partner_kpi_template.csv)")
    parser.add_argument("--total-revenue", type=float, required=True, help="Total company revenue for the period")
    parser.add_argument("--as-of", help="Evaluation date YYYY-MM-DD (default today)")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    args = parser.parse_args()
    try:
        as_of = datetime.strptime(args.as_of, "%Y-%m-%d").date() if args.as_of else date.today()
        report = compute(load(args.input), args.total_revenue, as_of)
    except (OSError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(report, indent=2) if args.format == "json" else render_text(report))
    return 0


if __name__ == "__main__":
    sys.exit(main())
