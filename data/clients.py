from __future__ import annotations

import hashlib
import json
import re
import time
from datetime import date, timedelta
from functools import lru_cache
from html import unescape
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus
from xml.etree import ElementTree

import httpx

from config.settings import get_settings


class FMPAccessError(RuntimeError):
    """Raised when Financial Modeling Prep rejects the configured API key."""


class BaseAPIClient:
    """Shared client skeleton with simple file cache and retry hooks."""

    def __init__(
        self,
        *,
        api_key_env: str,
        base_url_env: str | None = None,
        cache_dir: str | None = None,
        max_retries: int = 2,
        retry_backoff: float = 0.25,
    ) -> None:
        settings = get_settings()
        env_values = {
            "GEMINI_API_KEY": settings.gemini_api_key or "",
            "GEMINI_BASE_URL": settings.gemini_base_url or "",
            "FMP_API_KEY": settings.fmp_api_key or "",
            "FRED_API_KEY": settings.fred_api_key or "",
            "EDGAR_USER_AGENT": settings.edgar_user_agent or "",
            "NEWS_API_KEY": settings.news_api_key or "",
            "FILINGS_API_KEY": settings.filings_api_key or "",
            "TRANSCRIPT_API_KEY": settings.transcript_api_key or "",
            "MARKET_DATA_API_KEY": settings.market_data_api_key or "",
        }
        self.api_key = env_values.get(api_key_env, "")
        self.base_url = env_values.get(base_url_env, "") if base_url_env else ""
        self.cache_dir = Path(cache_dir or settings.cache_dir)
        self.enable_response_cache = settings.enable_response_cache
        if self.enable_response_cache:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.max_retries = max_retries
        self.retry_backoff = retry_backoff

    def load_cached(self, namespace: str, key: str) -> Any | None:
        if not self.enable_response_cache:
            return None
        path = self._cache_path(namespace, key)
        if not path.exists():
            return None
        return json.loads(path.read_text())

    def save_cached(self, namespace: str, key: str, payload: Any) -> None:
        if not self.enable_response_cache:
            return
        path = self._cache_path(namespace, key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2))

    def with_retry(self, operation_name: str, fn) -> Any:
        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                return fn()
            except Exception as exc:  # pragma: no cover
                last_error = exc
                if attempt >= self.max_retries:
                    break
                time.sleep(self.retry_backoff * (attempt + 1))
        if last_error is None:  # pragma: no cover
            raise RuntimeError(f"{operation_name} failed without exception details")
        raise RuntimeError(f"{operation_name} failed after retries: {last_error}") from last_error

    def _cache_path(self, namespace: str, key: str) -> Path:
        digest = hashlib.md5(key.encode("utf-8")).hexdigest()
        return self.cache_dir / namespace / f"{digest}.json"


class MarketDataClient(BaseAPIClient):
    def __init__(self) -> None:
        super().__init__(api_key_env="MARKET_DATA_API_KEY")

    def get_snapshot(self, ticker: str) -> dict[str, Any]:
        cached = self.load_cached("market", ticker.upper())
        if cached and not self._should_refresh_cached_market(cached):
            return cached

        def _fetch() -> dict[str, Any]:
            quote = _safe_yahoo_quote(ticker)
            info = _safe_yahoo_quote_summary(ticker)
            chart = _safe_yahoo_chart(ticker)
            if self._needs_yfinance_fallback(quote=quote, info=info, chart=chart):
                quote, info, chart = _yfinance_market_bundle(ticker)
            closes = [float(value) for value in chart["close"] if value is not None]
            volumes = [float(value) for value in chart["volume"] if value is not None]
            chart_meta = chart.get("meta") or {}
            if not closes and _as_float(chart_meta.get("regularMarketPrice")) is None:
                raise ValueError(f"No market history returned for {ticker}")

            summary_profile = info.get("summaryProfile") or {}
            financial_data = info.get("financialData") or {}
            default_stats = info.get("defaultKeyStatistics") or {}
            flat_info = _flatten_live_info(
                ticker=ticker,
                quote={**chart_meta, **quote},
                summary_profile=summary_profile,
                financial_data=financial_data,
                default_stats=default_stats,
            )
            current_price = (
                _as_float(quote.get("regularMarketPrice"))
                or _as_float(chart_meta.get("regularMarketPrice"))
                or (float(closes[-1]) if closes else 0.0)
            )
            rolling_high = float(max(closes)) if closes else current_price
            drawdown_pct = ((current_price / rolling_high) - 1.0) * 100 if rolling_high else 0.0
            avg_volume = (
                sum(volumes[:-1]) / len(volumes[:-1])
                if len(volumes) > 1
                else float(volumes[-1] if volumes else 0.0)
            )
            volume_spike_ratio = (float(volumes[-1]) / avg_volume) if avg_volume else 1.0
            price_percentile = float(sum(1 for value in closes if value <= current_price) / len(closes) * 100)
            forward_pe = (
                _as_float(quote.get("forwardPE"))
                or _as_float(default_stats.get("forwardPE"))
                or _as_float(chart_meta.get("trailingPE"))
                or _as_float(quote.get("trailingPE"))
                or 0.0
            )
            ev_ebitda = _as_float(default_stats.get("enterpriseToEbitda")) or 0.0
            payload = {
                "ticker": ticker.upper(),
                "current_price": current_price,
                "forward_pe": forward_pe,
                "peer_forward_pe": forward_pe * 1.1 if forward_pe else 0.0,
                "ev_ebitda": ev_ebitda,
                "historical_pe_percentile": price_percentile,
                "drawdown_pct": drawdown_pct,
                "volume_spike_ratio": volume_spike_ratio,
                "stress_pe": forward_pe * 0.8 if forward_pe else 0.0,
                "sector_trend_summary": _sector_summary(flat_info),
                "factor_style_exposure": _factor_exposure(flat_info, drawdown_pct),
                "info": flat_info,
            }
            return payload
        try:
            payload = self.with_retry("market_snapshot", _fetch)
            self.save_cached("market", ticker.upper(), payload)
            return payload
        except Exception:
            if cached:
                return cached
            raise

    @staticmethod
    def _needs_yfinance_fallback(
        *,
        quote: dict[str, Any],
        info: dict[str, Any],
        chart: dict[str, Any],
    ) -> bool:
        summary_profile = info.get("summaryProfile") or {}
        financial_data = info.get("financialData") or {}
        default_stats = info.get("defaultKeyStatistics") or {}
        chart_meta = chart.get("meta") or {}
        has_price = _as_float(quote.get("regularMarketPrice")) is not None or _as_float(chart_meta.get("regularMarketPrice")) is not None
        has_profile = bool(summary_profile.get("sector") or quote.get("sector") or quote.get("industry"))
        has_multiple = any(
            _as_float(item) is not None and float(_as_float(item) or 0.0) > 0
            for item in (
                quote.get("forwardPE"),
                quote.get("trailingPE"),
                default_stats.get("forwardPE"),
                default_stats.get("enterpriseToEbitda"),
            )
        )
        has_growth = _as_float(financial_data.get("revenueGrowth")) is not None
        return not (has_price and (has_profile or has_multiple or has_growth))

    @staticmethod
    def _should_refresh_cached_market(cached: dict[str, Any]) -> bool:
        info = cached.get("info") or {}
        bad_profile = not any(
            [
                info.get("sector") not in {None, "", "Unknown"},
                info.get("industry") not in {None, "", "Unknown"},
                info.get("country") not in {None, "", "Unknown"},
            ]
        )
        bad_multiples = not any(
            float(cached.get(field) or 0.0) > 0
            for field in ("forward_pe", "peer_forward_pe", "ev_ebitda")
        )
        bad_factors = float(info.get("revenueGrowth") or 0.0) == 0.0 and float(info.get("returnOnEquity") or 0.0) == 0.0
        return bad_profile and bad_multiples and bad_factors

    def get_company_profile(self, ticker: str) -> dict[str, Any]:
        snapshot = self.get_snapshot(ticker)
        info = snapshot.get("info", {})
        return {
            "ticker": ticker.upper(),
            "company_name": info.get("shortName") or info.get("longName") or ticker.upper(),
            "sector": info.get("sector") or "Unknown",
            "region": info.get("country") or info.get("region") or "Unknown",
            "currency": info.get("currency") or "USD",
            "catalysts": _default_catalysts(info),
        }

    def get_quote_value(self, symbol: str) -> float:
        quote = _yahoo_quote(symbol)
        price = _as_float(quote.get("regularMarketPrice"))
        if price is None:
            raise ValueError(f"No live price returned for symbol {symbol}")
        return price


class MacroDataClient(BaseAPIClient):
    def __init__(self) -> None:
        super().__init__(api_key_env="FRED_API_KEY")
        settings = get_settings()
        self.edgar_user_agent = settings.edgar_user_agent or "AlphaAgent contact@example.com"

    def get_macro_snapshot(self, profile: dict[str, Any], ticker: str) -> dict[str, Any]:
        cache_key = f"{ticker.upper()}::{profile.get('currency', 'USD')}::{profile.get('region', 'Unknown')}"
        cached = self.load_cached("macro", cache_key)
        if cached and not self._should_refresh_cached_macro(cached):
            return cached

        snapshot = _build_macro_snapshot(
            profile=profile,
            fred_api_key=self.api_key,
        )
        self.save_cached("macro", cache_key, snapshot)
        return snapshot

    def _should_refresh_cached_macro(self, cached: dict[str, Any]) -> bool:
        if not self.api_key:
            return False
        flags = set(cached.get("data_quality_flags", []))
        return bool(
            {
                "fred_rates_unavailable",
                "fred_inflation_unavailable",
                "fred_credit_unavailable",
            }
            & flags
        )


class FundamentalsClient(BaseAPIClient):
    def __init__(self) -> None:
        super().__init__(api_key_env="FMP_API_KEY")

    def get_financials(self, ticker: str) -> dict[str, Any]:
        cached = self.load_cached("fundamentals", ticker.upper())
        if cached and not self._should_refresh_cached_fundamentals(cached):
            return cached

        def _fetch() -> dict[str, Any]:
            fmp_payload = self._load_fmp_fundamentals(ticker)
            if fmp_payload is not None:
                return fmp_payload
            sec_payload = _sec_fundamentals_snapshot(
                ticker=ticker,
                user_agent=get_settings().edgar_user_agent or "AlphaAgent contact@example.com",
            )
            if sec_payload is not None:
                return sec_payload

            market_snapshot = MarketDataClient().get_snapshot(ticker)
            quote = market_snapshot.get("info", {})
            info = _safe_yahoo_quote_summary(ticker)
            financial_data = info.get("financialData") or {}
            summary_profile = info.get("summaryProfile") or {}
            default_stats = info.get("defaultKeyStatistics") or {}
            revenue_growth_raw = _as_float(financial_data.get("revenueGrowth"))
            gross_margin_raw = _as_float(financial_data.get("grossMargins"))
            ebit_margin_raw = _as_float(financial_data.get("operatingMargins"))
            fcf_value_raw = _as_float(financial_data.get("freeCashflow"))
            ocf_value_raw = _as_float(financial_data.get("operatingCashflow"))
            revenue_growth_yoy = (revenue_growth_raw or 0.0) * 100
            gross_margin = (gross_margin_raw or 0.0) * 100
            ebit_margin = (ebit_margin_raw or 0.0) * 100
            fcf_value = fcf_value_raw or 0.0
            ocf_value = ocf_value_raw or 0.0
            flat_info = _flatten_live_info(
                ticker=ticker,
                quote=quote,
                summary_profile=summary_profile,
                financial_data=financial_data,
                default_stats=default_stats,
            )
            cash_flow_commentary = _cash_flow_commentary(fcf_value, ocf_value)
            if not fcf_value and not ocf_value:
                cash_flow_commentary = "Live source did not expose cash flow ratios directly; treat cash flow quality as incomplete."
            return {
                "business_overview": summary_profile.get("longBusinessSummary")
                or f"{ticker.upper()} operates in {summary_profile.get('sector') or 'its sector'}, but the live profile summary was limited.",
                "revenue_growth_yoy": revenue_growth_yoy,
                "prior_revenue_growth_yoy": revenue_growth_yoy,
                "gross_margin": gross_margin,
                "ebit_margin": ebit_margin,
                "prior_ebit_margin": ebit_margin,
                "fcf_margin": 0.0,
                "cash_conversion": 0.0,
                "cash_flow_commentary": cash_flow_commentary,
                "earnings_surprise_pct": 0.0,
                "management_change": "",
                "regulatory_event": "",
                "key_business_drivers": _business_drivers(flat_info),
                "risk_factors": _risk_factors(flat_info),
                "source": "yahoo_finance_fallback",
                "source_detail": "Yahoo fallback because neither FMP nor SEC EDGAR fundamentals were available for this run.",
                "source_warning": (
                    "Financial Modeling Prep and SEC EDGAR fundamentals were unavailable or incomplete; using weaker Yahoo live fallback."
                    if self.api_key
                    else "Financial Modeling Prep key not configured and SEC EDGAR fallback was incomplete; using Yahoo live fallback."
                ),
                "data_quality_flags": [
                    flag
                    for flag, is_missing in {
                        "revenue_growth_unavailable": revenue_growth_raw is None,
                        "gross_margin_unavailable": gross_margin_raw is None,
                        "ebit_margin_unavailable": ebit_margin_raw is None,
                        "fcf_margin_unavailable": fcf_value_raw is None,
                        "cash_conversion_unavailable": ocf_value_raw is None,
                    }.items()
                    if is_missing
                ],
            }

        try:
            payload = self.with_retry("fundamentals_snapshot", _fetch)
            self.save_cached("fundamentals", ticker.upper(), payload)
            return payload
        except Exception:
            if cached:
                return cached
            raise

    def _should_refresh_cached_fundamentals(self, cached: dict[str, Any]) -> bool:
        warning = str(cached.get("source_warning") or "")
        return bool(self.api_key) and "key not configured" in warning.lower()

    def _load_fmp_fundamentals(self, ticker: str) -> dict[str, Any] | None:
        if not self.api_key:
            return None
        try:
            return _fmp_financials_snapshot(ticker, self.api_key)
        except (FMPAccessError, ValueError):
            return None


class NewsClient(BaseAPIClient):
    def __init__(self) -> None:
        super().__init__(api_key_env="NEWS_API_KEY")

    def get_news(self, ticker: str) -> list[dict[str, Any]]:
        cached = self.load_cached("news", ticker.upper())
        if cached:
            return cached

        payload = self.search_news(query=f"{ticker.upper()} stock", namespace=ticker.upper())
        self.save_cached("news", ticker.upper(), payload)
        return payload

    def search_news(self, query: str, namespace: str) -> list[dict[str, Any]]:
        if self.api_key:
            articles = _newsapi_search(query, self.api_key)
        else:
            articles = _google_news_rss(query)
        return [
            {
                "id": f"{namespace}-news-{index}",
                "title": article["title"],
                "snippet": article["snippet"],
                "url": article.get("url", ""),
                "published_at": article.get("published_at", ""),
            }
            for index, article in enumerate(articles[:5], start=1)
        ]


class FilingsClient(BaseAPIClient):
    def __init__(self) -> None:
        super().__init__(api_key_env="FILINGS_API_KEY")

    def get_filings(self, ticker: str) -> list[dict[str, Any]]:
        cached = self.load_cached("filings", ticker.upper())
        if cached:
            return cached

        api_key = self.api_key or get_settings().fmp_api_key or ""
        docs = _fmp_filings(ticker, api_key) if api_key else []
        if not docs:
            docs = _sec_filings(ticker)
        self.save_cached("filings", ticker.upper(), docs)
        return docs


class TranscriptClient(BaseAPIClient):
    def __init__(self) -> None:
        super().__init__(api_key_env="TRANSCRIPT_API_KEY")

    def get_transcripts(self, ticker: str) -> list[dict[str, Any]]:
        cached = self.load_cached("transcripts", ticker.upper())
        if cached:
            return cached

        api_key = self.api_key or get_settings().fmp_api_key or ""
        docs = _fmp_transcripts(ticker, api_key) if api_key else []
        self.save_cached("transcripts", ticker.upper(), docs)
        return docs

def _fmp_financials_snapshot(ticker: str, api_key: str) -> dict[str, Any]:
    last_access_error: FMPAccessError | None = None
    for candidate in _fmp_symbol_candidates(ticker):
        try:
            profile_rows = _fmp_get(f"/profile/{candidate}", api_key)
            income_rows = _fmp_get(f"/income-statement/{candidate}", api_key, {"limit": 4})
        except FMPAccessError as exc:
            last_access_error = exc
            break
        except Exception:
            continue

        cash_flow_rows = _fmp_optional_get(
            f"/cash-flow-statement/{candidate}",
            api_key,
            {"limit": 4},
        )
        key_metric_rows = _fmp_optional_get(f"/key-metrics-ttm/{candidate}", api_key)
        earnings_rows = _fmp_optional_get(
            f"/earnings-surprises/{candidate}",
            api_key,
            {"limit": 4},
        )

        profile = profile_rows[0] if profile_rows else {}
        current_income = income_rows[0] if income_rows else {}
        prior_income = income_rows[1] if len(income_rows) > 1 else {}
        current_cash = cash_flow_rows[0] if cash_flow_rows else {}
        metrics = key_metric_rows[0] if key_metric_rows else {}
        earnings = earnings_rows[0] if earnings_rows else {}

        current_revenue = _as_float(current_income.get("revenue")) or 0.0
        prior_revenue = _as_float(prior_income.get("revenue")) or 0.0
        current_operating_income = _as_float(current_income.get("operatingIncome")) or 0.0
        prior_operating_income = _as_float(prior_income.get("operatingIncome")) or 0.0
        current_ebit_margin = (_as_float(current_income.get("operatingIncomeRatio")) or 0.0) * 100
        if not current_ebit_margin:
            current_ebit_margin = _ratio(current_operating_income, current_revenue)
        prior_ebit_margin = (_as_float(prior_income.get("operatingIncomeRatio")) or 0.0) * 100
        if not prior_ebit_margin:
            prior_ebit_margin = _ratio(prior_operating_income, prior_revenue)
        gross_margin = (_as_float(current_income.get("grossProfitRatio")) or 0.0) * 100
        if not gross_margin:
            gross_margin = _ratio(
                _as_float(current_income.get("grossProfit")) or 0.0,
                current_revenue,
            )
        free_cash_flow = _as_float(current_cash.get("freeCashFlow")) or 0.0
        operating_cash_flow = _as_float(current_cash.get("operatingCashFlow")) or 0.0
        net_income = _as_float(current_cash.get("netIncome")) or _as_float(current_income.get("netIncome")) or 0.0
        capital_expenditure = _as_float(current_cash.get("capitalExpenditure")) or 0.0

        if not free_cash_flow and operating_cash_flow:
            free_cash_flow = operating_cash_flow + capital_expenditure

        revenue_growth = _growth(current_revenue, prior_revenue)
        fcf_margin = _ratio(free_cash_flow, current_revenue)
        cash_conversion = _ratio(operating_cash_flow, net_income)

        flat_info = {
            "sector": profile.get("sector") or "Unknown",
            "sectorDisp": profile.get("sector") or "Unknown",
            "industry": profile.get("industry") or "Unknown",
            "industryDisp": profile.get("industry") or "Unknown",
            "country": profile.get("country") or "Unknown",
        }
        return {
            "business_overview": profile.get("description")
            or f"{ticker.upper()} operates in {profile.get('sector') or 'its sector'} with limited profile detail from FMP.",
            "revenue_growth_yoy": revenue_growth,
            "prior_revenue_growth_yoy": revenue_growth,
            "gross_margin": gross_margin,
            "ebit_margin": current_ebit_margin,
            "prior_ebit_margin": prior_ebit_margin or current_ebit_margin,
            "fcf_margin": fcf_margin,
            "cash_conversion": cash_conversion,
            "cash_flow_commentary": _cash_flow_commentary(fcf_margin, cash_conversion),
            "earnings_surprise_pct": _as_float(earnings.get("earningsSurprise")) or 0.0,
            "management_change": "",
            "regulatory_event": "",
            "key_business_drivers": _business_drivers(flat_info),
            "risk_factors": _risk_factors(flat_info),
            "source": "financial_modeling_prep",
            "source_symbol": candidate,
            "source_detail": (
                "Core profile and statement fields came from FMP free-compatible endpoints."
                if cash_flow_rows
                else "Core profile and income statement fields came from FMP free-compatible endpoints."
            ),
            "source_warning": (
                "Some premium FMP enhancer endpoints were unavailable, so advanced metrics may be partial."
                if not key_metric_rows or not earnings_rows
                else ""
            ),
            "data_quality_flags": [
                flag
                for flag, is_missing in {
                    "cash_flow_statement_unavailable": not cash_flow_rows,
                    "key_metrics_ttm_unavailable": not key_metric_rows,
                    "earnings_surprises_unavailable": not earnings_rows,
                }.items()
                if is_missing
            ],
        }
    if last_access_error:
        raise last_access_error
    raise ValueError(f"FMP returned no fundamentals rows for {ticker}")


def _row_series(frame, candidates: list[str]):
    if frame is None or getattr(frame, "empty", True):
        return None
    for candidate in candidates:
        if candidate in frame.index:
            return frame.loc[candidate]
    return None


def _series_value(series, idx: int, default: float = 0.0) -> float:
    if series is None:
        return float(default)
    values = [value for value in series.tolist() if value is not None]
    if not values or idx >= len(values):
        return float(default)
    return float(values[idx] or default)


def _growth(current: float, prior: float) -> float:
    if not prior:
        return 0.0
    return ((current / prior) - 1.0) * 100


def _ratio(numerator: float, denominator: float) -> float:
    if not denominator:
        return 0.0
    return (numerator / denominator) * 100


def _sector_summary(info: dict[str, Any]) -> str:
    sector = info.get("sectorDisp") or info.get("sector") or "the sector"
    industry = info.get("industryDisp") or info.get("industry") or "core industry"
    return f"{sector} remains the primary backdrop, with investors focused on demand durability in {industry}."


def _factor_exposure(info: dict[str, Any], drawdown_pct: float) -> dict[str, str]:
    beta = float(info.get("beta") or 1.0)
    return {
        "growth": "High" if float(info.get("revenueGrowth") or 0.0) > 0.1 else "Moderate",
        "quality": "High" if float(info.get("returnOnEquity") or 0.0) > 0.15 else "Moderate",
        "momentum": "Weak" if drawdown_pct < -15 else "Moderate",
        "beta": "High" if beta > 1.2 else "Moderate",
    }


def _default_catalysts(info: dict[str, Any]) -> list[str]:
    return [
        f"Next earnings event for {info.get('shortName') or 'the company'}",
        "Forward guidance revision",
        "Margin and cash flow trajectory",
    ]


def _business_drivers(info: dict[str, Any]) -> list[str]:
    sector = info.get("sectorDisp") or info.get("sector") or "core end markets"
    industry = info.get("industryDisp") or info.get("industry") or "operating execution"
    return [
        f"Demand trends across {sector}",
        f"Competitive position within {industry}",
        "Management execution versus guidance",
    ]


def _risk_factors(info: dict[str, Any]) -> dict[str, str]:
    sector = info.get("sectorDisp") or info.get("sector") or "the sector"
    country = info.get("country") or "key markets"
    return {
        "competition": f"Competitive intensity in {sector} could pressure pricing or market share.",
        "regulation": f"Regulatory and policy developments in {country} may affect sentiment and operations.",
        "execution": "Execution risk remains tied to guidance delivery, costs, and capital allocation.",
    }


def _cash_flow_commentary(fcf_margin: float, cash_conversion: float) -> str:
    if not fcf_margin and not cash_conversion:
        return "Live source did not expose enough cash flow detail to score quality confidently."
    if fcf_margin > 15 and cash_conversion > 90:
        return "Cash generation looks healthy relative to revenue and earnings."
    if fcf_margin > 5:
        return "Cash generation is positive but still sensitive to working capital or capex timing."
    return "Cash generation appears constrained and deserves closer monitoring."


def _fetch_text(urls: list[str], params: dict[str, Any] | None = None, headers: dict[str, str] | None = None) -> str:
    request_headers = {"User-Agent": "Mozilla/5.0 AlphaAgent"}
    if headers:
        request_headers.update(headers)
    last_error: Exception | None = None
    for url in urls:
        try:
            with httpx.Client(timeout=20.0, follow_redirects=True, headers=request_headers) as client:
                response = client.get(url, params=params)
                response.raise_for_status()
                return response.text
        except Exception as exc:
            last_error = exc
            continue
    if last_error is None:  # pragma: no cover
        raise RuntimeError("No text endpoints were provided")
    raise last_error


def _fetch_json(
    urls: list[str],
    params: dict[str, Any],
    headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    request_headers = {"User-Agent": "Mozilla/5.0 AlphaAgent"}
    if headers:
        request_headers.update(headers)
    last_error: Exception | None = None
    for url in urls:
        try:
            with httpx.Client(timeout=15.0, follow_redirects=True, headers=request_headers) as client:
                response = client.get(url, params=params)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as exc:
            last_error = exc
            status_code = exc.response.status_code
            symbol = params.get("symbols") or params.get("symbol")
            if status_code == 404 and symbol:
                raise ValueError(
                    f"Ticker '{symbol}' is not recognized by the live Yahoo Finance endpoint. "
                    "Please confirm the symbol and exchange suffix, for example AAPL, 0700.HK, or 005930.KS."
                ) from exc
        except Exception as exc:
            last_error = exc
            continue
    if last_error is None:  # pragma: no cover
        raise RuntimeError("No Yahoo Finance endpoint URLs were provided")
    raise last_error


def _safe_yahoo_quote_summary(ticker: str) -> dict[str, Any]:
    try:
        return _yahoo_quote_summary(ticker)
    except Exception:
        return {}


def _safe_yahoo_quote(ticker: str) -> dict[str, Any]:
    try:
        return _yahoo_quote(ticker)
    except Exception:
        return {}


def _safe_yahoo_chart(ticker: str) -> dict[str, Any]:
    try:
        return _yahoo_chart(ticker)
    except Exception:
        return {"close": [], "volume": [], "meta": {}}


def _newsapi_search(query: str, api_key: str) -> list[dict[str, str]]:
    payload = _fetch_json(
        ["https://newsapi.org/v2/everything"],
        {
            "q": query,
            "language": "en",
            "sortBy": "publishedAt",
            "pageSize": 5,
            "apiKey": api_key,
        },
    )
    articles = payload.get("articles") or []
    return [
        {
            "title": article.get("title") or "Untitled article",
            "snippet": article.get("description") or article.get("content") or "",
            "url": article.get("url") or "",
            "published_at": article.get("publishedAt") or "",
        }
        for article in articles
        if article.get("title")
    ]


def _google_news_rss(query: str) -> list[dict[str, str]]:
    xml_text = _fetch_text(
        [f"https://news.google.com/rss/search?q={quote_plus(query)}&hl=en-US&gl=US&ceid=US:en"]
    )
    root = ElementTree.fromstring(xml_text)
    docs = []
    for item in root.findall(".//item")[:5]:
        title = (item.findtext("title") or "").strip()
        description = _strip_html(item.findtext("description") or "")
        docs.append(
            {
                "title": title,
                "snippet": description or title,
                "url": (item.findtext("link") or "").strip(),
                "published_at": (item.findtext("pubDate") or "").strip(),
            }
        )
    return docs


def _fmp_get(path: str, api_key: str, params: dict[str, Any] | None = None, version: str = "v3") -> list[dict[str, Any]]:
    url, query = _fmp_request(path, api_key, params=params, version=version)
    try:
        payload = _fetch_json([url], query)
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code in {401, 403}:
            raise FMPAccessError("Financial Modeling Prep rejected the configured API key or plan access.") from exc
        raise
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        if isinstance(payload.get("data"), list):
            return payload["data"]
        if isinstance(payload.get("results"), list):
            return payload["results"]
    return []


def _fmp_try_get(paths: list[tuple[str, str]], api_key: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    for path, version in paths:
        try:
            rows = _fmp_get(path, api_key, params=params, version=version)
            if rows:
                return rows
        except FMPAccessError:
            raise
        except Exception:
            continue
    return []


def _fmp_optional_get(
    path: str,
    api_key: str,
    params: dict[str, Any] | None = None,
    version: str = "v3",
) -> list[dict[str, Any]]:
    try:
        return _fmp_get(path, api_key, params=params, version=version)
    except Exception:
        return []


def _fmp_request(path: str, api_key: str, params: dict[str, Any] | None = None, version: str = "v3") -> tuple[str, dict[str, Any]]:
    query = dict(params or {})
    query["apikey"] = api_key
    stable_mapping = _stable_fmp_mapping(path, query)
    if stable_mapping is not None:
        stable_path, stable_query = stable_mapping
        return f"https://financialmodelingprep.com/stable/{stable_path}", stable_query
    if version == "stable":
        return f"https://financialmodelingprep.com/stable/{path.lstrip('/')}", query
    return f"https://financialmodelingprep.com/api/{version}{path}", query


def _stable_fmp_mapping(path: str, query: dict[str, Any]) -> tuple[str, dict[str, Any]] | None:
    cloned = dict(query)
    if path.startswith("/profile/"):
        cloned["symbol"] = path.rsplit("/", 1)[-1]
        return "profile", cloned
    if path.startswith("/income-statement/"):
        cloned["symbol"] = path.rsplit("/", 1)[-1]
        return "income-statement", cloned
    if path.startswith("/cash-flow-statement/"):
        cloned["symbol"] = path.rsplit("/", 1)[-1]
        return "cash-flow-statement", cloned
    if path.startswith("/key-metrics-ttm/"):
        cloned["symbol"] = path.rsplit("/", 1)[-1]
        return "key-metrics-ttm", cloned
    if path.startswith("/earnings-surprises/"):
        symbol = path.rsplit("/", 1)[-1]
        year = cloned.pop("year", None) or date.today().year
        cloned["year"] = year
        cloned["symbol"] = symbol
        return "earnings", cloned
    if path.startswith("/sec_filings/"):
        cloned["symbol"] = path.rsplit("/", 1)[-1]
        cloned.pop("type", None)
        cloned.setdefault("page", 0)
        cloned.setdefault("limit", 20)
        cloned.setdefault("from", (date.today() - timedelta(days=365 * 3)).isoformat())
        cloned.setdefault("to", date.today().isoformat())
        return "sec-filings-search/symbol", cloned
    if path == "/earning_call_transcript":
        return "earning-call-transcript", cloned
    if path == "/earning_call_transcript_dates":
        return "earning-call-transcript-dates", cloned
    if path.startswith("/earning_call_transcript/"):
        cloned["symbol"] = path.rsplit("/", 1)[-1]
        return "earning-call-transcript", cloned
    if path.startswith("/batch_earning_call_transcript/"):
        cloned["symbol"] = path.rsplit("/", 1)[-1]
        return "earning-call-transcript", cloned
    return None


def _fmp_symbol_candidates(ticker: str) -> list[str]:
    normalized = ticker.upper()
    aliases = [normalized]
    alias_map = {
        "GOOG": ["GOOGL"],
        "GOOGL": ["GOOG"],
        "BRK.B": ["BRK-B"],
        "BRK-B": ["BRK.B"],
        "BF.B": ["BF-B"],
        "BF-B": ["BF.B"],
    }
    for alias in alias_map.get(normalized, []):
        if alias not in aliases:
            aliases.append(alias)
    return aliases


def _fmp_transcripts(ticker: str, api_key: str) -> list[dict[str, Any]]:
    date_rows = _fmp_optional_get(
        "/earning_call_transcript_dates",
        api_key,
        {"symbol": ticker},
        version="stable",
    )
    rows: list[dict[str, Any]] = []
    for row in date_rows[:3]:
        year = row.get("year")
        quarter = row.get("quarter")
        if year is None or quarter is None:
            continue
        transcript_rows = _fmp_optional_get(
            "/earning_call_transcript",
            api_key,
            {"symbol": ticker, "year": year, "quarter": quarter},
            version="stable",
        )
        rows.extend(transcript_rows[:1])
    docs = []
    for index, row in enumerate(rows[:3], start=1):
        content = row.get("content") or row.get("transcript") or row.get("text") or ""
        title = row.get("title") or row.get("date") or f"{ticker.upper()} earnings transcript"
        if not content:
            continue
        docs.append(
            {
                "id": f"{ticker.upper()}-transcript-{index}",
                "title": title,
                "snippet": _compact_text(content, max_chars=1400),
                "date": row.get("date") or "",
            }
        )
    return docs


def _fmp_filings(ticker: str, api_key: str) -> list[dict[str, Any]]:
    rows = _fmp_get(f"/sec_filings/{ticker}", api_key, params={"type": "10-K", "page": 0})
    docs = []
    for row in rows[:10]:
        filing_type = row.get("formType") or row.get("type") or ""
        if filing_type and filing_type not in {"10-K", "10-Q", "20-F", "6-K"}:
            continue
        filing_url = row.get("finalLink") or row.get("link") or row.get("filingUrl") or ""
        if not filing_url:
            continue
        filing_date = row.get("fillingDate") or row.get("date") or row.get("acceptedDate") or ""
        try:
            filing_text = _fetch_text([filing_url])
        except Exception:
            filing_text = ""
        snippet = _compact_text(_strip_html(filing_text), max_chars=1600)
        if not snippet:
            snippet = _metadata_filing_snippet(
                ticker=ticker,
                filing_type=filing_type or "Filing",
                filing_date=filing_date,
                filing_url=filing_url,
            )
        docs.append(
            {
                "id": f"{ticker.upper()}-filing-{len(docs) + 1}",
                "title": f"{filing_type or 'Filing'} {filing_date}".strip(),
                "snippet": snippet,
                "url": filing_url,
                "source": "fmp_stable",
            }
        )
        if len(docs) >= 2:
            break
    return docs


def _fmp_stock_peers(ticker: str, api_key: str) -> list[str]:
    rows = _fmp_optional_get("/stock_peers", api_key, {"symbol": ticker})
    for row in rows[:1]:
        peers = row.get("peersList") or row.get("peers") or row.get("symbols") or []
        if isinstance(peers, str):
            peers = [item.strip() for item in peers.split(",")]
        return [str(item).upper() for item in peers if str(item).strip()]
    return []


@lru_cache(maxsize=1)
def _sec_company_map() -> dict[str, str]:
    payload = _sec_json("https://www.sec.gov/files/company_tickers.json")
    mapping = {}
    for row in payload.values():
        ticker = str(row.get("ticker") or "").upper()
        cik = str(row.get("cik_str") or "").zfill(10)
        if ticker and cik:
            mapping[ticker] = cik
    return mapping


def _sec_filings(ticker: str, user_agent: str | None = None) -> list[dict[str, Any]]:
    cik = _sec_company_map().get(ticker.upper())
    if not cik:
        return []
    headers = _sec_headers(user_agent)
    submissions = _sec_json(f"https://data.sec.gov/submissions/CIK{cik}.json", user_agent=user_agent)
    recent = ((submissions.get("filings") or {}).get("recent")) or {}
    forms = recent.get("form") or []
    accessions = recent.get("accessionNumber") or []
    primary_docs = recent.get("primaryDocument") or []
    dates = recent.get("filingDate") or []
    docs = []
    for form, accession, primary_doc, filing_date in zip(forms, accessions, primary_docs, dates):
        if form not in {"10-K", "10-Q", "20-F", "6-K"}:
            continue
        accession_compact = str(accession).replace("-", "")
        filing_url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession_compact}/{primary_doc}"
        try:
            filing_text = _fetch_text([filing_url], headers=headers)
        except Exception:
            filing_text = ""
        snippet = _filing_snippet_from_text(filing_text, max_chars=1600)
        if not snippet:
            snippet = _metadata_filing_snippet(
                ticker=ticker,
                filing_type=form,
                filing_date=filing_date,
                filing_url=filing_url,
            )
        docs.append(
            {
                "id": f"{ticker.upper()}-sec-{form}-{filing_date}",
                "title": f"{form} filed {filing_date}",
                "snippet": snippet,
                "url": filing_url,
                "source": "sec_fallback",
            }
        )
        if len(docs) >= 2:
            break
    return docs


def _sec_fundamentals_snapshot(ticker: str, user_agent: str) -> dict[str, Any] | None:
    cik = _sec_company_map().get(ticker.upper())
    if not cik:
        return None

    try:
        facts_payload = _sec_json(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json", user_agent=user_agent)
    except Exception:
        return None

    facts = ((facts_payload.get("facts") or {}).get("us-gaap")) or {}
    revenue_points = _sec_fact_points(facts, ["RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues", "SalesRevenueNet"])
    gross_profit_points = _sec_fact_points(facts, ["GrossProfit"])
    operating_income_points = _sec_fact_points(facts, ["OperatingIncomeLoss"])
    operating_cash_flow_points = _sec_fact_points(
        facts,
        ["NetCashProvidedByUsedInOperatingActivities", "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations"],
    )
    capex_points = _sec_fact_points(
        facts,
        ["PaymentsToAcquirePropertyPlantAndEquipment", "CapitalExpendituresIncurredButNotYetPaid"],
    )

    latest_revenue = _sec_latest_value(revenue_points)
    prior_revenue = _sec_prior_value(revenue_points)
    latest_gross_profit = _sec_latest_value(gross_profit_points)
    latest_operating_income = _sec_latest_value(operating_income_points)
    prior_operating_income = _sec_prior_value(operating_income_points)
    latest_operating_cash_flow = _sec_latest_value(operating_cash_flow_points)
    latest_capex = _sec_latest_value(capex_points)

    if latest_revenue is None and latest_operating_income is None:
        return None

    yahoo_summary = _safe_yahoo_quote_summary(ticker)
    summary_profile = yahoo_summary.get("summaryProfile") or {}
    financial_data = yahoo_summary.get("financialData") or {}
    default_stats = yahoo_summary.get("defaultKeyStatistics") or {}
    quote = _safe_yahoo_quote(ticker)
    flat_info = _flatten_live_info(
        ticker=ticker,
        quote=quote,
        summary_profile=summary_profile,
        financial_data=financial_data,
        default_stats=default_stats,
    )

    revenue_growth_yoy = _growth(latest_revenue or 0.0, prior_revenue or 0.0)
    gross_margin = _ratio(latest_gross_profit or 0.0, latest_revenue or 0.0)
    ebit_margin = _ratio(latest_operating_income or 0.0, latest_revenue or 0.0)
    prior_ebit_margin = _ratio(prior_operating_income or 0.0, prior_revenue or 0.0) or ebit_margin
    fcf_margin = _ratio(
        (latest_operating_cash_flow or 0.0) - abs(latest_capex or 0.0),
        latest_revenue or 0.0,
    )
    cash_conversion = _ratio(latest_operating_cash_flow or 0.0, latest_operating_income or 0.0)

    return {
        "business_overview": summary_profile.get("longBusinessSummary")
        or f"{ticker.upper()} operates in {flat_info.get('industryDisp') or 'its sector'}, based on SEC-reported fundamentals.",
        "revenue_growth_yoy": revenue_growth_yoy,
        "prior_revenue_growth_yoy": revenue_growth_yoy,
        "gross_margin": gross_margin,
        "ebit_margin": ebit_margin,
        "prior_ebit_margin": prior_ebit_margin,
        "fcf_margin": fcf_margin,
        "cash_conversion": cash_conversion,
        "cash_flow_commentary": _cash_flow_commentary(fcf_margin, cash_conversion),
        "earnings_surprise_pct": 0.0,
        "management_change": "",
        "regulatory_event": "",
        "key_business_drivers": _business_drivers(flat_info),
        "risk_factors": _risk_factors(flat_info),
        "source": "sec_edgar_fallback",
        "source_detail": "Core financial statement fields came from SEC EDGAR company facts.",
        "source_warning": "Consensus and some enhancer metrics remain unavailable without FMP.",
        "data_quality_flags": [
            flag
            for flag, is_missing in {
                "revenue_growth_unavailable": latest_revenue is None or prior_revenue is None,
                "gross_margin_unavailable": latest_gross_profit is None or latest_revenue is None,
                "ebit_margin_unavailable": latest_operating_income is None or latest_revenue is None,
                "fcf_margin_unavailable": latest_operating_cash_flow is None or latest_revenue is None,
                "cash_conversion_unavailable": latest_operating_cash_flow is None or latest_operating_income is None,
            }.items()
            if is_missing
        ],
    }


def _sec_headers(user_agent: str | None = None) -> dict[str, str]:
    resolved = (user_agent or get_settings().edgar_user_agent or "AlphaAgent research assistant support@example.com").strip()
    return {
        "User-Agent": resolved,
        "Accept-Encoding": "gzip, deflate",
    }


def _sec_json(url: str, user_agent: str | None = None) -> dict[str, Any]:
    return _fetch_json([url], {}, headers=_sec_headers(user_agent))


def _sec_fact_points(facts: dict[str, Any], concept_names: list[str]) -> list[dict[str, Any]]:
    points: list[dict[str, Any]] = []
    for concept in concept_names:
        units = ((facts.get(concept) or {}).get("units")) or {}
        for unit_name in ("USD", "USDm", "shares"):
            points.extend(units.get(unit_name) or [])
    return _sec_ranked_points(points)


def _sec_ranked_points(points: list[dict[str, Any]]) -> list[dict[str, Any]]:
    filtered = [
        point for point in points
        if point.get("val") is not None
        and point.get("fy") is not None
        and not str(point.get("frame") or "").startswith("CY")
    ]
    return sorted(
        filtered,
        key=lambda point: (
            int(point.get("fy") or 0),
            str(point.get("fp") or ""),
            str(point.get("end") or ""),
        ),
        reverse=True,
    )


def _sec_latest_value(points: list[dict[str, Any]]) -> float | None:
    for point in points:
        value = _as_float(point.get("val"))
        if value is not None:
            return value
    return None


def _sec_prior_value(points: list[dict[str, Any]]) -> float | None:
    if len(points) < 2:
        return None
    for point in points[1:]:
        value = _as_float(point.get("val"))
        if value is not None:
            return value
    return None


def _strip_html(text: str) -> str:
    no_script = re.sub(r"<(script|style).*?>.*?</\\1>", " ", text, flags=re.IGNORECASE | re.DOTALL)
    no_tags = re.sub(r"<[^>]+>", " ", no_script)
    clean = re.sub(r"\s+", " ", unescape(no_tags)).strip()
    return clean


def _compact_text(text: str, max_chars: int = 1200) -> str:
    return re.sub(r"\s+", " ", text).strip()[:max_chars]


def _filing_snippet_from_text(text: str, max_chars: int = 1200) -> str:
    cleaned = _strip_html(text)
    if not cleaned:
        return ""

    cleaned = re.sub(r"https?://\S+", " ", cleaned)
    cleaned = re.sub(r"\b(?:us-gaap|dei|srt|xbrli|iso4217|country|[a-z]{2,10}):[A-Za-z0-9_]+\b", " ", cleaned)
    cleaned = re.sub(r"\b\d{6,}\b", " ", cleaned)
    cleaned = re.sub(r"\b(?:19|20)\d{2}(?:-\d{2}-\d{2})?\b", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    if _looks_like_noisy_filing_text(cleaned):
        return ""

    sentences = re.split(r"(?<=[.!?])\s+", cleaned)
    selected: list[str] = []
    for sentence in sentences:
        candidate = sentence.strip()
        if len(candidate) < 40:
            continue
        if _looks_like_noisy_filing_text(candidate):
            continue
        selected.append(candidate)
        if len(" ".join(selected)) >= max_chars:
            break

    return _compact_text(" ".join(selected) or cleaned, max_chars=max_chars)


def _looks_like_noisy_filing_text(text: str) -> bool:
    if not text:
        return True
    lowered = text.lower()
    url_count = lowered.count("http")
    colon_count = text.count(":")
    digit_count = sum(char.isdigit() for char in text)
    alpha_count = sum(char.isalpha() for char in text)
    tokens = text.split()
    long_symbol_tokens = sum(
        1
        for token in tokens
        if any(marker in token.lower() for marker in ("us-gaap", "http", ".xsd", ".xml", "linkbase", "schema", "member"))
        or re.match(r"^[a-z]{2,10}:[A-Za-z0-9_]+$", token.lower())
    )
    if alpha_count == 0:
        return True
    if url_count >= 3:
        return True
    if long_symbol_tokens >= 3:
        return True
    if colon_count > max(len(tokens) // 3, 6):
        return True
    if digit_count > alpha_count * 1.2:
        return True
    return False


def _metadata_filing_snippet(
    *,
    ticker: str,
    filing_type: str,
    filing_date: str,
    filing_url: str,
) -> str:
    return _compact_text(
        f"{ticker.upper()} {filing_type} filing dated {filing_date or 'recent period'} is available at {filing_url}. "
        "Use the filing URL for primary disclosure review when a full text excerpt was not retrievable from the current source.",
        max_chars=500,
    )


def _flatten_live_info(
    *,
    ticker: str,
    quote: dict[str, Any],
    summary_profile: dict[str, Any],
    financial_data: dict[str, Any],
    default_stats: dict[str, Any],
) -> dict[str, Any]:
    return {
        "ticker": ticker.upper(),
        "shortName": quote.get("shortName") or quote.get("longName") or ticker.upper(),
        "longName": quote.get("longName") or quote.get("shortName") or ticker.upper(),
        "currency": quote.get("currency") or "USD",
        "sector": summary_profile.get("sector") or quote.get("sector") or "Unknown",
        "sectorDisp": summary_profile.get("sector") or quote.get("sector") or "Unknown",
        "industry": summary_profile.get("industry") or quote.get("industry") or "Unknown",
        "industryDisp": summary_profile.get("industry") or quote.get("industry") or "Unknown",
        "country": summary_profile.get("country") or quote.get("region") or "Unknown",
        "region": quote.get("region") or summary_profile.get("country") or "Unknown",
        "beta": _as_float(default_stats.get("beta")) or _as_float(quote.get("beta")) or 1.0,
        "revenueGrowth": _as_float(financial_data.get("revenueGrowth")) or 0.0,
        "returnOnEquity": _as_float(financial_data.get("returnOnEquity")) or 0.0,
    }


def _yahoo_quote(ticker: str) -> dict[str, Any]:
    urls = [
        "https://query1.finance.yahoo.com/v7/finance/quote",
        "https://query2.finance.yahoo.com/v7/finance/quote",
    ]
    payload = _fetch_json(urls, {"symbols": ticker})
    result = (((payload.get("quoteResponse") or {}).get("result")) or [None])[0]
    if not result:
        raise ValueError(f"No quote data returned for {ticker}")
    return result


def _yahoo_quote_summary(ticker: str) -> dict[str, Any]:
    urls = [
        f"https://query1.finance.yahoo.com/v10/finance/quoteSummary/{ticker}",
        f"https://query2.finance.yahoo.com/v10/finance/quoteSummary/{ticker}",
    ]
    params = {
        "modules": "price,summaryProfile,financialData,defaultKeyStatistics,quoteType",
    }
    payload = _fetch_json(urls, params)
    result = (((payload.get("quoteSummary") or {}).get("result")) or [None])[0]
    if not result:
        raise ValueError(f"No quote summary returned for {ticker}")
    return result


def _yahoo_chart(ticker: str) -> dict[str, Any]:
    urls = [
        f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}",
        f"https://query2.finance.yahoo.com/v8/finance/chart/{ticker}",
    ]
    params = {"range": "6mo", "interval": "1d", "includePrePost": "false", "events": "div,splits"}
    payload = _fetch_json(urls, params)
    result = (((payload.get("chart") or {}).get("result")) or [None])[0]
    if not result:
        raise ValueError(f"No chart data returned for {ticker}")
    meta = result.get("meta") or {}
    quote = ((result.get("indicators") or {}).get("quote") or [{}])[0]
    return {
        "close": quote.get("close") or [],
        "volume": quote.get("volume") or [],
        "meta": meta,
    }


def _yfinance_market_bundle(ticker: str) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    import yfinance as yf

    ticker_obj = yf.Ticker(ticker)
    info = ticker_obj.info or {}
    history = ticker_obj.history(period="6mo", interval="1d", auto_adjust=False)
    closes = []
    volumes = []
    if history is not None and not history.empty:
        closes = [float(value) for value in history["Close"].tolist()]
        volumes = [float(value) for value in history["Volume"].tolist()]

    quote = {
        "symbol": ticker.upper(),
        "shortName": info.get("shortName") or info.get("longName") or ticker.upper(),
        "longName": info.get("longName") or info.get("shortName") or ticker.upper(),
        "currency": info.get("currency") or info.get("financialCurrency") or "USD",
        "region": info.get("country") or info.get("region") or "Unknown",
        "sector": info.get("sector") or "Unknown",
        "industry": info.get("industry") or "Unknown",
        "regularMarketPrice": _as_float(info.get("currentPrice")) or _as_float(info.get("regularMarketPrice")),
        "forwardPE": _as_float(info.get("forwardPE")),
        "trailingPE": _as_float(info.get("trailingPE")),
        "beta": _as_float(info.get("beta")),
    }
    summary = {
        "summaryProfile": {
            "sector": info.get("sector"),
            "industry": info.get("industry"),
            "country": info.get("country") or info.get("region"),
            "longBusinessSummary": info.get("longBusinessSummary"),
        },
        "financialData": {
            "revenueGrowth": _as_float(info.get("revenueGrowth")),
            "grossMargins": _as_float(info.get("grossMargins")),
            "operatingMargins": _as_float(info.get("operatingMargins")),
            "freeCashflow": _as_float(info.get("freeCashflow")),
            "operatingCashflow": _as_float(info.get("operatingCashflow")),
            "returnOnEquity": _as_float(info.get("returnOnEquity")),
        },
        "defaultKeyStatistics": {
            "forwardPE": _as_float(info.get("forwardPE")),
            "enterpriseToEbitda": _as_float(info.get("enterpriseToEbitda")),
            "beta": _as_float(info.get("beta")),
        },
    }
    chart = {
        "close": closes,
        "volume": volumes,
        "meta": {
            "regularMarketPrice": quote.get("regularMarketPrice"),
            "currency": quote.get("currency"),
        },
    }
    return quote, summary, chart


def _as_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, dict):
        for key in ("raw", "fmt", "longFmt"):
            if key in value and value[key] is not None:
                try:
                    return float(value[key])
                except (TypeError, ValueError):
                    continue
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _build_macro_snapshot(profile: dict[str, Any], fred_api_key: str | None) -> dict[str, Any]:
    currency = str(profile.get("currency") or "USD").upper()
    region = profile.get("region") or "Unknown"
    company_name = profile.get("company_name") or profile.get("ticker") or "The company"

    rates_signal = _fred_macro_signal("GS10", "10Y Treasury", fred_api_key)
    inflation_signal = _fred_macro_signal("CPIAUCSL", "CPI", fred_api_key)
    credit_signal = _fred_macro_signal("BAMLC0A4CBBB", "BBB OAS", fred_api_key)

    rates_summary_parts = []
    if rates_signal:
        rates_summary_parts.append(
            f"{rates_signal['label']} is {rates_signal['current_value']:.2f} with a {rates_signal['percentile_10y']:.0f}th percentile 10Y context."
        )
    if credit_signal:
        rates_summary_parts.append(
            f"{credit_signal['label']} sits at {credit_signal['current_value']:.2f}, framing financing conditions."
        )
    rates_summary = " ".join(rates_summary_parts) or "FRED macro rates context was unavailable for this run."

    macro_summary_parts = []
    if inflation_signal:
        macro_summary_parts.append(
            f"Inflation proxy {inflation_signal['label']} is running at {inflation_signal['current_value']:.2f} with a {inflation_signal['percentile_10y']:.0f}th percentile backdrop."
        )
    if rates_signal:
        macro_summary_parts.append("Macro framing is tied to real rates, liquidity, and cost-of-capital pressure.")
    macro_summary = " ".join(macro_summary_parts) or f"Macro context for {company_name} could not be refreshed from FRED."

    regional_context = (
        "Asia-Pacific context should be considered for supply chains, end demand, and regional policy spillovers."
        if region != "United States"
        else "Global demand, especially Asia-linked supply chains, can still influence expectations."
    )
    currency_sensitivity = (
        f"{company_name} reports in {currency}, so valuation should be monitored against rates and FX translation risk."
    )

    data_quality_flags = []
    if not rates_signal:
        data_quality_flags.append("fred_rates_unavailable")
    if not inflation_signal:
        data_quality_flags.append("fred_inflation_unavailable")
    if not credit_signal:
        data_quality_flags.append("fred_credit_unavailable")

    return {
        "macro_summary": macro_summary,
        "rates_summary": rates_summary,
        "currency_sensitivity_notes": currency_sensitivity,
        "asia_pacific_angle": regional_context,
        "macro_risk": "Tighter financial conditions or slowing nominal growth could pressure multiples and expectations.",
        "data_quality_flags": data_quality_flags,
        "signals": [signal for signal in (rates_signal, inflation_signal, credit_signal) if signal],
    }


def _fred_macro_signal(series_id: str, label: str, api_key: str | None, lookback_years: int = 10) -> dict[str, Any] | None:
    if not api_key:
        return None
    try:
        series = _fred_series_observations(series_id, api_key)
    except Exception:
        return None
    values = [item for item in series if item["value"] is not None]
    if len(values) < 2:
        return None
    current = values[-1]["value"]
    history = [item["value"] for item in values if item["date"] >= _lookback_cutoff(lookback_years)]
    if not history:
        history = [item["value"] for item in values]
    percentile = sum(1 for item in history if item <= current) / len(history) * 100
    return {
        "series_id": series_id,
        "label": label,
        "current_value": current,
        "percentile_10y": round(percentile, 1),
        "source": "fred",
    }


def _fred_series_observations(series_id: str, api_key: str) -> list[dict[str, Any]]:
    payload = _fetch_json(
        ["https://api.stlouisfed.org/fred/series/observations"],
        {
            "series_id": series_id,
            "api_key": api_key,
            "file_type": "json",
            "sort_order": "asc",
        },
    )
    observations = payload.get("observations") or []
    rows = []
    for row in observations:
        value = None if row.get("value") in {None, "."} else _as_float(row.get("value"))
        rows.append({"date": str(row.get("date") or ""), "value": value})
    return rows


def _lookback_cutoff(years: int) -> str:
    return (date.today() - timedelta(days=365 * years)).isoformat()


def _damodaran_industry_snapshot(sector: str, industry: str) -> dict[str, Any] | None:
    try:
        from compdata.comp_data import Industry, industry_name_list
    except Exception:
        return None

    matched = _match_damodaran_industry(
        sector=sector,
        industry=industry,
        industry_names=list(industry_name_list),
    )
    if not matched:
        return None

    ind = Industry(matched)
    pe_series = _safe_compdata_series(ind, "get_price_earnings")
    ev_series = _safe_compdata_series(ind, "get_ev_multiples")
    coc_series = _safe_compdata_series(ind, "get_cost_of_capital")
    margin_series = _safe_compdata_series(ind, "get_margins")
    beta_series = _safe_compdata_series(ind, "get_betas")

    return {
        "matched_industry": matched,
        "forward_pe": _compdata_series_value(pe_series, ["Current PE", "Trailing PE", "PE"]),
        "ev_ebitda": _compdata_series_value(ev_series, ["EV/EBITDA"]),
        "cost_of_capital": _compdata_series_value(coc_series, ["Cost of capital"]),
        "operating_margin": _compdata_series_value(
            margin_series,
            ["Pre-tax, pre-stock compensation operating margin", "Operating margin"],
        ),
        "unlevered_beta": _compdata_series_value(beta_series, ["Unlevered beta", "Beta"]),
        "source": "damodaran_compdata",
    }


def _safe_compdata_series(industry_obj: Any, method_name: str):
    try:
        return getattr(industry_obj, method_name)()
    except Exception:
        return None


def _match_damodaran_industry(sector: str, industry: str, industry_names: list[str]) -> str | None:
    normalized_industry = str(industry or "").lower().strip()
    normalized_sector = str(sector or "").lower().strip()
    alias_target = _DAMODARAN_INDUSTRY_MAP.get(normalized_industry) or _DAMODARAN_INDUSTRY_MAP.get(normalized_sector)
    if alias_target:
        for name in industry_names:
            if name.lower() == alias_target.lower():
                return name

    normalized_candidates = [
        normalized_industry,
        normalized_sector,
    ]
    exact = {name.lower(): name for name in industry_names}
    for candidate in normalized_candidates:
        if candidate in exact:
            return exact[candidate]

    industry_tokens = _industry_tokens(normalized_industry)
    if industry_tokens:
        best_name = None
        best_score = 0
        for name in industry_names:
            name_tokens = _industry_tokens(name)
            score = len(industry_tokens & name_tokens)
            if score > best_score:
                best_score = score
                best_name = name
        if best_name and best_score >= 1 and "technology" not in industry_tokens:
            return best_name
    return None


def _industry_tokens(value: str) -> set[str]:
    tokens = set(re.findall(r"[a-z]+", value.lower()))
    stop_words = {"and", "the", "of", "services", "technology"}
    return {token for token in tokens if token not in stop_words}


_DAMODARAN_INDUSTRY_MAP = {
    "software - infrastructure": "Software (System & Application)",
    "software - application": "Software (System & Application)",
    "software": "Software (System & Application)",
    "information services": "Information Services",
    "internet content & information": "Software (Internet)",
    "semiconductors": "Semiconductor",
    "semiconductor manufacturing": "Semiconductor",
    "semiconductor equipment": "Semiconductor Equip",
    "consumer electronics": "Electronics (Consumer & Office)",
    "electronics": "Electronics (General)",
    "computer hardware": "Computers/Peripherals",
    "technology": "Computer Services",
}


def _compdata_series_value(series: Any, keys: list[str]) -> float | None:
    if series is None:
        return None
    for key in keys:
        target = key.lower()
        for idx, raw in zip(getattr(series, "index", []), getattr(series, "tolist", lambda: [])()):
            if str(idx).replace("\xa0", " ").strip().lower() == target:
                return _parse_compdata_value(raw)
    return None


def _parse_compdata_value(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).replace("\xa0", "").replace("$", "").replace(",", "").strip()
    is_percent = text.endswith("%")
    text = text.rstrip("%").strip()
    try:
        parsed = float(text)
    except (TypeError, ValueError):
        return None
    return parsed / 100 if is_percent else parsed
