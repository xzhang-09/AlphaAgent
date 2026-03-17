from agents.signal_agent import SignalDetectionAgent
from data.clients import FMPAccessError, FundamentalsClient, MarketDataClient, _fmp_filings, _fmp_financials_snapshot, _fmp_get, _fmp_request
from pipelines.opportunity_pipeline import screen_opportunities
from pipelines.research_graph import run_research
from schemas.memo import AnalystFeedback
from schemas.research_state import ResearchState
from data.market_data import MarketDataAdapter
from data.fundamentals import FundamentalsAdapter


def test_base_agent_contract_populates_output_and_alias():
    market = MarketDataAdapter()
    fundamentals = FundamentalsAdapter()
    state = ResearchState(
        ticker="NVDA",
        analyst_feedback=AnalystFeedback(),
        company_profile=market.get_company_profile("NVDA"),
        market_snapshot=market.get_market_snapshot("NVDA"),
        fundamentals_snapshot=fundamentals.get_fundamentals_snapshot("NVDA"),
    )
    updated = SignalDetectionAgent().run(state)
    assert updated["signal_output"] is not None
    assert updated["signals"] is not None
    assert updated["signal_output"]["ranked_candidates"][0]["ticker"] == "NVDA"


def test_critique_loop_with_feedback_does_not_crash():
    result = run_research(
        "TSM",
        analyst_feedback={
            "bull_case": "Bull case should emphasize CoWoS bottleneck easing.",
            "bear_case": "Bear case should stress overseas fab cost inflation.",
            "catalysts": "Next earnings and packaging utilization updates.",
        },
    )
    assert result["critic_output"] is not None
    assert result["final_output"]["passed_evaluator"] is True


def test_market_client_falls_back_when_quote_summary_is_unavailable(monkeypatch):
    client = MarketDataClient()

    monkeypatch.setattr(client, "load_cached", lambda namespace, key: None)
    monkeypatch.setattr(client, "save_cached", lambda namespace, key, payload: None)

    def _raise_quote_summary(_ticker: str):
        raise RuntimeError("quote summary unavailable")

    monkeypatch.setattr("data.clients._yahoo_quote_summary", _raise_quote_summary)
    monkeypatch.setattr(
        "data.clients._yahoo_quote",
        lambda _ticker: {
            "shortName": "Apple Inc.",
            "longName": "Apple Inc.",
            "currency": "USD",
            "region": "United States",
            "regularMarketPrice": 190.0,
            "trailingPE": 28.0,
        },
    )
    monkeypatch.setattr(
        "data.clients._yahoo_chart",
        lambda _ticker: {
            "close": [180.0, 185.0, 190.0],
            "volume": [100.0, 105.0, 210.0],
        },
    )

    snapshot = client.get_snapshot("AAPL")
    profile = client.get_company_profile("AAPL")

    assert snapshot["ticker"] == "AAPL"
    assert snapshot["current_price"] == 190.0
    assert snapshot["forward_pe"] == 28.0
    assert profile["company_name"] == "Apple Inc."


def test_opportunity_screen_respects_explicit_ticker_selection():
    rows = screen_opportunities(tickers=["AAPL"])
    assert len(rows) == 1
    assert rows[0]["ticker"] == "AAPL"


def test_fundamentals_client_handles_quote_endpoint_401(monkeypatch):
    client = FundamentalsClient()

    monkeypatch.setattr(client, "load_cached", lambda namespace, key: None)
    monkeypatch.setattr(client, "save_cached", lambda namespace, key, payload: None)
    monkeypatch.setattr(
        "data.clients.MarketDataClient.get_snapshot",
        lambda self, ticker: {
            "ticker": ticker,
            "current_price": 400.0,
            "forward_pe": 21.0,
            "peer_forward_pe": 23.0,
            "ev_ebitda": 15.0,
            "historical_pe_percentile": 55.0,
            "drawdown_pct": -8.0,
            "volume_spike_ratio": 1.1,
            "stress_pe": 18.0,
            "sector_trend_summary": "Software demand remains resilient.",
            "factor_style_exposure": {"growth": "High"},
            "info": {
                "shortName": "Microsoft",
                "longName": "Microsoft Corporation",
                "currency": "USD",
                "sector": "Technology",
                "sectorDisp": "Technology",
                "industry": "Software",
                "industryDisp": "Software",
                "country": "United States",
                "region": "United States",
            },
        },
    )
    monkeypatch.setattr("data.clients._safe_yahoo_quote_summary", lambda _ticker: {})

    snapshot = client.get_financials("MSFT")

    assert snapshot["business_overview"]
    assert snapshot["source"] in {"yahoo_finance", "stubbed_live_data"}


def test_fundamentals_client_returns_none_when_fmp_has_no_rows(monkeypatch):
    client = FundamentalsClient()
    client.api_key = "configured"

    monkeypatch.setattr(
        "data.clients._fmp_financials_snapshot",
        lambda ticker, api_key: (_ for _ in ()).throw(ValueError(f"FMP returned no fundamentals rows for {ticker}")),
    )

    assert client._load_fmp_fundamentals("0700.HK") is None


def test_fmp_get_raises_access_error_on_forbidden(monkeypatch):
    class _Response:
        status_code = 403

    class _HTTPStatusError(Exception):
        def __init__(self):
            self.response = _Response()

    monkeypatch.setattr(
        "data.clients._fetch_json",
        lambda urls, params: (_ for _ in ()).throw(__import__("httpx").HTTPStatusError("forbidden", request=None, response=_Response())),
    )

    try:
        _fmp_get("/profile/MSFT", "configured")
        assert False, "Expected FMPAccessError"
    except FMPAccessError:
        assert True


def test_fmp_financials_snapshot_uses_free_plan_core_endpoints_when_enhancers_fail(monkeypatch):
    def _stub_fmp_get(path, api_key, params=None, version="v3"):
        if path == "/profile/GOOG":
            return [
                {
                    "sector": "Communication Services",
                    "industry": "Internet Content & Information",
                    "country": "United States",
                    "description": "Alphabet is a global internet platform company.",
                }
            ]
        if path == "/income-statement/GOOG":
            return [
                {
                    "revenue": 1000.0,
                    "grossProfit": 580.0,
                    "operatingIncome": 320.0,
                    "netIncome": 250.0,
                },
                {
                    "revenue": 900.0,
                    "operatingIncome": 270.0,
                },
            ]
        if path == "/cash-flow-statement/GOOG":
            return [
                {
                    "operatingCashFlow": 310.0,
                    "capitalExpenditure": -90.0,
                }
            ]
        if path in {"/key-metrics-ttm/GOOG", "/earnings-surprises/GOOG"}:
            raise FMPAccessError("plan limited")
        raise AssertionError(f"Unexpected path {path}")

    monkeypatch.setattr("data.clients._fmp_get", _stub_fmp_get)

    snapshot = _fmp_financials_snapshot("GOOG", "configured")

    assert snapshot["source"] == "financial_modeling_prep"
    assert snapshot["source_symbol"] == "GOOG"
    assert snapshot["revenue_growth_yoy"] > 0
    assert round(snapshot["gross_margin"], 2) == 58.0
    assert round(snapshot["ebit_margin"], 2) == 32.0
    assert round(snapshot["fcf_margin"], 2) == 22.0
    assert "key_metrics_ttm_unavailable" in snapshot["data_quality_flags"]
    assert "earnings_surprises_unavailable" in snapshot["data_quality_flags"]


def test_fmp_request_maps_legacy_profile_to_stable():
    url, query = _fmp_request("/profile/MSFT", "configured")

    assert url == "https://financialmodelingprep.com/stable/profile"
    assert query["symbol"] == "MSFT"
    assert query["apikey"] == "configured"


def test_fundamentals_client_refreshes_stale_no_key_cache():
    client = FundamentalsClient()
    client.api_key = "configured"

    assert client._should_refresh_cached_fundamentals(
        {
            "source": "yahoo_finance_fallback",
            "source_warning": "Financial Modeling Prep key not configured; using Yahoo live fallback.",
        }
    )


def test_fmp_filings_falls_back_to_metadata_when_text_fetch_fails(monkeypatch):
    monkeypatch.setattr(
        "data.clients._fmp_get",
        lambda path, api_key, params=None, version="v3": [
            {
                "formType": "10-K",
                "fillingDate": "2025-12-31",
                "finalLink": "https://example.com/filing",
            }
        ],
    )
    monkeypatch.setattr(
        "data.clients._fetch_text",
        lambda urls, params=None, headers=None: (_ for _ in ()).throw(RuntimeError("fetch failed")),
    )

    docs = _fmp_filings("MSFT", "configured")

    assert len(docs) == 1
    assert docs[0]["source"] == "fmp_stable"
    assert "10-K filing dated 2025-12-31" in docs[0]["snippet"]
