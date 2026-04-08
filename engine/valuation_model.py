from __future__ import annotations

from itertools import product
from typing import Any


class ValuationModel:
    def run(self, market: dict, fundamentals: dict) -> dict:
        current_price = float(market.get("current_price") or 0.0)
        forward_pe = self._positive_float(market.get("forward_pe"))
        peer_forward_pe = self._positive_float(market.get("peer_forward_pe"))
        ev_ebitda = self._positive_float(market.get("ev_ebitda"))
        stress_pe = self._resolved_stress_pe(market, forward_pe, peer_forward_pe)
        historical_percentile = self._positive_float(market.get("historical_pe_percentile"))

        quality_flags: list[str] = []
        if forward_pe is None:
            quality_flags.append("forward_pe_unavailable")
        if peer_forward_pe is None:
            quality_flags.append("peer_forward_pe_unavailable")
        if ev_ebitda is None:
            quality_flags.append("ev_ebitda_unavailable")

        valuation_supported = forward_pe is not None and peer_forward_pe is not None and current_price > 0
        support_summary = self._support_summary(
            forward_pe=forward_pe,
            peer_forward_pe=peer_forward_pe,
            current_price=current_price,
        )

        relative_valuation = {
            "forward_pe": forward_pe,
            "peer_forward_pe": peer_forward_pe,
            "ev_ebitda": ev_ebitda,
            "implied_ev_ebitda_price": self._implied_ev_ebitda_price(
                current_price=current_price,
                ev_ebitda=ev_ebitda,
                peer_forward_pe=peer_forward_pe,
            ),
        }

        if not valuation_supported:
            return {
                "current_price": current_price,
                "relative_valuation": relative_valuation,
                "historical_percentile": historical_percentile,
                "scenario_analysis": {},
                "sensitivity_table": [],
                "data_quality_flags": quality_flags,
                "valuation_supported": False,
                "support_summary": support_summary,
            }

        current_eps = current_price / float(forward_pe)
        base_growth = float(fundamentals.get("revenue_growth_yoy") or 0.0) / 100
        base_margin = float(fundamentals.get("ebit_margin") or 0.0) / 100

        scenario_analysis = {
            "bull": self._scenario(
                "Bull",
                current_eps=current_eps,
                current_price=current_price,
                growth=base_growth + 0.08,
                margin=base_margin + 0.03,
                target_pe=float(peer_forward_pe) + 2.0,
            ),
            "base": self._scenario(
                "Base",
                current_eps=current_eps,
                current_price=current_price,
                growth=base_growth,
                margin=base_margin,
                target_pe=float(peer_forward_pe),
            ),
            "bear": self._scenario(
                "Bear",
                current_eps=current_eps,
                current_price=current_price,
                growth=max(base_growth - 0.10, 0.02),
                margin=max(base_margin - 0.04, 0.08),
                target_pe=float(stress_pe),
            ),
        }

        sensitivity_table = []
        growth_grid = [max(base_growth - 0.05, 0.02), base_growth, base_growth + 0.05]
        margin_grid = [max(base_margin - 0.03, 0.08), base_margin, base_margin + 0.03]
        for growth, margin in product(growth_grid, margin_grid):
            implied_eps = current_eps * (1 + growth) * (0.9 + margin)
            implied_price = implied_eps * float(peer_forward_pe)
            sensitivity_table.append(
                {
                    "revenue_growth_pct": round(growth * 100, 1),
                    "ebit_margin_pct": round(margin * 100, 1),
                    "target_price": round(implied_price, 2),
                }
            )

        return {
            "current_price": current_price,
            "relative_valuation": relative_valuation,
            "historical_percentile": historical_percentile,
            "scenario_analysis": scenario_analysis,
            "sensitivity_table": sensitivity_table,
            "data_quality_flags": quality_flags,
            "valuation_supported": True,
            "support_summary": support_summary,
        }

    @staticmethod
    def _scenario(
        name: str,
        *,
        current_eps: float,
        current_price: float,
        growth: float,
        margin: float,
        target_pe: float,
    ) -> dict[str, Any]:
        scenario_eps = current_eps * (1 + growth) * (0.9 + margin)
        target_price = scenario_eps * target_pe
        upside_pct = ((target_price / current_price) - 1) * 100
        thesis = (
            f"{name} case assumes revenue growth of {growth * 100:.1f}% and EBIT margin of {margin * 100:.1f}%"
            f" with {target_pe:.1f}x forward P/E."
        )
        return {
            "revenue_growth_pct": round(growth * 100, 1),
            "ebit_margin_pct": round(margin * 100, 1),
            "target_pe": round(target_pe, 1),
            "target_price": round(target_price, 2),
            "upside_pct": round(upside_pct, 1),
            "thesis": thesis,
        }

    @staticmethod
    def _support_summary(
        *,
        forward_pe: float | None,
        peer_forward_pe: float | None,
        current_price: float,
    ) -> str:
        missing = []
        if current_price <= 0:
            missing.append("live price")
        if forward_pe is None:
            missing.append("current forward P/E")
        if peer_forward_pe is None:
            missing.append("peer or Damodaran benchmark P/E")
        if not missing:
            return "Valuation scenario analysis is supported by current and benchmark multiples."
        return (
            "Valuation scenario analysis was not generated because "
            + ", ".join(missing)
            + " was unavailable."
        )

    @staticmethod
    def _implied_ev_ebitda_price(
        *,
        current_price: float,
        ev_ebitda: float | None,
        peer_forward_pe: float | None,
    ) -> float | None:
        if current_price <= 0 or ev_ebitda is None or peer_forward_pe is None:
            return None
        current_ebitda = current_price / ev_ebitda
        return round(current_ebitda * peer_forward_pe, 2)

    @staticmethod
    def _resolved_stress_pe(
        market: dict,
        forward_pe: float | None,
        peer_forward_pe: float | None,
    ) -> float:
        raw_stress = ValuationModel._positive_float(market.get("stress_pe"))
        if raw_stress is not None:
            return raw_stress
        anchors = [value for value in (forward_pe, peer_forward_pe) if value is not None]
        if not anchors:
            return 0.0
        anchor = min(anchors)
        return round(anchor * 0.8, 2)

    @staticmethod
    def _positive_float(value: Any) -> float | None:
        if value is None:
            return None
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return None
        return numeric if numeric > 0 else None
