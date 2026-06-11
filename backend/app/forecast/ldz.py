"""LDZ (local distribution zone) demand baseline forecast per country.

Model (v0.1):
    gwh ~ HDD_pop + weekday + holiday + lag1 + lag7

Fit on rolling 3y per country. This module is a placeholder skeleton — the
training pipeline lands in Phase 2 once HDD ingest is wired.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass
class LDZModel:
    country: str
    coefs: dict[str, float]
    version: str = "ldz-v0.1"

    def predict(self, hdd: float, weekday: int, is_holiday: bool, lag1: float, lag7: float) -> float:
        c = self.coefs
        return (
            c.get("intercept", 0.0)
            + c.get("hdd", 0.0) * hdd
            + c.get(f"wd_{weekday}", 0.0)
            + c.get("holiday", 0.0) * (1 if is_holiday else 0)
            + c.get("lag1", 0.0) * lag1
            + c.get("lag7", 0.0) * lag7
        )


def stub_model(country: str) -> LDZModel:
    """Placeholder coefficients to allow API wiring before the real fit lands."""
    return LDZModel(
        country=country,
        coefs={
            "intercept": 800.0,
            "hdd": 45.0,
            "wd_5": -120.0,
            "wd_6": -180.0,
            "holiday": -150.0,
            "lag1": 0.3,
            "lag7": 0.4,
        },
    )
