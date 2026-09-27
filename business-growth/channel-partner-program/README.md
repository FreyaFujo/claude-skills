# Channel Partner Program

Design, launch and run a B2B channel partner program: constraint diagnosis, partner-type selection, Ideal Partner Profile (IPP) scoring, channel sizing math, tier assignment, 90-day activation plans and KPI tracking. Standard-library Python only, no API calls.

## Tools

| Script | Purpose | Example |
|---|---|---|
| `scripts/partner_type_advisor.py` | Partner types, modules and Advise/Build/Lead level from a diagnosed constraint | `python scripts/partner_type_advisor.py --constraint pipeline-volume --capability partial` |
| `scripts/ipp_scorer.py` | Rank prospects on 12 weighted IPP criteria; recruit / conditional / decline | `python scripts/ipp_scorer.py assets/sample_prospects.csv --format csv` |
| `scripts/channel_planner.py pipeline` | Revenue target to deals, opportunities, pipeline and partner contribution | `python scripts/channel_planner.py pipeline --target 5000000 --avg-deal 30000 --win-rate 0.25 --partners 5 --opps-per-partner 3` |
| `scripts/channel_planner.py tiers` | Registered / Silver / Gold assignment with next-tier gap | `python scripts/channel_planner.py tiers assets/sample_partner_performance.csv --config assets/tier_config.json` |
| `scripts/channel_planner.py activation` | Dated 90-day Launch / Pipeline / Review plan | `python scripts/channel_planner.py activation --partner "Acme" --start 2026-10-01 --format md` |
| `scripts/kpi_tracker.py` | Seven channel KPIs vs benchmark, health grade, at-risk partners | `python scripts/kpi_tracker.py assets/sample_partner_kpis.csv --total-revenue 4200000` |

All tools support `--format json` and exit 1 with a message on bad input.

## Workflow

1. Diagnose the constraint and choose partner types.
2. Score prospects against the IPP (`assets/prospects_template.csv`, `assets/ipp_weights.json`).
3. Size the channel against the revenue target.
4. Write the value proposition, set three tiers (`assets/tier_config.json`), generate a 90-day plan per partner.
5. Track KPIs weekly and re-activate flagged partners.

See `SKILL.md` for the full phase-by-phase method and `references/` for the source framework (Partner2B operating model, partner types and IPP, channel sales blueprint).
