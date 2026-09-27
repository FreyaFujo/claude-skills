#!/usr/bin/env python3
"""IPP Scorer - Rank prospective channel partners against a weighted Ideal Partner Profile.

Scores each prospect on 12 criteria (0-5) across four pillars (firmographic,
capability, strategic alignment, ICP trust mapping), applies configurable weights
that sum to 100, and returns a recruit / conditional / decline decision per prospect
with strengths, gaps and the recommended entry tier.

Usage:
    python ipp_scorer.py prospects.csv
    python ipp_scorer.py prospects.csv --format json
    python ipp_scorer.py prospects.csv --weights custom_weights.json --recruit 75 --conditional 55
    python ipp_scorer.py prospects.csv --format csv > ranked.csv
"""

import argparse
import csv
import json
import sys
from typing import Any

# Criterion key -> (pillar, label, default weight). Weights sum to 100.
CRITERIA: dict[str, tuple[str, str, int]] = {
    "company_profile": ("Firmographic", "Company profile and financial stability", 8),
    "geographic_reach": ("Firmographic", "Geographic reach in target territories", 7),
    "industry_specialisation": ("Firmographic", "Industry specialisation in priority verticals", 7),
    "customer_base": ("Capability", "Existing customer base quality", 10),
    "sales_technical_expertise": ("Capability", "Sales and technical expertise", 12),
    "marketing_sophistication": ("Capability", "Marketing sophistication", 6),
    "icp_overlap": ("Alignment", "ICP overlap", 12),
    "solution_complementarity": ("Alignment", "Solution complementarity", 8),
    "gtm_culture_match": ("Alignment", "GTM and culture match", 8),
    "workflow_adjacency": ("Trust map", "Workflow adjacency", 6),
    "buying_context": ("Trust map", "Buying context", 6),
    "trusted_advisor": ("Trust map", "Trusted advisor status", 10),
}

MAX_RAW = 5


def load_weights(path: str | None) -> dict[str, int]:
    weights = {k: v[2] for k, v in CRITERIA.items()}
    if path:
        with open(path, encoding="utf-8") as fh:
            custom = json.load(fh)
        unknown = set(custom) - set(CRITERIA)
        if unknown:
            raise ValueError(f"Unknown criteria in weights file: {sorted(unknown)}")
        weights.update({k: int(v) for k, v in custom.items()})
    total = sum(weights.values())
    if total != 100:
        raise ValueError(f"Weights must sum to 100, got {total}")
    return weights


def load_prospects(path: str) -> list[dict[str, Any]]:
    if path.endswith(".json"):
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, list) else data.get("prospects", [])
    with open(path, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def score_prospect(row: dict[str, Any], weights: dict[str, int]) -> dict[str, Any]:
    name = (row.get("partner_name") or row.get("name") or "").strip()
    if not name:
        raise ValueError("Each prospect needs a partner_name")
    pillar_scores: dict[str, float] = {}
    pillar_max: dict[str, float] = {}
    criteria_out = []
    total = 0.0
    for key, (pillar, label, _) in CRITERIA.items():
        raw_val = row.get(key, "")
        try:
            raw = float(raw_val) if raw_val not in ("", None) else 0.0
        except (TypeError, ValueError):
            raise ValueError(f"{name}: criterion '{key}' must be numeric 0-5, got {raw_val!r}")
        if not 0 <= raw <= MAX_RAW:
            raise ValueError(f"{name}: criterion '{key}' must be between 0 and 5, got {raw}")
        weighted = raw / MAX_RAW * weights[key]
        total += weighted
        pillar_scores[pillar] = pillar_scores.get(pillar, 0.0) + weighted
        pillar_max[pillar] = pillar_max.get(pillar, 0.0) + weights[key]
        criteria_out.append({"criterion": key, "label": label, "pillar": pillar,
                             "raw": raw, "weight": weights[key], "weighted": round(weighted, 1)})
    pillars = {p: {"score": round(s, 1), "max": pillar_max[p], "pct": round(s / pillar_max[p] * 100)}
               for p, s in pillar_scores.items()}
    strengths = [c["label"] for c in criteria_out if c["raw"] >= 4]
    gaps = [c["label"] for c in criteria_out if c["raw"] <= 2 and c["weight"] >= 8]
    return {
        "partner_name": name,
        "partner_type": (row.get("partner_type") or "").strip(),
        "region": (row.get("region") or "").strip(),
        "total_score": round(total, 1),
        "pillars": pillars,
        "criteria": criteria_out,
        "strengths": strengths,
        "gaps": gaps,
    }


def decide(score: float, recruit: float, conditional: float) -> tuple[str, str]:
    if score >= recruit:
        return "RECRUIT", "Gold-track: recruit now, target Silver entry with Gold review at 90 days"
    if score >= conditional:
        return "CONDITIONAL", "Recruit with conditions: Registered tier, pilot period, close named gaps"
    return "DECLINE", "Decline or park: revisit in 2 quarters if gaps change"


def rank(prospects: list[dict[str, Any]], weights: dict[str, int],
         recruit: float, conditional: float) -> dict[str, Any]:
    results = []
    for row in prospects:
        r = score_prospect(row, weights)
        r["decision"], r["recommendation"] = decide(r["total_score"], recruit, conditional)
        results.append(r)
    results.sort(key=lambda r: r["total_score"], reverse=True)
    for i, r in enumerate(results, 1):
        r["rank"] = i
    counts = {d: sum(1 for r in results if r["decision"] == d) for d in ("RECRUIT", "CONDITIONAL", "DECLINE")}
    return {
        "summary": {
            "prospects_scored": len(results),
            "thresholds": {"recruit": recruit, "conditional": conditional},
            "decisions": counts,
            "average_score": round(sum(r["total_score"] for r in results) / len(results), 1) if results else 0,
        },
        "weights": weights,
        "results": results,
    }


def render_text(report: dict[str, Any]) -> str:
    s = report["summary"]
    lines = ["IPP SCORECARD RESULTS", "=" * 72,
             f"Prospects scored: {s['prospects_scored']}   Average: {s['average_score']}   "
             f"Recruit >= {s['thresholds']['recruit']}   Conditional >= {s['thresholds']['conditional']}",
             f"Decisions: RECRUIT {s['decisions']['RECRUIT']} | CONDITIONAL {s['decisions']['CONDITIONAL']} | "
             f"DECLINE {s['decisions']['DECLINE']}", ""]
    lines.append(f"{'#':>2}  {'Partner':<28}{'Type':<14}{'Score':>6}  Decision")
    lines.append("-" * 72)
    for r in report["results"]:
        lines.append(f"{r['rank']:>2}  {r['partner_name'][:27]:<28}{r['partner_type'][:13]:<14}"
                     f"{r['total_score']:>6}  {r['decision']}")
    lines.append("")
    for r in report["results"]:
        lines.append(f"{r['rank']}. {r['partner_name']} ({r['total_score']}/100) - {r['decision']}")
        lines.append(f"   {r['recommendation']}")
        pil = ", ".join(f"{p} {v['pct']}%" for p, v in r["pillars"].items())
        lines.append(f"   Pillars: {pil}")
        if r["strengths"]:
            lines.append(f"   Strengths: {'; '.join(r['strengths'])}")
        if r["gaps"]:
            lines.append(f"   Gaps to close: {'; '.join(r['gaps'])}")
        lines.append("")
    return "\n".join(lines)


def render_csv(report: dict[str, Any]) -> str:
    out = []
    header = ["rank", "partner_name", "partner_type", "region", "total_score", "decision"] + list(CRITERIA)
    out.append(",".join(header))
    for r in report["results"]:
        raw = {c["criterion"]: c["raw"] for c in r["criteria"]}
        row = [str(r["rank"]), f'"{r["partner_name"]}"', r["partner_type"], r["region"],
               str(r["total_score"]), r["decision"]] + [str(int(raw[k])) for k in CRITERIA]
        out.append(",".join(row))
    return "\n".join(out)


def main() -> int:
    parser = argparse.ArgumentParser(description="Score and rank prospective partners against a weighted IPP.")
    parser.add_argument("input", help="Prospects file (.csv or .json) with partner_name and 12 criteria columns")
    parser.add_argument("--weights", help="JSON file overriding criterion weights (must sum to 100)")
    parser.add_argument("--recruit", type=float, default=75, help="Recruit threshold (default 75)")
    parser.add_argument("--conditional", type=float, default=55, help="Conditional threshold (default 55)")
    parser.add_argument("--format", choices=["text", "json", "csv"], default="text")
    args = parser.parse_args()
    try:
        weights = load_weights(args.weights)
        prospects = load_prospects(args.input)
        if not prospects:
            raise ValueError("No prospects found in input")
        report = rank(prospects, weights, args.recruit, args.conditional)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    if args.format == "json":
        print(json.dumps(report, indent=2))
    elif args.format == "csv":
        print(render_csv(report))
    else:
        print(render_text(report))
    return 0


if __name__ == "__main__":
    sys.exit(main())
