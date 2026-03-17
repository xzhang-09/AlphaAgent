from __future__ import annotations

from copy import deepcopy


MOCK_COMPANIES = {
    "NVDA": {
        "company_profile": {
            "ticker": "NVDA",
            "company_name": "NVIDIA",
            "sector": "Semiconductors",
            "region": "United States",
            "currency": "USD",
            "catalysts": [
                "Next earnings print and AI server shipment cadence",
                "Further hyperscaler capex commentary",
                "Gross margin stability through product transition",
            ],
        },
        "market": {
            "current_price": 905.0,
            "forward_pe": 31.0,
            "peer_forward_pe": 33.0,
            "ev_ebitda": 24.0,
            "historical_pe_percentile": 42.0,
            "drawdown_pct": -18.0,
            "volume_spike_ratio": 1.8,
            "stress_pe": 24.0,
            "sector_trend_summary": "AI infrastructure demand remains strong, but the supply chain is watching digestion risk and customer concentration.",
            "factor_style_exposure": {
                "growth": "High",
                "quality": "High",
                "momentum": "Moderate after the drawdown",
                "beta": "Elevated",
            },
        },
        "fundamentals": {
            "business_overview": "NVIDIA designs GPUs and accelerated computing platforms serving data center, gaming, and edge AI workloads.",
            "revenue_growth_yoy": 64.0,
            "prior_revenue_growth_yoy": 38.0,
            "gross_margin": 75.2,
            "ebit_margin": 52.5,
            "prior_ebit_margin": 46.4,
            "fcf_margin": 39.0,
            "cash_conversion": 118.0,
            "cash_flow_commentary": "Cash generation remains strong with working capital tailwinds and limited balance-sheet stress.",
            "earnings_surprise_pct": 8.5,
            "management_change": "",
            "regulatory_event": "US export controls remain a live overhang for China shipments.",
            "key_business_drivers": [
                "Hyperscaler AI capex is still expanding",
                "GPU supply remains tight in high-end inference and training clusters",
                "Software and networking attach deepen platform economics",
            ],
            "risk_factors": {
                "competition": "Customer verticalization and peer accelerator launches could slow share gains.",
                "regulation": "Export restrictions into China can reshape mix and lower realized ASPs.",
                "execution": "Product transition risk could pressure gross margin if supply or yields slip.",
            },
        },
        "peers": [
            {"ticker": "AMD", "forward_pe": 34.0, "ev_ebitda": 22.0, "revenue_growth_yoy": 22.0},
            {"ticker": "AVGO", "forward_pe": 29.0, "ev_ebitda": 19.0, "revenue_growth_yoy": 16.0},
        ],
        "macro": {
            "macro_summary": "US policy rates are restrictive, but AI capex remains one of the few clear spending priorities.",
            "fx_summary": "FX is not a primary driver for this name, though international demand still matters for mix.",
            "rates_summary": "Higher real yields can compress growth multiples if earnings revisions cool.",
            "currency_sensitivity_notes": None,
            "asia_pacific_angle": "Asia-Pacific supply-chain execution still matters through packaging, foundry capacity, and China demand.",
            "macro_risk": "A broad capex slowdown or AI digestion phase could cut sentiment faster than fundamentals.",
        },
        "documents": {
            "filings": [
                {"id": "nvda-f1", "title": "10-K Business Overview", "snippet": "Data center revenue expanded on AI compute demand and networking attach."},
                {"id": "nvda-f2", "title": "10-Q Risk Factors", "snippet": "Export control compliance may affect revenue concentration and product mix."},
            ],
            "transcripts": [
                {"id": "nvda-t1", "title": "Q4 Earnings Call", "snippet": "Management highlighted sustained hyperscaler demand and strong backlog visibility."},
                {"id": "nvda-t2", "title": "Analyst Day", "snippet": "Networking, software, and enterprise AI tooling are supporting platform monetization."},
            ],
            "news": [
                {"id": "nvda-n1", "title": "AI Server Capex Update", "snippet": "Large cloud buyers continue lifting capex guidance around accelerated computing."},
                {"id": "nvda-n2", "title": "China Export Watch", "snippet": "Policy discussion remains active around advanced chip shipment controls."},
            ],
        },
    },
    "AMD": {
        "company_profile": {
            "ticker": "AMD",
            "company_name": "Advanced Micro Devices",
            "sector": "Semiconductors",
            "region": "United States",
            "currency": "USD",
            "catalysts": [
                "MI-series accelerator adoption updates",
                "PC recovery and console normalization",
                "Server CPU share gains",
            ],
        },
        "market": {
            "current_price": 178.0,
            "forward_pe": 34.0,
            "peer_forward_pe": 33.0,
            "ev_ebitda": 22.0,
            "historical_pe_percentile": 58.0,
            "drawdown_pct": -16.0,
            "volume_spike_ratio": 1.6,
            "stress_pe": 26.0,
            "sector_trend_summary": "Semiconductor demand is bifurcated between AI strength and mixed industrial or consumer recovery.",
            "factor_style_exposure": {
                "growth": "High",
                "quality": "Moderate",
                "momentum": "Moderate",
                "beta": "High",
            },
        },
        "fundamentals": {
            "business_overview": "AMD supplies CPUs, GPUs, and adaptive computing products across data center, client, gaming, and embedded markets.",
            "revenue_growth_yoy": 22.0,
            "prior_revenue_growth_yoy": 8.0,
            "gross_margin": 52.0,
            "ebit_margin": 21.0,
            "prior_ebit_margin": 18.0,
            "fcf_margin": 16.0,
            "cash_conversion": 92.0,
            "cash_flow_commentary": "Cash generation is recovering, though mix and inventory timing still matter.",
            "earnings_surprise_pct": 4.0,
            "management_change": "",
            "regulatory_event": "",
            "key_business_drivers": [
                "Accelerator ramp into cloud and enterprise deployments",
                "Server CPU momentum versus incumbent share",
                "PC channel normalization",
            ],
            "risk_factors": {
                "competition": "Scale disadvantage against larger rivals can limit pricing power.",
                "regulation": "Advanced chip restrictions can constrain some end markets.",
                "execution": "New product ramp execution remains critical for upside delivery.",
            },
        },
        "peers": [
            {"ticker": "NVDA", "forward_pe": 31.0, "ev_ebitda": 24.0, "revenue_growth_yoy": 64.0},
            {"ticker": "INTC", "forward_pe": 27.0, "ev_ebitda": 14.0, "revenue_growth_yoy": 9.0},
        ],
        "macro": {
            "macro_summary": "Data center spending is resilient, but consumer and industrial recovery remains uneven.",
            "fx_summary": "FX is secondary, though overseas customer mix can influence reported growth.",
            "rates_summary": "Tighter financial conditions can temper speculative multiple re-rating.",
            "currency_sensitivity_notes": None,
            "asia_pacific_angle": "Manufacturing and channel inventory conditions in Asia remain relevant for PCs and gaming.",
            "macro_risk": "A softer enterprise spending cycle could delay AI ramp expectations.",
        },
        "documents": {
            "filings": [
                {"id": "amd-f1", "title": "10-K Segment Review", "snippet": "Data center and client segments remain key swing factors for margin improvement."},
                {"id": "amd-f2", "title": "10-Q Liquidity", "snippet": "Inventory management and disciplined opex are central to free cash flow recovery."},
            ],
            "transcripts": [
                {"id": "amd-t1", "title": "Q4 Earnings Call", "snippet": "Management expects accelerator momentum to build through the year."},
                {"id": "amd-t2", "title": "Investor Conference", "snippet": "Server CPU demand remains healthy across cloud and enterprise customers."},
            ],
            "news": [
                {"id": "amd-n1", "title": "AI Chip Launch Coverage", "snippet": "Buy-side focus remains on meaningful accelerator volume conversion."},
            ],
        },
    },
    "TSM": {
        "company_profile": {
            "ticker": "TSM",
            "company_name": "Taiwan Semiconductor Manufacturing",
            "sector": "Semiconductors",
            "region": "Taiwan",
            "currency": "TWD",
            "catalysts": [
                "Foundry utilization recovery",
                "Advanced node mix improvement",
                "US dollar and Taiwan dollar sensitivity around overseas expansion",
            ],
        },
        "market": {
            "current_price": 142.0,
            "forward_pe": 19.0,
            "peer_forward_pe": 23.0,
            "ev_ebitda": 12.0,
            "historical_pe_percentile": 37.0,
            "drawdown_pct": -12.0,
            "volume_spike_ratio": 1.3,
            "stress_pe": 15.0,
            "sector_trend_summary": "The foundry cycle is improving with AI and advanced packaging strength offsetting slower legacy demand.",
            "factor_style_exposure": {
                "growth": "Moderate",
                "quality": "High",
                "momentum": "Improving",
                "beta": "Moderate",
            },
        },
        "fundamentals": {
            "business_overview": "TSMC is the leading pure-play semiconductor foundry with dominant share in advanced process nodes and packaging.",
            "revenue_growth_yoy": 28.0,
            "prior_revenue_growth_yoy": 11.0,
            "gross_margin": 53.0,
            "ebit_margin": 42.0,
            "prior_ebit_margin": 39.0,
            "fcf_margin": 24.0,
            "cash_conversion": 103.0,
            "cash_flow_commentary": "Cash flow quality is solid, though overseas fab build-out raises capex intensity.",
            "earnings_surprise_pct": 6.0,
            "management_change": "",
            "regulatory_event": "Cross-strait policy and export control developments remain part of the risk backdrop.",
            "key_business_drivers": [
                "Advanced node demand tied to AI accelerators and premium smartphones",
                "CoWoS and advanced packaging capacity expansion",
                "Utilization recovery in HPC outweighing legacy-node softness",
            ],
            "risk_factors": {
                "competition": "Samsung and Intel Foundry are investing aggressively, especially where governments subsidize local capacity.",
                "regulation": "Geopolitical or export-control changes can affect customer planning and geographic mix.",
                "execution": "Overseas fab ramp and cost discipline are key to sustaining margins.",
            },
        },
        "peers": [
            {"ticker": "2330.TW", "forward_pe": 19.0, "ev_ebitda": 12.0, "revenue_growth_yoy": 28.0},
            {"ticker": "005930.KS", "forward_pe": 17.0, "ev_ebitda": 8.0, "revenue_growth_yoy": 14.0},
        ],
        "macro": {
            "macro_summary": "Asia technology exports are recovering, helped by AI demand and inventory normalization.",
            "fx_summary": "A weaker TWD versus USD can support reported margins, while overseas fab spend introduces currency and cost complexity.",
            "rates_summary": "Regional policy remains supportive, but geopolitical risk premium can dominate rate sensitivity.",
            "currency_sensitivity_notes": "Revenue is largely USD-linked while a meaningful cost base remains in TWD, so FX can influence margin cadence.",
            "asia_pacific_angle": "TSMC sits at the center of Asia-Pacific semiconductor supply chains, including Taiwan, Korea, Japan, and China demand considerations.",
            "macro_risk": "Geopolitical shocks or a sharper smartphone slowdown in Asia could offset AI-driven strength.",
        },
        "documents": {
            "filings": [
                {"id": "tsm-f1", "title": "Annual Report Operations", "snippet": "Advanced technologies remain the largest revenue contributor, with strong HPC end demand."},
                {"id": "tsm-f2", "title": "Form 20-F Risks", "snippet": "Global expansion raises cost complexity while geopolitical conditions remain an overhang."},
            ],
            "transcripts": [
                {"id": "tsm-t1", "title": "Q4 Earnings Call", "snippet": "Management expects healthy AI-related demand and ongoing advanced packaging tightness."},
                {"id": "tsm-t2", "title": "Capital Markets Day", "snippet": "Currency remains a partial margin tailwind due to USD revenue exposure."},
            ],
            "news": [
                {"id": "tsm-n1", "title": "Asia Supply Chain Update", "snippet": "Advanced packaging bottlenecks are easing only gradually across the region."},
                {"id": "tsm-n2", "title": "Taiwan FX Watch", "snippet": "TWD moves are being watched for their effect on semiconductor exporters' margin profiles."},
            ],
        },
    },
}


def get_company_bundle(ticker: str) -> dict:
    try:
        return deepcopy(MOCK_COMPANIES[ticker.upper()])
    except KeyError as exc:
        raise ValueError(f"Unsupported ticker: {ticker}") from exc


def has_company_bundle(ticker: str) -> bool:
    return ticker.upper() in MOCK_COMPANIES
