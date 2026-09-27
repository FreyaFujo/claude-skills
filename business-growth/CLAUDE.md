# Business & Growth Skills - Claude Code Guidance

This guide covers the 5 production-ready business and growth skills and their Python automation tools.

## Business & Growth Skills Overview

**Available Skills:**
1. **customer-success-manager/** - Customer health scoring, churn risk analysis, expansion opportunities (3 Python tools)
2. **sales-engineer/** - Technical discovery, RFP analysis, competitive positioning, POC planning (3 Python tools)
3. **revenue-operations/** - Pipeline analysis, forecast accuracy, GTM efficiency metrics (3 Python tools)
4. **contract-and-proposal-writer/** - Contract and proposal drafting
5. **channel-partner-program/** - Partner type selection, IPP scoring, channel sizing, tiering, 90-day activation, channel KPIs (4 Python tools)

**Total Tools:** 13 Python automation tools, 12 knowledge bases, 28+ templates

## Python Automation Tools

### Customer Success Manager Tools

#### 1. Health Score Calculator (`customer-success-manager/scripts/health_score_calculator.py`)

**Purpose:** Multi-dimensional customer health scoring with trend analysis

**Features:**
- Weighted scoring across 4 dimensions (usage, engagement, support, relationship)
- Red/Yellow/Green classification with configurable thresholds
- Trend analysis comparing current vs previous period
- Segment-aware benchmarking (Enterprise/Mid-Market/SMB)

**Usage:**
```bash
python customer-success-manager/scripts/health_score_calculator.py customer_data.json
python customer-success-manager/scripts/health_score_calculator.py customer_data.json --format json
```

#### 2. Churn Risk Analyzer (`customer-success-manager/scripts/churn_risk_analyzer.py`)

**Purpose:** Identify at-risk accounts with intervention recommendations

**Features:**
- Risk scoring based on behavioral signals
- Warning signal detection and categorization
- Tier-appropriate intervention playbooks
- Urgency-based prioritization

**Usage:**
```bash
python customer-success-manager/scripts/churn_risk_analyzer.py customer_data.json
python customer-success-manager/scripts/churn_risk_analyzer.py customer_data.json --format json
```

#### 3. Expansion Opportunity Scorer (`customer-success-manager/scripts/expansion_opportunity_scorer.py`)

**Purpose:** Identify upsell and cross-sell opportunities

**Features:**
- Adoption depth analysis across product modules
- Whitespace mapping for unused features
- Revenue opportunity estimation
- Priority ranking by effort and impact

**Usage:**
```bash
python customer-success-manager/scripts/expansion_opportunity_scorer.py customer_data.json
python customer-success-manager/scripts/expansion_opportunity_scorer.py customer_data.json --format json
```

### Sales Engineer Tools

#### 4. RFP Response Analyzer (`sales-engineer/scripts/rfp_response_analyzer.py`)

**Purpose:** Score RFP/RFI coverage and identify gaps

**Features:**
- Requirement coverage scoring (Full/Partial/Planned/Gap)
- Effort estimation per requirement
- Gap identification with mitigation strategies
- Overall bid/no-bid recommendation

**Usage:**
```bash
python sales-engineer/scripts/rfp_response_analyzer.py rfp_data.json
python sales-engineer/scripts/rfp_response_analyzer.py rfp_data.json --format json
```

#### 5. Competitive Matrix Builder (`sales-engineer/scripts/competitive_matrix_builder.py`)

**Purpose:** Generate feature comparison matrices and competitive positioning

**Features:**
- Feature-by-feature comparison matrix
- Competitive scoring with weighted categories
- Differentiator identification
- Battlecard-ready output

**Usage:**
```bash
python sales-engineer/scripts/competitive_matrix_builder.py competitive_data.json
python sales-engineer/scripts/competitive_matrix_builder.py competitive_data.json --format json
```

#### 6. POC Planner (`sales-engineer/scripts/poc_planner.py`)

**Purpose:** Plan proof-of-concept engagements

**Features:**
- Timeline estimation based on scope
- Resource allocation planning
- Success criteria definition
- Evaluation scorecard generation

**Usage:**
```bash
python sales-engineer/scripts/poc_planner.py poc_data.json
python sales-engineer/scripts/poc_planner.py poc_data.json --format json
```

### Revenue Operations Tools

#### 7. Pipeline Analyzer (`revenue-operations/scripts/pipeline_analyzer.py`)

**Purpose:** Analyze sales pipeline health and velocity

**Features:**
- Coverage ratio calculation (pipeline/quota)
- Stage conversion rate analysis
- Sales velocity metrics (4-lever model)
- Deal aging analysis

**Usage:**
```bash
python revenue-operations/scripts/pipeline_analyzer.py pipeline_data.json
python revenue-operations/scripts/pipeline_analyzer.py pipeline_data.json --format json
```

#### 8. Forecast Accuracy Tracker (`revenue-operations/scripts/forecast_accuracy_tracker.py`)

**Purpose:** Measure and improve forecast accuracy

**Features:**
- MAPE (Mean Absolute Percentage Error) calculation
- Forecast bias detection (over/under-forecasting)
- Period-over-period trend analysis
- Category-level accuracy breakdown

**Usage:**
```bash
python revenue-operations/scripts/forecast_accuracy_tracker.py forecast_data.json
python revenue-operations/scripts/forecast_accuracy_tracker.py forecast_data.json --format json
```

#### 9. GTM Efficiency Calculator (`revenue-operations/scripts/gtm_efficiency_calculator.py`)

**Purpose:** Calculate go-to-market efficiency metrics

**Features:**
- Magic number calculation
- LTV:CAC ratio analysis
- CAC payback period
- Burn multiple assessment
- Industry benchmarking

**Usage:**
```bash
python revenue-operations/scripts/gtm_efficiency_calculator.py gtm_data.json
python revenue-operations/scripts/gtm_efficiency_calculator.py gtm_data.json --format json
```

### Channel Partner Program Tools

#### 10. Partner Type Advisor (`channel-partner-program/scripts/partner_type_advisor.py`)

**Purpose:** Recommend partner types, service modules and Advise/Build/Lead involvement from a diagnosed growth constraint

**Features:**
- Six constraints (pipeline volume, geographic reach, vertical penetration, deployment complexity, product stickiness, deal conversion)
- Five partner types (referral, reseller, system integrator, technology, channel) with module dependency map
- Involvement level shifted by in-house capability (none / partial / full)

**Usage:**
```bash
python channel-partner-program/scripts/partner_type_advisor.py --constraint pipeline-volume --capability partial
python channel-partner-program/scripts/partner_type_advisor.py --constraint deployment-complexity --format json
```

#### 11. IPP Scorer (`channel-partner-program/scripts/ipp_scorer.py`)

**Purpose:** Rank prospective partners against a weighted Ideal Partner Profile

**Features:**
- 12 criteria across firmographic, capability, alignment and trust-mapping pillars, weights sum to 100
- Recruit / conditional / decline thresholds (default 75 / 55), strengths and gaps per prospect
- CSV, JSON and text output; custom weights file

**Usage:**
```bash
python channel-partner-program/scripts/ipp_scorer.py prospects.csv
python channel-partner-program/scripts/ipp_scorer.py prospects.csv --weights ipp_weights.json --format csv
```

#### 12. Channel Planner (`channel-partner-program/scripts/channel_planner.py`)

**Purpose:** Pipeline math, tier assignment and 90-day activation plans

**Features:**
- `pipeline`: revenue target to deals, qualified opportunities, coverage and partner contribution
- `tiers`: Registered / Silver / Gold from revenue, certified engineers, training and agreement, with next-tier gap
- `activation`: dated Launch / Pipeline / Review plan in text, JSON or Markdown

**Usage:**
```bash
python channel-partner-program/scripts/channel_planner.py pipeline --target 5000000 --avg-deal 30000 --win-rate 0.25 --partners 5 --opps-per-partner 3
python channel-partner-program/scripts/channel_planner.py tiers partner_performance.csv --config tier_config.json
python channel-partner-program/scripts/channel_planner.py activation --partner "Acme" --start 2026-10-01 --format md
```

#### 13. Channel KPI Tracker (`channel-partner-program/scripts/kpi_tracker.py`)

**Purpose:** Score channel program health against benchmarks and flag at-risk partners

**Features:**
- Seven KPIs: sourced and influenced revenue share, pipeline coverage, enablement completion, portal engagement, time to first deal, retention
- 0-100 health score with GREEN / AMBER / RED grade; misses earn discounted credit
- At-risk partner list with reasons and next action

**Usage:**
```bash
python channel-partner-program/scripts/kpi_tracker.py partner_kpis.csv --total-revenue 4200000
python channel-partner-program/scripts/kpi_tracker.py partner_kpis.csv --total-revenue 4200000 --as-of 2026-09-30 --format json
```

## Quality Standards

**All business & growth Python tools must:**
- Use standard library only (no external dependencies)
- Support both JSON and human-readable output via `--format` flag
- Provide clear error messages for invalid input
- Return appropriate exit codes
- Process files locally (no API calls)
- Include argparse CLI with `--help` support

## Related Skills

- **Marketing:** Content creation, demand generation -> `../marketing-skill/`
- **Product Team:** User research, feature prioritization -> `../product-team/`
- **C-Level:** Strategic planning -> `../c-level-advisor/`
- **Engineering:** Technical implementation -> `../engineering-team/`

---

**Last Updated:** September 2026
**Skills Deployed:** 5/5 business & growth skills production-ready
**Total Tools:** 13 Python automation tools
