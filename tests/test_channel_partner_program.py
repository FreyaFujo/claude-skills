"""Unit tests for the Channel Partner Program tools."""

import os
import sys
from datetime import date

import pytest

SCRIPTS = os.path.join(os.path.dirname(__file__), "..", "business-growth", "channel-partner-program", "scripts")
sys.path.insert(0, SCRIPTS)

from channel_planner import activation_plan, load_tier_config, pipeline_math, qualifies  # noqa: E402
from ipp_scorer import CRITERIA, decide, load_weights, score_prospect  # noqa: E402
from kpi_tracker import compute  # noqa: E402
from partner_type_advisor import CONSTRAINTS, PARTNER_TYPES, advise, shift_level  # noqa: E402


class TestIppScorer:
    def test_default_weights_sum_to_100(self):
        assert sum(load_weights(None).values()) == 100

    def test_custom_weights_must_sum_to_100(self, tmp_path):
        f = tmp_path / "w.json"
        f.write_text('{"company_profile": 50}')
        with pytest.raises(ValueError):
            load_weights(str(f))

    def test_perfect_prospect_scores_100(self):
        row = {"partner_name": "Perfect", **{k: 5 for k in CRITERIA}}
        assert score_prospect(row, load_weights(None))["total_score"] == 100.0

    def test_zero_prospect_scores_0_and_lists_gaps(self):
        row = {"partner_name": "Zero", **{k: 0 for k in CRITERIA}}
        r = score_prospect(row, load_weights(None))
        assert r["total_score"] == 0.0
        assert "ICP overlap" in r["gaps"]

    def test_out_of_range_rejected(self):
        row = {"partner_name": "Bad", **{k: 0 for k in CRITERIA}, "icp_overlap": 7}
        with pytest.raises(ValueError):
            score_prospect(row, load_weights(None))

    def test_decisions(self):
        assert decide(80, 75, 55)[0] == "RECRUIT"
        assert decide(60, 75, 55)[0] == "CONDITIONAL"
        assert decide(40, 75, 55)[0] == "DECLINE"


class TestChannelPlanner:
    def test_pipeline_math_rm5m_case(self):
        r = pipeline_math(5_000_000, 30_000, 0.25, 4, 12, 5, 3, None)
        assert r["requirement"]["deals_per_month"] == 13.9
        assert r["requirement"]["qualified_opps_per_month"] == 55.6
        assert r["requirement"]["active_pipeline_value"] == 1_666_667
        assert r["partner_contribution"]["partner_share_of_target_pct"] == 27.0

    def test_pipeline_math_rejects_bad_inputs(self):
        with pytest.raises(ValueError):
            pipeline_math(1, 0, 0.5, 4, 12, 0, 0, None)
        with pytest.raises(ValueError):
            pipeline_math(1, 10, 1.5, 4, 12, 0, 0, None)

    def test_tier_qualification(self):
        tiers = load_tier_config(None)
        gold = tiers[0]
        p = {"closed_revenue_12m": 600_000, "certified_engineers": 2, "training_complete": True, "agreement_signed": True}
        assert qualifies(p, gold) == []
        p["certified_engineers"] = 1
        assert any("certified engineers" in m for m in qualifies(p, gold))

    def test_activation_plan_dates(self):
        r = activation_plan("Acme", date(2026, 10, 1), "CM")
        assert r["day_90"] == "2026-12-29"
        assert r["phases"][1]["start"] == "2026-10-31"
        assert len(r["phases"]) == 3


class TestKpiTracker:
    def _partners(self):
        return [
            {"partner_name": "A", "tier": "Gold", "onboarded": date(2026, 1, 1), "first_deal": date(2026, 3, 1),
             "sourced_revenue": 300, "influenced_revenue": 50, "pipeline": 800, "quota": 200,
             "enablement_completion_pct": 90, "portal_logins_30d": 5, "active": True},
            {"partner_name": "B", "tier": "Registered", "onboarded": date(2026, 1, 1), "first_deal": None,
             "sourced_revenue": 0, "influenced_revenue": 0, "pipeline": 0, "quota": 100,
             "enablement_completion_pct": 10, "portal_logins_30d": 0, "active": True},
        ]

    def test_metrics_and_flags(self):
        r = compute(self._partners(), 1000, date(2026, 9, 30))
        assert r["metrics"]["partner_sourced_share_pct"] == 30.0
        assert r["metrics"]["time_to_first_deal_days"] == 59
        assert r["metrics"]["partner_retention_pct"] == 100.0
        flagged = {f["partner_name"] for f in r["flags"]}
        assert flagged == {"B"}
        assert any("no first deal" in x for x in r["flags"][0]["reasons"])

    def test_health_not_green_when_most_kpis_below(self):
        partners = self._partners()
        partners[0]["sourced_revenue"] = 100
        r = compute(partners, 1000, date(2026, 9, 30))
        assert r["health"]["grade"] != "GREEN"


class TestPartnerTypeAdvisor:
    def test_every_constraint_maps_to_known_types(self):
        for c in CONSTRAINTS.values():
            for t in c["primary"] + c["secondary"]:
                assert t in PARTNER_TYPES

    def test_capability_shifts_level(self):
        assert shift_level("Build", "none") == "Lead"
        assert shift_level("Build", "full") == "Advise"
        assert shift_level("Lead", "none") == "Lead"

    def test_advise_output(self):
        r = advise("deployment-complexity", "partial")
        assert r["recommendations"][0]["partner_type"] == "System Integrator"
        assert r["recommendations"][0]["priority"] == "primary"
