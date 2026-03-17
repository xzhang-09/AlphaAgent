from __future__ import annotations

from itertools import product


class ValuationModel:
    def run(self, market: dict, fundamentals: dict) -> dict:
        current_price = market["current_price"]
        resolved_forward_pe = self._resolved_forward_pe(market)
        resolved_peer_pe = self._resolved_peer_pe(market, resolved_forward_pe)
        resolved_stress_pe = self._resolved_stress_pe(market, resolved_forward_pe)
        resolved_ev_ebitda = self._resolved_ev_ebitda(market)
        current_eps = current_price / resolved_forward_pe
        current_ebitda = current_price / resolved_ev_ebitda

        base_growth = fundamentals["revenue_growth_yoy"] / 100
        base_margin = fundamentals["ebit_margin"] / 100
        quality_flags = []
        if not market.get("forward_pe"):
            quality_flags.append("forward_pe_unavailable")
        if not market.get("peer_forward_pe"):
            quality_flags.append("peer_forward_pe_unavailable")
        if not market.get("ev_ebitda"):
            quality_flags.append("ev_ebitda_unavailable")

        scenario_analysis = {
            "bull": self._scenario(
                "Bull",
                current_eps,
                current_price,
                base_growth + 0.08,
                base_margin + 0.03,
                resolved_peer_pe + 2,
            ),
            "base": self._scenario(
                "Base",
                current_eps,
                current_price,
                base_growth,
                base_margin,
                resolved_peer_pe,
            ),
            "bear": self._scenario(
                "Bear",
                current_eps,
                current_price,
                max(base_growth - 0.10, 0.02),
                max(base_margin - 0.04, 0.08),
                resolved_stress_pe,
            ),
        }

        sensitivity_table = []
        growth_grid = [max(base_growth - 0.05, 0.02), base_growth, base_growth + 0.05]
        margin_grid = [max(base_margin - 0.03, 0.08), base_margin, base_margin + 0.03]
        for growth, margin in product(growth_grid, margin_grid):
            implied_eps = current_eps * (1 + growth) * (0.9 + margin)
            implied_price = implied_eps * resolved_peer_pe
            sensitivity_table.append(
                {
                    "revenue_growth_pct": round(growth * 100, 1),
                    "ebit_margin_pct": round(margin * 100, 1),
                    "target_price": round(implied_price, 2),
                }
            )

        return {
            "current_price": current_price,
            "relative_valuation": {
                "forward_pe": resolved_forward_pe,
                "peer_forward_pe": resolved_peer_pe,
                "ev_ebitda": resolved_ev_ebitda,
                "implied_ev_ebitda_price": round(current_ebitda * resolved_peer_pe, 2),
            },
            "historical_percentile": market["historical_pe_percentile"],
            "scenario_analysis": scenario_analysis,
            "sensitivity_table": sensitivity_table,
            "data_quality_flags": quality_flags,
        }

    @staticmethod
    def _scenario(
        name: str,
        current_eps: float,
        current_price: float,
        growth: float,
        margin: float,
        target_pe: float,
    ) -> dict:
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
    def _resolved_forward_pe(market: dict) -> float:
        return max(float(market.get("forward_pe") or 0.0), 15.0)

    @staticmethod
    def _resolved_peer_pe(market: dict, fallback_forward_pe: float) -> float:
        return max(float(market.get("peer_forward_pe") or 0.0), fallback_forward_pe * 1.1)

    @staticmethod
    def _resolved_stress_pe(market: dict, fallback_forward_pe: float) -> float:
        return max(float(market.get("stress_pe") or 0.0), fallback_forward_pe * 0.8)

    @staticmethod
    def _resolved_ev_ebitda(market: dict) -> float:
        return max(float(market.get("ev_ebitda") or 0.0), 10.0)
