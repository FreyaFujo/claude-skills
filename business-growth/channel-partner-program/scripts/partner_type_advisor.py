#!/usr/bin/env python3
"""Partner Type Advisor - Recommend partner types, service modules and involvement level from a diagnosed constraint.

Implements the constraint-first rule: name the bottleneck, then pick the one or two
partner types that remove it, the service modules each type depends on, and whether
the vendor should Advise, Build or Lead each program function given its in-house capability.

Usage:
    python partner_type_advisor.py --constraint pipeline-volume
    python partner_type_advisor.py --constraint deployment-complexity --capability partial --format json
    python partner_type_advisor.py --list
"""

import argparse
import json
import sys
from typing import Any

CONSTRAINTS: dict[str, dict[str, Any]] = {
    "pipeline-volume": {
        "description": "Not enough qualified opportunities entering the funnel",
        "primary": ["Referral", "Channel"],
        "secondary": ["Reseller"],
    },
    "geographic-reach": {
        "description": "Cannot cover target regions or territories with direct sales",
        "primary": ["Reseller"],
        "secondary": ["Channel", "Referral"],
    },
    "vertical-penetration": {
        "description": "Weak presence in a priority industry vertical",
        "primary": ["Reseller", "System Integrator"],
        "secondary": ["Referral"],
    },
    "deployment-complexity": {
        "description": "Deals stall on implementation, integration or delivery capacity",
        "primary": ["System Integrator"],
        "secondary": ["Technology"],
    },
    "product-stickiness": {
        "description": "Retention or expansion is weak; product is not embedded in customer workflow",
        "primary": ["Technology"],
        "secondary": ["System Integrator"],
    },
    "deal-conversion": {
        "description": "Opportunities exist but close slowly or on discount",
        "primary": ["Referral", "System Integrator"],
        "secondary": ["Reseller"],
        "note": "Conversion is usually a positioning and enablement problem first; fix those before recruiting",
    },
}

PARTNER_TYPES: dict[str, dict[str, Any]] = {
    "Referral": {
        "role": "Warm introductions for a fee; does not sell or implement",
        "structure": "Simple sign-up, commission 5-15% of first-year value",
        "modules": {"positioning": "M", "content": "M", "demand_gen": "L", "sales_enablement": "L",
                    "partner_marketing": "H", "ai_transformation": "L"},
        "involvement": {"program_design": "Advise", "recruitment": "Build", "enablement": "Advise",
                        "management": "Advise"},
    },
    "Reseller": {
        "role": "Buys and resells; owns the sales process and customer relationship",
        "structure": "Training and certification, deal registration, 20-40% margin tiers, MDF",
        "modules": {"positioning": "H", "content": "M", "demand_gen": "M", "sales_enablement": "H",
                    "partner_marketing": "H", "ai_transformation": "M"},
        "involvement": {"program_design": "Build", "recruitment": "Lead", "enablement": "Build",
                        "management": "Build"},
    },
    "System Integrator": {
        "role": "Complex deployment, customisation and implementation",
        "structure": "Technical certification, professional services model, co-selling, implementation incentives",
        "modules": {"positioning": "M", "content": "M", "demand_gen": "L", "sales_enablement": "H",
                    "partner_marketing": "M", "ai_transformation": "H"},
        "involvement": {"program_design": "Build", "recruitment": "Build", "enablement": "Lead",
                        "management": "Build"},
    },
    "Technology": {
        "role": "Builds integrations or complementary offerings for a joint solution",
        "structure": "API agreement, co-marketing, joint solution development, marketplace listing",
        "modules": {"positioning": "H", "content": "H", "demand_gen": "M", "sales_enablement": "L",
                    "partner_marketing": "H", "ai_transformation": "M"},
        "involvement": {"program_design": "Advise", "recruitment": "Build", "enablement": "Build",
                        "management": "Advise"},
    },
    "Channel": {
        "role": "Umbrella: resellers, distributors, agents, MSPs scaling indirect distribution",
        "structure": "Multi-tier levels, volume incentives, vertical specialisation",
        "modules": {"positioning": "M", "content": "M", "demand_gen": "H", "sales_enablement": "H",
                    "partner_marketing": "H", "ai_transformation": "M"},
        "involvement": {"program_design": "Lead", "recruitment": "Lead", "enablement": "Build",
                        "management": "Lead"},
    },
}

# How much in-house capability shifts the recommended involvement level.
CAPABILITY_SHIFT = {"none": +1, "partial": 0, "full": -1}
LEVELS = ["Advise", "Build", "Lead"]


def shift_level(level: str, capability: str) -> str:
    idx = LEVELS.index(level) + CAPABILITY_SHIFT[capability]
    return LEVELS[max(0, min(len(LEVELS) - 1, idx))]


def advise(constraint: str, capability: str) -> dict[str, Any]:
    c = CONSTRAINTS[constraint]
    recs = []
    for ptype in c["primary"] + c["secondary"]:
        spec = PARTNER_TYPES[ptype]
        recs.append({
            "partner_type": ptype,
            "priority": "primary" if ptype in c["primary"] else "secondary",
            "role": spec["role"],
            "structure": spec["structure"],
            "modules_required": [m for m, lvl in spec["modules"].items() if lvl == "H"],
            "modules_secondary": [m for m, lvl in spec["modules"].items() if lvl == "M"],
            "involvement": {fn: shift_level(lvl, capability) for fn, lvl in spec["involvement"].items()},
        })
    return {
        "constraint": constraint,
        "constraint_description": c["description"],
        "in_house_capability": capability,
        "rule": "Open only the primary types first. Add secondary types once time-to-first-deal is under 90 days "
                "for the primary program.",
        "note": c.get("note"),
        "recommendations": recs,
    }


def render_text(r: dict[str, Any]) -> str:
    lines = ["PARTNER TYPE RECOMMENDATION", "=" * 72,
             f"Constraint: {r['constraint']} - {r['constraint_description']}",
             f"In-house capability: {r['in_house_capability']}", ""]
    if r.get("note"):
        lines += [f"Note: {r['note']}", ""]
    for rec in r["recommendations"]:
        lines.append(f"[{rec['priority'].upper()}] {rec['partner_type']}")
        lines.append(f"  Role:       {rec['role']}")
        lines.append(f"  Structure:  {rec['structure']}")
        lines.append(f"  Modules:    primary {', '.join(rec['modules_required'])}; "
                     f"secondary {', '.join(rec['modules_secondary']) or '-'}")
        inv = ", ".join(f"{k.replace('_', ' ')}={v}" for k, v in rec["involvement"].items())
        lines.append(f"  Involvement: {inv}")
        lines.append("")
    lines.append(f"Rule: {r['rule']}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Recommend partner types and involvement levels from a diagnosed constraint.")
    parser.add_argument("--constraint", choices=sorted(CONSTRAINTS), help="Diagnosed bottleneck")
    parser.add_argument("--capability", choices=sorted(CAPABILITY_SHIFT), default="partial",
                        help="In-house partner-management capability (default partial)")
    parser.add_argument("--list", action="store_true", help="List constraints and partner types, then exit")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    args = parser.parse_args()
    if args.list:
        listing = {"constraints": {k: v["description"] for k, v in CONSTRAINTS.items()},
                   "partner_types": {k: v["role"] for k, v in PARTNER_TYPES.items()}}
        print(json.dumps(listing, indent=2) if args.format == "json" else
              "\n".join([*(f"constraint {k}: {v}" for k, v in listing["constraints"].items()),
                         *(f"type {k}: {v}" for k, v in listing["partner_types"].items())]))
        return 0
    if not args.constraint:
        parser.error("--constraint is required unless --list is given")
    result = advise(args.constraint, args.capability)
    print(json.dumps(result, indent=2) if args.format == "json" else render_text(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
