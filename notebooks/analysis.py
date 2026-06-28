"""
Financial portfolio BI workflow.

Generates a synthetic loan/customer portfolio, cleans it, loads it into an
in-memory SQLite database, runs the analysis queries, and exports the KPI and
trend visuals.
"""

from __future__ import annotations

import math
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "loan_customer_portfolio.csv"
SQL_PATH = ROOT / "sql" / "analysis_queries.sql"
VISUALS_DIR = ROOT / "visuals"
RNG = np.random.default_rng(42)


REGION_COUNTRIES = {
    "North America": ["United States", "Canada", "Mexico"],
    "Europe": ["Germany", "France", "United Kingdom", "Netherlands"],
    "Asia-Pacific": ["India", "China", "Singapore", "Australia"],
    "Middle East & Africa": ["United Arab Emirates", "Saudi Arabia", "South Africa"],
    "Latin America": ["Brazil", "Chile", "Colombia"],
}

SEGMENT_BASE_AMOUNT = {
    "SME": 320_000,
    "Mid-Market": 950_000,
    "Enterprise": 3_400_000,
    "Public Sector": 2_200_000,
}

PRODUCT_MULTIPLIER = {
    "Equipment Finance": 1.00,
    "Leasing": 0.75,
    "Working Capital": 0.55,
    "Project Finance": 1.85,
    "Trade Finance": 0.65,
}

INDUSTRY_RISK_ADJUSTMENT = {
    "Manufacturing": 0.010,
    "Energy": 0.020,
    "Healthcare": -0.010,
    "Technology": -0.005,
    "Transportation": 0.025,
    "Construction": 0.035,
    "Public Sector": -0.030,
    "Retail": 0.018,
}

REGION_RISK_ADJUSTMENT = {
    "North America": -0.004,
    "Europe": -0.008,
    "Asia-Pacific": 0.006,
    "Middle East & Africa": 0.018,
    "Latin America": 0.024,
}

RISK_ORDER = ["Low", "Moderate", "Elevated", "High"]
CHART_COLORS = ["#1F77B4", "#2CA58D", "#F28E2B", "#E15759", "#7B61FF", "#4E79A7"]


def choose_country(region: str) -> str:
    return str(RNG.choice(REGION_COUNTRIES[region]))


def generate_portfolio(rows: int = 1500) -> pd.DataFrame:
    """Build a synthetic loan portfolio from a fixed random seed."""
    regions = RNG.choice(
        list(REGION_COUNTRIES.keys()),
        size=rows,
        p=[0.30, 0.32, 0.20, 0.10, 0.08],
    )
    customer_segments = RNG.choice(
        ["SME", "Mid-Market", "Enterprise", "Public Sector"],
        size=rows,
        p=[0.36, 0.32, 0.22, 0.10],
    )
    industries = RNG.choice(
        [
            "Manufacturing",
            "Energy",
            "Healthcare",
            "Technology",
            "Transportation",
            "Construction",
            "Public Sector",
            "Retail",
        ],
        size=rows,
        p=[0.20, 0.10, 0.12, 0.14, 0.12, 0.11, 0.08, 0.13],
    )
    products = RNG.choice(
        ["Equipment Finance", "Leasing", "Working Capital", "Project Finance", "Trade Finance"],
        size=rows,
        p=[0.34, 0.23, 0.19, 0.14, 0.10],
    )

    month_starts = pd.date_range("2023-01-01", "2025-12-01", freq="MS")
    origination_months = RNG.choice(month_starts, size=rows)
    origination_dates = pd.to_datetime(origination_months) + pd.to_timedelta(
        RNG.integers(0, 28, size=rows), unit="D"
    )
    term_months = RNG.choice([24, 36, 48, 60, 72, 84], size=rows, p=[0.08, 0.20, 0.27, 0.24, 0.15, 0.06])
    maturity_dates = [date + pd.DateOffset(months=int(term)) for date, term in zip(origination_dates, term_months)]

    segment_factor = np.array([SEGMENT_BASE_AMOUNT[segment] for segment in customer_segments])
    product_factor = np.array([PRODUCT_MULTIPLIER[product] for product in products])
    loan_amount = segment_factor * product_factor * RNG.lognormal(mean=0.02, sigma=0.58, size=rows)
    loan_amount = np.clip(loan_amount, 55_000, 12_500_000).round(2)

    current_date = pd.Timestamp("2026-01-01")
    months_since_origination = (
        (current_date.year - pd.to_datetime(origination_dates).year) * 12
        + (current_date.month - pd.to_datetime(origination_dates).month)
    )
    amortization_speed = RNG.uniform(0.40, 0.82, size=rows)
    remaining_factor = 1 - (months_since_origination / term_months) * amortization_speed
    outstanding_balance = loan_amount * np.clip(remaining_factor, 0.08, 0.98)
    outstanding_balance = outstanding_balance.round(2)

    segment_score_base = {
        "SME": 672,
        "Mid-Market": 704,
        "Enterprise": 736,
        "Public Sector": 748,
    }
    industry_score_adjust = {
        "Construction": -22,
        "Transportation": -14,
        "Retail": -12,
        "Energy": -8,
        "Manufacturing": 0,
        "Technology": 9,
        "Healthcare": 11,
        "Public Sector": 18,
    }
    credit_score = np.array([segment_score_base[segment] for segment in customer_segments], dtype=float)
    credit_score += np.array([industry_score_adjust[industry] for industry in industries], dtype=float)
    credit_score += RNG.normal(0, 38, size=rows)
    credit_score = np.clip(credit_score, 520, 820).round(0)

    risk_adjustment = (
        np.array([INDUSTRY_RISK_ADJUSTMENT[industry] for industry in industries])
        + np.array([REGION_RISK_ADJUSTMENT[region] for region in regions])
        + np.where(customer_segments == "SME", 0.020, 0)
        + np.where(customer_segments == "Enterprise", -0.010, 0)
        + np.where(customer_segments == "Public Sector", -0.020, 0)
    )

    interest_rate = 0.038 + np.maximum(0, 735 - credit_score) / 9_000 + risk_adjustment
    interest_rate += np.where(products == "Working Capital", 0.012, 0)
    interest_rate += np.where(products == "Project Finance", 0.007, 0)
    interest_rate += RNG.normal(0, 0.006, size=rows)
    interest_rate = np.clip(interest_rate, 0.032, 0.145).round(4)

    collateral_multiplier = RNG.uniform(0.90, 1.65, size=rows)
    collateral_multiplier += np.where(products == "Equipment Finance", 0.12, 0)
    collateral_multiplier -= np.where(products == "Working Capital", 0.22, 0)
    collateral_value = np.maximum(loan_amount * collateral_multiplier, outstanding_balance * 1.02).round(2)
    ltv = (outstanding_balance / collateral_value).round(3)

    revenue_base = {
        "SME": 5.5,
        "Mid-Market": 58.0,
        "Enterprise": 480.0,
        "Public Sector": 230.0,
    }
    annual_revenue_m = np.array([revenue_base[segment] for segment in customer_segments], dtype=float)
    annual_revenue_m *= RNG.lognormal(mean=0.0, sigma=0.62, size=rows)
    annual_revenue_m = np.clip(annual_revenue_m, 0.8, 2_600).round(2)

    debt_service_coverage_ratio = 1.68 - (risk_adjustment * 8.0) + RNG.normal(0, 0.27, size=rows)
    debt_service_coverage_ratio += np.where(customer_segments == "Public Sector", 0.22, 0)
    debt_service_coverage_ratio -= np.where(products == "Working Capital", 0.08, 0)
    debt_service_coverage_ratio = np.clip(debt_service_coverage_ratio, 0.65, 3.20).round(2)

    base_default_probability = 0.012 + risk_adjustment
    base_default_probability += np.maximum(0, 675 - credit_score) / 2_900
    base_default_probability += np.maximum(0, ltv - 0.78) * 0.08
    base_default_probability += np.maximum(0, 1.15 - debt_service_coverage_ratio) * 0.055
    default_probability = np.clip(base_default_probability, 0.003, 0.16)

    late_60_probability = np.clip(default_probability * 1.25 + 0.010, 0.010, 0.22)
    late_30_probability = np.clip(default_probability * 1.80 + 0.025, 0.020, 0.30)
    grace_probability = np.clip(default_probability * 1.40 + 0.030, 0.025, 0.22)
    random_draw = RNG.random(rows)

    payment_status = np.full(rows, "Current", dtype=object)
    days_past_due = np.zeros(rows, dtype=int)
    default_mask = random_draw < default_probability
    late_60_mask = (random_draw >= default_probability) & (random_draw < default_probability + late_60_probability)
    late_30_mask = (
        (random_draw >= default_probability + late_60_probability)
        & (random_draw < default_probability + late_60_probability + late_30_probability)
    )
    grace_mask = (
        (random_draw >= default_probability + late_60_probability + late_30_probability)
        & (
            random_draw
            < default_probability + late_60_probability + late_30_probability + grace_probability
        )
    )

    payment_status[default_mask] = "Default"
    days_past_due[default_mask] = RNG.integers(120, 241, size=default_mask.sum())
    payment_status[late_60_mask] = "Late 60"
    days_past_due[late_60_mask] = RNG.integers(60, 120, size=late_60_mask.sum())
    payment_status[late_30_mask] = "Late 30"
    days_past_due[late_30_mask] = RNG.integers(30, 60, size=late_30_mask.sum())
    payment_status[grace_mask] = "Grace Period"
    days_past_due[grace_mask] = RNG.integers(1, 30, size=grace_mask.sum())

    score_component = np.maximum(0, 720 - credit_score) * 0.18
    ltv_component = np.maximum(0, ltv - 0.62) * 80
    dscr_component = np.maximum(0, 1.55 - debt_service_coverage_ratio) * 26
    payment_component = np.where(payment_status == "Default", 45, 0)
    payment_component += np.where(payment_status == "Late 60", 28, 0)
    payment_component += np.where(payment_status == "Late 30", 18, 0)
    risk_score = 18 + score_component + ltv_component + dscr_component + payment_component
    risk_score += np.array([INDUSTRY_RISK_ADJUSTMENT[industry] for industry in industries]) * 180
    risk_score = np.clip(risk_score, 5, 100).round(1)
    risk_bucket = pd.cut(
        risk_score,
        bins=[0, 35, 55, 75, 100],
        labels=["Low", "Moderate", "Elevated", "High"],
        include_lowest=True,
    ).astype(str)

    df = pd.DataFrame(
        {
            "loan_id": [f"L{100000 + i}" for i in range(rows)],
            "customer_id": [f"C{RNG.integers(1000, 1380)}" for _ in range(rows)],
            "origination_date": pd.to_datetime(origination_dates).strftime("%Y-%m-%d"),
            "maturity_date": pd.to_datetime(maturity_dates).strftime("%Y-%m-%d"),
            "region": regions,
            "country": [choose_country(region) for region in regions],
            "industry": industries,
            "customer_segment": customer_segments,
            "loan_product": products,
            "loan_amount": loan_amount,
            "outstanding_balance": outstanding_balance,
            "interest_rate": interest_rate,
            "term_months": term_months,
            "credit_score": credit_score,
            "annual_revenue_m": annual_revenue_m,
            "collateral_value": collateral_value,
            "ltv": ltv,
            "debt_service_coverage_ratio": debt_service_coverage_ratio,
            "payment_status": payment_status,
            "days_past_due": days_past_due,
            "risk_score": risk_score,
            "risk_bucket": risk_bucket,
            "default_flag": default_mask.astype(int),
        }
    )

    # Inject missing values and duplicate rows for the cleaning step to handle.
    df.loc[RNG.choice(df.index, size=26, replace=False), "credit_score"] = np.nan
    df.loc[RNG.choice(df.index, size=18, replace=False), "annual_revenue_m"] = np.nan
    df.loc[RNG.choice(df.index, size=15, replace=False), "collateral_value"] = np.nan
    df.loc[RNG.choice(df.index, size=12, replace=False), "industry"] = np.nan
    duplicate_rows = df.sample(18, random_state=7)
    df = pd.concat([df, duplicate_rows], ignore_index=True)
    return df


def clean_portfolio(raw_df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, object]]:
    """Clean duplicates, missing values, types, and derived ratios."""
    missing_before = raw_df.isna().sum()
    duplicate_count = int(raw_df.duplicated(subset=["loan_id"]).sum())

    df = raw_df.drop_duplicates(subset=["loan_id"], keep="first").copy()
    df["origination_date"] = pd.to_datetime(df["origination_date"])
    df["maturity_date"] = pd.to_datetime(df["maturity_date"])

    numeric_columns = [
        "loan_amount",
        "outstanding_balance",
        "interest_rate",
        "term_months",
        "credit_score",
        "annual_revenue_m",
        "collateral_value",
        "ltv",
        "debt_service_coverage_ratio",
        "days_past_due",
        "risk_score",
        "default_flag",
    ]
    for column in numeric_columns:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    df["industry"] = df["industry"].fillna("Unspecified")
    df["credit_score"] = df["credit_score"].fillna(
        df.groupby("customer_segment")["credit_score"].transform("median")
    )
    df["annual_revenue_m"] = df["annual_revenue_m"].fillna(
        df.groupby("customer_segment")["annual_revenue_m"].transform("median")
    )
    collateral_from_ltv = df["outstanding_balance"] / df["ltv"].replace(0, np.nan)
    df["collateral_value"] = df["collateral_value"].fillna(collateral_from_ltv)
    df["collateral_value"] = df["collateral_value"].fillna(df["collateral_value"].median())
    df["ltv"] = (df["outstanding_balance"] / df["collateral_value"]).clip(0, 1.4).round(3)

    date_columns = ["origination_date", "maturity_date"]
    for column in date_columns:
        df[column] = df[column].dt.strftime("%Y-%m-%d")

    missing_after = df.isna().sum()
    cleaning_log = {
        "raw_rows": len(raw_df),
        "clean_rows": len(df),
        "duplicates_removed": duplicate_count,
        "missing_before": missing_before[missing_before > 0].to_dict(),
        "missing_after": missing_after[missing_after > 0].to_dict(),
    }
    return df, cleaning_log


def load_named_queries(path: Path) -> dict[str, str]:
    queries: dict[str, list[str]] = {}
    current_name: str | None = None

    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("-- name:"):
            current_name = line.split(":", 1)[1].strip()
            queries[current_name] = []
        elif current_name:
            queries[current_name].append(line)

    return {name: "\n".join(lines).strip().rstrip(";") for name, lines in queries.items()}


def run_sql_analysis(clean_df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    queries = load_named_queries(SQL_PATH)
    with sqlite3.connect(":memory:") as connection:
        clean_df.to_sql("loan_portfolio", connection, if_exists="replace", index=False)
        return {name: pd.read_sql_query(query, connection) for name, query in queries.items()}


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    font_names = ["arialbd.ttf" if bold else "arial.ttf", "segoeuib.ttf" if bold else "segoeui.ttf"]
    for name in font_names:
        try:
            return ImageFont.truetype(f"C:/Windows/Fonts/{name}", size)
        except OSError:
            continue
    return ImageFont.load_default()


def draw_text(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    size: int = 24,
    fill: str = "#1F2937",
    bold: bool = False,
    anchor: str | None = None,
) -> None:
    draw.text(xy, text, font=font(size, bold=bold), fill=fill, anchor=anchor)


def text_width(draw: ImageDraw.ImageDraw, text: str, size: int, bold: bool = False) -> int:
    bbox = draw.textbbox((0, 0), text, font=font(size, bold=bold))
    return bbox[2] - bbox[0]


def money_millions(value: float) -> str:
    return f"${value / 1_000_000:.1f}M"


def save_kpi_summary(kpi: pd.Series, path: Path) -> None:
    width, height = 1400, 850
    image = Image.new("RGB", (width, height), "#F6F7F9")
    draw = ImageDraw.Draw(image)

    draw_text(draw, (64, 56), "Financial Portfolio KPI Summary", 42, "#111827", bold=True)
    draw_text(draw, (66, 112), "Cleaned portfolio metrics from the SQLite analysis", 23, "#4B5563")

    metrics = [
        ("Total outstanding", money_millions(kpi["total_outstanding"]), "#1F77B4"),
        ("Loans", f"{int(kpi['loans']):,}", "#2CA58D"),
        ("Customers", f"{int(kpi['customers']):,}", "#F28E2B"),
        ("Avg interest rate", f"{kpi['avg_interest_rate_pct']:.2f}%", "#7B61FF"),
        ("Delinquency rate", f"{kpi['delinquency_rate_pct']:.2f}%", "#E15759"),
        ("Default rate", f"{kpi['default_rate_pct']:.2f}%", "#B07AA1"),
        ("Weighted avg LTV", f"{kpi['weighted_avg_ltv']:.2f}", "#59A14F"),
        ("Exposure at risk", f"{kpi['exposure_at_risk_pct']:.2f}%", "#EDC948"),
    ]

    card_w, card_h = 300, 190
    start_x, start_y = 64, 185
    gap_x, gap_y = 32, 36
    for index, (label, value, accent) in enumerate(metrics):
        row, col = divmod(index, 4)
        x = start_x + col * (card_w + gap_x)
        y = start_y + row * (card_h + gap_y)
        draw.rounded_rectangle((x, y, x + card_w, y + card_h), radius=10, fill="#FFFFFF", outline="#D9DEE8", width=2)
        draw.rounded_rectangle((x, y, x + 12, y + card_h), radius=10, fill=accent)
        draw_text(draw, (x + 34, y + 34), label, 23, "#4B5563")
        draw_text(draw, (x + 34, y + 92), value, 38, "#111827", bold=True)

    draw_text(draw, (64, 765), "Risk definition: exposure at risk includes Elevated and High buckets.", 22, "#4B5563")
    image.save(path)


def save_monthly_trend(monthly: pd.DataFrame, path: Path) -> None:
    width, height = 1400, 850
    margin_left, margin_right, margin_top, margin_bottom = 115, 70, 185, 130
    chart_w = width - margin_left - margin_right
    chart_h = height - margin_top - margin_bottom

    image = Image.new("RGB", (width, height), "#FFFFFF")
    draw = ImageDraw.Draw(image)
    draw_text(draw, (64, 54), "Monthly Origination Trend", 40, "#111827", bold=True)
    draw_text(draw, (66, 106), "Total new loan amount by origination month", 23, "#4B5563")

    values = monthly["originated_amount"].astype(float).to_numpy()
    months = monthly["month"].astype(str).to_list()
    max_value = float(values.max())
    y_axis_max = math.ceil(max_value / 10_000_000) * 10_000_000

    for i in range(6):
        y = margin_top + chart_h - int(chart_h * i / 5)
        value = y_axis_max * i / 5
        draw.line((margin_left, y, width - margin_right, y), fill="#E5E7EB", width=1)
        draw_text(draw, (28, y - 12), money_millions(value), 18, "#6B7280")

    points = []
    for idx, value in enumerate(values):
        x = margin_left + int(idx * chart_w / (len(values) - 1))
        y = margin_top + chart_h - int((value / y_axis_max) * chart_h)
        points.append((x, y))

    draw.line(points, fill="#1F77B4", width=5, joint="curve")
    for point in points:
        draw.ellipse((point[0] - 5, point[1] - 5, point[0] + 5, point[1] + 5), fill="#2CA58D")

    draw.line((margin_left, margin_top, margin_left, margin_top + chart_h), fill="#374151", width=2)
    draw.line((margin_left, margin_top + chart_h, width - margin_right, margin_top + chart_h), fill="#374151", width=2)

    for idx, month in enumerate(months):
        if idx % 3 == 0 or idx == len(months) - 1:
            x = margin_left + int(idx * chart_w / (len(months) - 1))
            draw_text(draw, (x - 34, margin_top + chart_h + 24), month, 17, "#4B5563")

    peak_idx = int(values.argmax())
    peak_point = points[peak_idx]
    peak_label = f"Peak: {months[peak_idx]} ({money_millions(values[peak_idx])})"
    label_x = min(peak_point[0] + 18, width - margin_right - text_width(draw, peak_label, 20) - 12)
    draw.rounded_rectangle((label_x - 10, peak_point[1] - 48, label_x + text_width(draw, peak_label, 20) + 10, peak_point[1] - 12), radius=8, fill="#F3F4F6")
    draw_text(draw, (label_x, peak_point[1] - 43), peak_label, 20, "#111827", bold=True)
    image.save(path)


def save_segment_performance(segment: pd.DataFrame, path: Path) -> None:
    data = segment.sort_values("total_outstanding", ascending=True).reset_index(drop=True)
    width, height = 1400, 850
    image = Image.new("RGB", (width, height), "#FFFFFF")
    draw = ImageDraw.Draw(image)
    draw_text(draw, (64, 54), "Customer Segment Performance", 40, "#111827", bold=True)
    draw_text(draw, (66, 106), "Outstanding balance with delinquency and default context", 23, "#4B5563")

    left, top, bar_w, bar_h, gap = 270, 185, 870, 72, 48
    max_value = float(data["total_outstanding"].max())

    for idx, row in data.iterrows():
        y = top + idx * (bar_h + gap)
        value = float(row["total_outstanding"])
        fill_w = int((value / max_value) * bar_w)
        color = CHART_COLORS[idx % len(CHART_COLORS)]
        draw_text(draw, (64, y + 20), str(row["customer_segment"]), 25, "#111827", bold=True)
        draw.rounded_rectangle((left, y, left + bar_w, y + bar_h), radius=8, fill="#EEF2F7")
        draw.rounded_rectangle((left, y, left + fill_w, y + bar_h), radius=8, fill=color)
        draw_text(draw, (left + fill_w + 18, y + 8), money_millions(value), 25, "#111827", bold=True)
        context = f"Delinq {row['delinquency_rate_pct']:.1f}% | Default {row['default_rate_pct']:.1f}%"
        draw_text(draw, (left + fill_w + 18, y + 43), context, 19, "#4B5563")

    image.save(path)


def save_risk_bucket_summary(risk: pd.DataFrame, path: Path) -> None:
    data = risk.copy()
    data["risk_bucket"] = pd.Categorical(data["risk_bucket"], categories=RISK_ORDER, ordered=True)
    data = data.sort_values("risk_bucket")

    width, height = 1400, 850
    image = Image.new("RGB", (width, height), "#FFFFFF")
    draw = ImageDraw.Draw(image)
    draw_text(draw, (64, 54), "Risk Bucket Exposure", 40, "#111827", bold=True)
    draw_text(draw, (66, 106), "Exposure share and default rate by risk bucket", 23, "#4B5563")

    left, bottom = 165, 710
    chart_w, chart_h = 1060, 500
    bar_gap = 75
    bar_w = int((chart_w - bar_gap * (len(data) - 1)) / len(data))
    max_share = max(40, math.ceil(float(data["exposure_share_pct"].max()) / 5) * 5)
    colors = {
        "Low": "#2CA58D",
        "Moderate": "#1F77B4",
        "Elevated": "#F28E2B",
        "High": "#E15759",
    }

    for i in range(6):
        y = bottom - int(chart_h * i / 5)
        value = max_share * i / 5
        draw.line((left, y, left + chart_w, y), fill="#E5E7EB", width=1)
        draw_text(draw, (68, y - 12), f"{value:.0f}%", 18, "#6B7280")

    for idx, row in data.reset_index(drop=True).iterrows():
        bucket = str(row["risk_bucket"])
        share = float(row["exposure_share_pct"])
        default_rate = float(row["default_rate_pct"])
        x = left + idx * (bar_w + bar_gap)
        bar_h_actual = int((share / max_share) * chart_h)
        y = bottom - bar_h_actual
        draw.rounded_rectangle((x, y, x + bar_w, bottom), radius=10, fill=colors[bucket])
        label = f"{share:.1f}%"
        draw_text(draw, (x + bar_w // 2, y - 36), label, 24, "#111827", bold=True, anchor="mm")
        draw_text(draw, (x + bar_w // 2, bottom + 36), bucket, 24, "#111827", bold=True, anchor="mm")
        draw_text(draw, (x + bar_w // 2, bottom + 70), f"Default {default_rate:.1f}%", 19, "#4B5563", anchor="mm")

    draw.line((left, bottom - chart_h, left, bottom), fill="#374151", width=2)
    draw.line((left, bottom, left + chart_w, bottom), fill="#374151", width=2)
    image.save(path)


def build_insights(tables: dict[str, pd.DataFrame]) -> list[str]:
    kpi = tables["kpi_summary"].iloc[0]
    regions = tables["region_performance"]
    segments = tables["segment_performance"]
    industries = tables["industry_concentration"]
    risk = tables["risk_bucket_summary"]
    monthly = tables["monthly_trend"]

    top_region = regions.iloc[0]
    best_region = regions.sort_values(["default_rate_pct", "delinquency_rate_pct"]).iloc[0]
    weakest_segment = segments.sort_values(["default_rate_pct", "delinquency_rate_pct"], ascending=False).iloc[0]
    largest_segment = segments.iloc[0]
    top_industry = industries.iloc[0]
    peak_month = monthly.sort_values("originated_amount", ascending=False).iloc[0]
    elevated_exposure = risk[risk["risk_bucket"].isin(["Elevated", "High"])]["exposure_share_pct"].sum()

    return [
        f"Total outstanding portfolio is {money_millions(kpi['total_outstanding'])} across {int(kpi['loans']):,} loans and {int(kpi['customers']):,} customers.",
        f"{top_region['region']} is the largest region by outstanding balance ({money_millions(top_region['total_outstanding'])}).",
        f"{best_region['region']} has the strongest repayment profile, with {best_region['default_rate_pct']:.2f}% default rate and {best_region['delinquency_rate_pct']:.2f}% 30+ day delinquency.",
        f"{largest_segment['customer_segment']} is the biggest customer segment by exposure, while {weakest_segment['customer_segment']} shows the highest default pressure at {weakest_segment['default_rate_pct']:.2f}%.",
        f"{top_industry['industry']} is the top industry concentration at {top_industry['exposure_share_pct']:.2f}% of outstanding balance.",
        f"Elevated and High buckets represent {elevated_exposure:.2f}% of portfolio exposure, which is the main risk-monitoring group.",
        f"Origination volume peaked in {peak_month['month']} at {money_millions(peak_month['originated_amount'])}.",
    ]


def export_visuals(tables: dict[str, pd.DataFrame]) -> None:
    VISUALS_DIR.mkdir(exist_ok=True)
    save_kpi_summary(tables["kpi_summary"].iloc[0], VISUALS_DIR / "kpi_summary.png")
    save_monthly_trend(tables["monthly_trend"], VISUALS_DIR / "monthly_trend.png")
    save_segment_performance(tables["segment_performance"], VISUALS_DIR / "segment_performance.png")
    save_risk_bucket_summary(tables["risk_bucket_summary"], VISUALS_DIR / "risk_bucket_summary.png")


def main() -> None:
    DATA_PATH.parent.mkdir(exist_ok=True)
    VISUALS_DIR.mkdir(exist_ok=True)

    raw_df = generate_portfolio()
    raw_df.to_csv(DATA_PATH, index=False)

    clean_df, cleaning_log = clean_portfolio(raw_df)
    tables = run_sql_analysis(clean_df)
    export_visuals(tables)
    insights = build_insights(tables)

    print("Cleaning summary")
    print(f"- Raw rows: {cleaning_log['raw_rows']:,}")
    print(f"- Clean rows: {cleaning_log['clean_rows']:,}")
    print(f"- Duplicates removed: {cleaning_log['duplicates_removed']:,}")
    print(f"- Missing before: {cleaning_log['missing_before']}")
    print(f"- Missing after: {cleaning_log['missing_after']}")
    print()

    print("KPI summary")
    print(tables["kpi_summary"].to_string(index=False))
    print()

    print("Business insights")
    for insight in insights:
        print(f"- {insight}")
    print()
    print(f"Dataset saved to: {DATA_PATH}")
    print(f"Visuals saved to: {VISUALS_DIR}")


if __name__ == "__main__":
    main()
