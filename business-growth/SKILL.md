---
name: "business-growth-skills"
description: "5 business growth agent skills and plugins for Claude Code, Codex, Gemini CLI, Cursor, OpenClaw. Customer success (health scoring, churn), sales engineer (RFP), revenue operations (pipeline, GTM), contract & proposal writer, channel partner program (IPP scoring, tiers, activation, KPIs). Python tools (stdlib-only)."
version: 1.1.0
author: Alireza Rezvani
license: MIT
tags:
  - business
  - customer-success
  - sales
  - revenue-operations
  - growth
agents:
  - claude-code
  - codex-cli
  - openclaw
---

# Business & Growth Skills

5 production-ready skills for customer success, sales, revenue operations, and channel partner programs.

## Quick Start

### Claude Code
```
/read business-growth/customer-success-manager/SKILL.md
```

### Codex CLI
```bash
npx agent-skills-cli add alirezarezvani/claude-skills/business-growth
```

## Skills Overview

| Skill | Folder | Focus |
|-------|--------|-------|
| Customer Success Manager | `customer-success-manager/` | Health scoring, churn prediction, expansion |
| Sales Engineer | `sales-engineer/` | RFP analysis, competitive matrices, PoC planning |
| Channel Partner Program | `channel-partner-program/` | Partner types, IPP scoring, channel sizing, tiers, 90-day activation, channel KPIs |
| Revenue Operations | `revenue-operations/` | Pipeline analysis, forecast accuracy, GTM metrics |
| Contract & Proposal Writer | `contract-and-proposal-writer/` | Proposal generation, contract templates |

## Python Tools

9 scripts, all stdlib-only:

```bash
python3 customer-success-manager/scripts/health_score_calculator.py --help
python3 revenue-operations/scripts/pipeline_analyzer.py --help
```

## Rules

- Load only the specific skill SKILL.md you need
- Use Python tools for scoring and metrics, not manual estimates
