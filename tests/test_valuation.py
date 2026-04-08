from data.fundamentals import FundamentalsAdapter
from data.market_data import MarketDataAdapter
from engine.valuation_model import ValuationModel


def test_valuation_scenarios_have_expected_shape():
    market = MarketDataAdapter().get_market_snapshot("NVDA")
    fundamentals = FundamentalsAdapter().get_fundamentals_snapshot("NVDA")
    result = ValuationModel().run(market=market, fundamentals=fundamentals)
    assert result["valuation_supported"] is True
    assert set(result["scenario_analysis"].keys()) == {"bull", "base", "bear"}
    assert "target_price" in result["scenario_analysis"]["base"]
    assert len(result["sensitivity_table"]) == 9


def test_valuation_does_not_force_targets_when_benchmark_multiples_are_missing():
    market = {
        "current_price": 300.0,
        "forward_pe": 0.0,
        "peer_forward_pe": 0.0,
        "ev_ebitda": 0.0,
        "historical_pe_percentile": 40.0,
        "stress_pe": 0.0,
    }
    fundamentals = {
        "revenue_growth_yoy": 0.0,
        "ebit_margin": 0.0,
    }
    result = ValuationModel().run(market=market, fundamentals=fundamentals)
    assert result["valuation_supported"] is False
    assert result["scenario_analysis"] == {}
    assert result["sensitivity_table"] == []
    assert result["relative_valuation"]["forward_pe"] is None
    assert result["relative_valuation"]["peer_forward_pe"] is None
    assert "forward_pe_unavailable" in result["data_quality_flags"]
    assert "peer or Damodaran benchmark P/E" in result["support_summary"]
