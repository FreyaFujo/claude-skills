#!/usr/bin/env python3
"""Channel Planner - Pipeline math, tier assignment and 90-day activation plans for a channel program.

Subcommands:
    pipeline    Translate a revenue target into deals, opportunities and pipeline coverage,
                then size the partner contribution against the gap.
    tiers       Assign Registered / Silver / Gold tiers from partner performance data
                and report what each partner needs for the next tier.
    activation  Generate a dated first-90-days plan (Launch, Pipeline, Review) for a partner.

Usage:
    python channel_planner.py pipeline --target 5000000 --avg-deal 30000 --win-rate 0.25 --partners 5 --opps-per-partner 3
    python channel_planner.py tiers partner_performance.csv --config ../assets/tier_config.json
    python channel_planner.py activation --partner "Acme Networks" --start 2026-10-01 --format md
"""

import argparse
import csv
import json
import sys
from datetime import date, datetime, timedelta
from typing import Any

DEFAULT_TIERS = {
    "tiers": [
        {"name": "Gold", "margin": "30-35%", "min_revenue_12m": 500000, "min_certified_engineers": 2,
         "requires_training": True, "benefits": ["Co-selling", "MDF", "Dedicated support"]},
        {"name": "Silver", "margin": "20-25%", "min_revenue_12m": 100000, "min_certified_engineers": 1,
         "requires_training": True, "benefits": ["Shared leads", "Portal access"]},
        {"name": "Registered", "margin": "10-15%", "min_revenue_12m": 0, "min_certified_engineers": 0,
         "requires_training": False, "benefits": ["Product updates", "Training access"]},
    ]
}

ACTIVATION_PHASES = [
    {"name": "Launch", "start_day": 1, "end_day": 30, "activities": [
        "Complete partner agreement and deal-registration terms",
        "Provision partner portal access",
        "Welcome call with partner leadership and sales lead",
        "Product and positioning training (certification path started)",
        "Distribute sales kit: battlecards, playbook, collateral, price list",
    ]},
    {"name": "Pipeline", "start_day": 31, "end_day": 60, "activities": [
        "Joint business plan: targets, territories, named accounts",
        "Identify and agree top 10 target accounts",
        "Register first opportunities in deal registration",
        "Co-selling support on first two opportunities",
        "Launch first co-marketing campaign (MDF-funded where eligible)",
    ]},
    {"name": "Review", "start_day": 61, "end_day": 90, "activities": [
        "First quarterly business review (QBR)",
        "Assess enablement completion and certification status",
        "Review KPIs: registered pipeline, time to first deal, portal engagement",
        "Set next-quarter objectives and tier review date",
        "Adjust support model to observed performance",
    ]},
]


def _truthy(v: Any) -> bool:
    return str(v).strip().lower() in ("1", "true", "yes", "y")


# ---------------------------------------------------------------- pipeline
def pipeline_math(target: float, avg_deal: float, win_rate: float, coverage: float, months: int,
                  partners: int, opps_per_partner: float, partner_win_rate: float | None) -> dict[str, Any]:
    if avg_deal <= 0 or not 0 < win_rate <= 1 or months <= 0 or coverage <= 0:
        raise ValueError("avg-deal, months and coverage must be positive; win-rate must be in (0, 1]")
    pwr = partner_win_rate if partner_win_rate is not None else win_rate
    deals_total = target / avg_deal
    deals_month = deals_total / months
    opps_month = deals_month / win_rate
    pipeline_value = target / months * coverage
    partner_opps = partners * opps_per_partner
    partner_deals = partner_opps * pwr
    partner_revenue_month = partner_deals * avg_deal
    direct_opps_needed = max(0.0, opps_month - partner_opps * (pwr / win_rate))
    partners_to_cover = (opps_month / (opps_per_partner * (pwr / win_rate))) if opps_per_partner > 0 else None
    return {
        "inputs": {"target": target, "avg_deal": avg_deal, "win_rate": win_rate, "partner_win_rate": pwr,
                   "coverage": coverage, "months": months, "partners": partners,
                   "opps_per_partner_month": opps_per_partner},
        "requirement": {
            "deals_total": round(deals_total, 1),
            "deals_per_month": round(deals_month, 1),
            "qualified_opps_per_month": round(opps_month, 1),
            "active_pipeline_value": round(pipeline_value),
        },
        "partner_contribution": {
            "partner_opps_per_month": round(partner_opps, 1),
            "partner_deals_per_month": round(partner_deals, 2),
            "partner_revenue_per_month": round(partner_revenue_month),
            "partner_share_of_target_pct": round(partner_revenue_month * months / target * 100, 1),
            "direct_opps_still_needed_per_month": round(direct_opps_needed, 1),
            "partners_needed_to_cover_target": round(partners_to_cover, 1) if partners_to_cover else None,
        },
    }


def render_pipeline(r: dict[str, Any]) -> str:
    i, q, p = r["inputs"], r["requirement"], r["partner_contribution"]
    return "\n".join([
        "CHANNEL PIPELINE MATH", "=" * 60,
        f"Target {i['target']:,.0f} over {i['months']} months | avg deal {i['avg_deal']:,.0f} | "
        f"win rate {i['win_rate']:.0%} (partner {i['partner_win_rate']:.0%}) | coverage {i['coverage']}x", "",
        f"Deals required:              {q['deals_total']} total, {q['deals_per_month']} per month",
        f"Qualified opps required:     {q['qualified_opps_per_month']} per month",
        f"Active pipeline to hold:     {q['active_pipeline_value']:,.0f}", "",
        f"Partners modelled:           {i['partners']} x {i['opps_per_partner_month']} opps/month "
        f"= {p['partner_opps_per_month']} opps/month",
        f"Partner deals per month:     {p['partner_deals_per_month']}",
        f"Partner revenue per month:   {p['partner_revenue_per_month']:,.0f} "
        f"({p['partner_share_of_target_pct']}% of target)",
        f"Direct opps still needed:    {p['direct_opps_still_needed_per_month']} per month",
        f"Partners to cover 100%:      {p['partners_needed_to_cover_target']}",
    ])


# ---------------------------------------------------------------- tiers
def load_tier_config(path: str | None) -> list[dict[str, Any]]:
    cfg = DEFAULT_TIERS
    if path:
        with open(path, encoding="utf-8") as fh:
            cfg = json.load(fh)
    tiers = sorted(cfg["tiers"], key=lambda t: t["min_revenue_12m"], reverse=True)
    return tiers


def qualifies(p: dict[str, Any], tier: dict[str, Any]) -> list[str]:
    misses = []
    if p["closed_revenue_12m"] < tier["min_revenue_12m"]:
        misses.append(f"revenue {p['closed_revenue_12m']:,.0f} < {tier['min_revenue_12m']:,.0f}")
    if p["certified_engineers"] < tier["min_certified_engineers"]:
        misses.append(f"certified engineers {p['certified_engineers']} < {tier['min_certified_engineers']}")
    if tier.get("requires_training") and not p["training_complete"]:
        misses.append("training incomplete")
    if not p["agreement_signed"]:
        misses.append("agreement unsigned")
    return misses


def assign_tiers(path: str, tiers: list[dict[str, Any]]) -> dict[str, Any]:
    with open(path, encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    if not rows:
        raise ValueError("No partners in performance file")
    results = []
    for row in rows:
        p = {
            "partner_name": row.get("partner_name", "").strip(),
            "closed_revenue_12m": float(row.get("closed_revenue_12m") or 0),
            "certified_engineers": int(float(row.get("certified_engineers") or 0)),
            "training_complete": _truthy(row.get("training_complete", "")),
            "agreement_signed": _truthy(row.get("agreement_signed", "yes")),
        }
        assigned, next_gap = None, None
        for idx, tier in enumerate(tiers):
            misses = qualifies(p, tier)
            if not misses:
                assigned = tier
                if idx > 0:
                    next_gap = {"tier": tiers[idx - 1]["name"], "missing": qualifies(p, tiers[idx - 1])}
                break
        results.append({**p, "tier": assigned["name"] if assigned else "Unqualified",
                        "margin": assigned["margin"] if assigned else None,
                        "benefits": assigned["benefits"] if assigned else [],
                        "next_tier": next_gap})
    dist = {}
    for r in results:
        dist[r["tier"]] = dist.get(r["tier"], 0) + 1
    return {"summary": {"partners": len(results), "distribution": dist}, "tiers": tiers, "results": results}


def render_tiers(r: dict[str, Any]) -> str:
    lines = ["TIER ASSIGNMENT", "=" * 72,
             f"Partners: {r['summary']['partners']}   Distribution: "
             + ", ".join(f"{k} {v}" for k, v in r["summary"]["distribution"].items()), "",
             f"{'Partner':<28}{'Tier':<12}{'Margin':<9}{'Rev 12m':>12}  Next tier gap"]
    lines.append("-" * 72)
    for p in r["results"]:
        gap = "-" if not p["next_tier"] else f"{p['next_tier']['tier']}: " + "; ".join(p["next_tier"]["missing"])
        lines.append(f"{p['partner_name'][:27]:<28}{p['tier']:<12}{(p['margin'] or '-'):<9}"
                     f"{p['closed_revenue_12m']:>12,.0f}  {gap}")
    return "\n".join(lines)


# ---------------------------------------------------------------- activation
def activation_plan(partner: str, start: date, owner: str) -> dict[str, Any]:
    phases = []
    for ph in ACTIVATION_PHASES:
        phases.append({
            "phase": ph["name"],
            "days": f"{ph['start_day']}-{ph['end_day']}",
            "start": (start + timedelta(days=ph["start_day"] - 1)).isoformat(),
            "end": (start + timedelta(days=ph["end_day"] - 1)).isoformat(),
            "activities": [{"activity": a, "owner": owner, "status": "open"} for a in ph["activities"]],
        })
    return {"partner": partner, "start": start.isoformat(),
            "day_90": (start + timedelta(days=89)).isoformat(),
            "success_criteria": ["Enablement completion >= 80%", "At least one deal registered by day 60",
                                 "First closed deal by day 90", "Portal activity every week from day 30"],
            "phases": phases}


def render_activation(r: dict[str, Any], fmt: str) -> str:
    if fmt == "md":
        lines = [f"# 90-Day Activation Plan: {r['partner']}", "",
                 f"**Start:** {r['start']}  **Day 90:** {r['day_90']}", "",
                 "## Success criteria", *(f"- {c}" for c in r["success_criteria"]), ""]
        for ph in r["phases"]:
            lines += [f"## {ph['phase']} (days {ph['days']}: {ph['start']} to {ph['end']})", "",
                      "| Activity | Owner | Status |", "|---|---|---|"]
            lines += [f"| {a['activity']} | {a['owner']} | {a['status']} |" for a in ph["activities"]]
            lines.append("")
        return "\n".join(lines)
    lines = [f"90-DAY ACTIVATION PLAN: {r['partner']}", "=" * 60,
             f"Start {r['start']}  Day 90 {r['day_90']}", ""]
    for ph in r["phases"]:
        lines.append(f"{ph['phase']} (days {ph['days']}: {ph['start']} to {ph['end']})")
        lines += [f"  [ ] {a['activity']} ({a['owner']})" for a in ph["activities"]]
        lines.append("")
    lines.append("Success criteria: " + "; ".join(r["success_criteria"]))
    return "\n".join(lines)


# ---------------------------------------------------------------- cli
def main() -> int:
    parser = argparse.ArgumentParser(description="Channel program planning: pipeline math, tiers, activation plans.")
    sub = parser.add_subparsers(dest="cmd")

    pp = sub.add_parser("pipeline", help="Revenue target to opportunity and partner math")
    pp.add_argument("--target", type=float, required=True, help="Revenue target for the period")
    pp.add_argument("--avg-deal", type=float, required=True, help="Average deal size")
    pp.add_argument("--win-rate", type=float, required=True, help="Win rate as a fraction, e.g. 0.25")
    pp.add_argument("--partner-win-rate", type=float, help="Win rate on partner-sourced deals (default = win-rate)")
    pp.add_argument("--coverage", type=float, default=4.0, help="Pipeline coverage multiple (default 4)")
    pp.add_argument("--months", type=int, default=12, help="Months in the period (default 12)")
    pp.add_argument("--partners", type=int, default=0, help="Active partners modelled")
    pp.add_argument("--opps-per-partner", type=float, default=0, help="Qualified opps per partner per month")
    pp.add_argument("--format", choices=["text", "json"], default="text")

    tp = sub.add_parser("tiers", help="Assign tiers from partner performance CSV")
    tp.add_argument("input", help="CSV: partner_name, closed_revenue_12m, certified_engineers, training_complete, agreement_signed")
    tp.add_argument("--config", help="Tier config JSON (default: built-in Registered/Silver/Gold)")
    tp.add_argument("--format", choices=["text", "json"], default="text")

    ap = sub.add_parser("activation", help="Dated 90-day activation plan")
    ap.add_argument("--partner", required=True, help="Partner name")
    ap.add_argument("--start", help="Start date YYYY-MM-DD (default today)")
    ap.add_argument("--owner", default="Channel manager", help="Default activity owner")
    ap.add_argument("--format", choices=["text", "json", "md"], default="text")

    args = parser.parse_args()
    if not args.cmd:
        parser.print_help()
        return 1
    try:
        if args.cmd == "pipeline":
            r = pipeline_math(args.target, args.avg_deal, args.win_rate, args.coverage, args.months,
                              args.partners, args.opps_per_partner, args.partner_win_rate)
            print(json.dumps(r, indent=2) if args.format == "json" else render_pipeline(r))
        elif args.cmd == "tiers":
            r = assign_tiers(args.input, load_tier_config(args.config))
            print(json.dumps(r, indent=2) if args.format == "json" else render_tiers(r))
        else:
            start = datetime.strptime(args.start, "%Y-%m-%d").date() if args.start else date.today()
            r = activation_plan(args.partner, start, args.owner)
            print(json.dumps(r, indent=2) if args.format == "json" else render_activation(r, args.format))
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
