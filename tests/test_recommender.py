"""
Unit tests for Component 2: Decision Recommendation Ladder.
Verifies escalation from Send Demand -> Formal Notice -> File Samadhaan.
"""

from datetime import date, timedelta
import pytest
from pipeline.recommender import DecisionRecommender, RecommendedAction


def test_initial_case_recommends_demand():
    recommender = DecisionRecommender()
    actions = recommender.recommend(
        has_violations=True,
        contact_attempts=0,
        first_contact_date=None,
    )
    assert len(actions) == 3
    recommended = [a for a in actions if a.is_recommended]
    assert len(recommended) == 1
    assert recommended[0].action_id == "send_demand"
    assert recommended[0].escalation_order == 1


def test_contact_made_within_30_days_recommends_notice():
    recommender = DecisionRecommender()
    today = date(2026, 3, 15)
    first_contact = date(2026, 3, 1)  # 14 days ago (< 30 days)
    actions = recommender.recommend(
        has_violations=True,
        contact_attempts=1,
        first_contact_date=first_contact,
        current_date=today,
    )
    assert len(actions) == 3
    recommended = [a for a in actions if a.is_recommended]
    assert len(recommended) == 1
    assert recommended[0].action_id == "formal_notice"
    assert recommended[0].escalation_order == 2


def test_contact_made_after_30_days_recommends_samadhaan():
    recommender = DecisionRecommender()
    today = date(2026, 4, 15)
    first_contact = date(2026, 3, 1)  # 45 days ago (>= 30 days)
    actions = recommender.recommend(
        has_violations=True,
        contact_attempts=2,
        first_contact_date=first_contact,
        current_date=today,
    )
    assert len(actions) == 3
    recommended = [a for a in actions if a.is_recommended]
    assert len(recommended) == 1
    assert recommended[0].action_id == "file_samadhaan"
    assert recommended[0].escalation_order == 3
