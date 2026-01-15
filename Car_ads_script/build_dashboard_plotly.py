import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def build_yad2_dashboard_html(
    csv_path="yad2_scraped_data.csv",
    years="all",                 # "all" | (min_year, max_year) | [2020,2021,...] | "2020-2024"
    model="all",                 # "all" | exact model string
    submodel="all",              # "all" | exact submodel string (works only if model is not "all")
    out_html="dashboard.html",
    min_price=1000               # basic sanity filter
):
    # ---------- Load & clean ----------
    df = pd.read_csv(csv_path)

    for col in ["Production Year", "Price (₪)", "KM", "Hand"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=["Production Year", "Price (₪)"]).copy()
    df["Production Year"] = df["Production Year"].round().astype(int)
    df = df[df["Price (₪)"] > min_price].copy()

    # text columns
    for col in ["Model", "SubModel", "City", "Link"]:
        if col in df.columns:
            df[col] = df[col].fillna("").astype(str)

    if "Model" not in df.columns:
        df["Model"] = ""
    if "SubModel" not in df.columns:
        df["SubModel"] = ""

    # ---------- Apply GLOBAL filters (data-level) ----------
    # years filter
    if years != "all" and years is not None:
        if isinstance(years, str) and "-" in years:
            a, b = years.split("-", 1)
            y_from, y_to = int(a.strip()), int(b.strip())
            df = df[df["Production Year"].between(y_from, y_to)].copy()
        elif isinstance(years, (tuple, list)) and len(years) == 2 and all(isinstance(x, (int, np.integer)) for x in years):
            y_from, y_to = int(years[0]), int(years[1])
            df = df[df["Production Year"].between(y_from, y_to)].copy()
        elif isinstance(years, (list, set, tuple)):
            years_set = set(int(x) for x in years)
            df = df[df["Production Year"].isin(years_set)].copy()
        else:
            raise ValueError("years must be 'all', (min,max), 'YYYY-YYYY', or a list of years")

    # model/submodel filter
    if model != "all" and model is not None:
        df = df[df["Model"] == model].copy()
        if submodel != "all" and submodel is not None:
            df = df[df["SubModel"] == submodel].copy()

    if df.empty:
        raise ValueError("No data after applying filters (years/model/submodel).")

    # ---------- jitter for nicer scatter ----------
    rng = np.random.default_rng(42)
    df["YearJitter"] = df["Production Year"] + rng.normal(0, 0.08, size=len(df))

    years_all = sorted(df["Production Year"].unique())
    ymin = float(df["Price (₪)"].min())
    ymax = float(df["Price (₪)"].max())

    def build_aggs(dfx: pd.DataFrame):
        by_year = dfx.groupby("Production Year").agg(
            listings=("Price (₪)", "size"),
            avg_price=("Price (₪)", "mean"),
            median_price=("Price (₪)", "median"),
        ).reset_index().sort_values("Production Year")

        # YoY % change (as you had)
        by_year["depr_yoy_pct"] = by_year["avg_price"].pct_change() * 100

        # ---- NEW: "economic" sweet point ----
        # how much already depreciated from previous year (positive = good)
        by_year["depr_from_prev_pct"] = (
            (by_year["avg_price"].shift(1) - by_year["avg_price"]) / by_year["avg_price"].shift(1)
        ) * 100

        # how much expected to depreciate to next year (positive = bad)
        by_year["depr_to_next_pct"] = (
            (by_year["avg_price"] - by_year["avg_price"].shift(-1)) / by_year["avg_price"]
        ) * 100

        # Availability (liquidity)
        by_year["availability"] = np.log1p(by_year["listings"])

        # Penalize low sample size (unreliable years)
        MIN_LISTINGS = 5
        by_year["low_count_penalty"] = np.where(by_year["listings"] < MIN_LISTINGS, 1.0, 0.0)

        # Fill NaNs (edges: first/last year)
        by_year["depr_from_prev_pct"] = by_year["depr_from_prev_pct"].fillna(0)
        by_year["depr_to_next_pct"] = by_year["depr_to_next_pct"].fillna(0)

        # Sweet score:
        # - prefer years where depreciation already happened (from prev)...
        # - and future depreciation is low (to next)...
        # - and there is enough market data (availability)...
        # - penalize low sample years
        by_year["sweet_score"] = (
            1.2 * by_year["depr_from_prev_pct"]
            - 1.5 * by_year["depr_to_next_pct"]
            + 0.3 * by_year["availability"]
            - 2.0 * by_year["low_count_penalty"]
        )

        sweet_year = None
        if len(by_year) > 0:
            sweet_year = int(by_year.loc[by_year["sweet_score"].idxmax(), "Production Year"])

        return by_year, sweet_year


    # ---------- Dashboard scaffold: 3 rows x 2 cols ----------
    fig = make_subplots(
        rows=3, cols=2,
        subplot_titles=(
            "Scatter: Price by Year (each dot = listing)",
            "Histogram: Price distribution",
            "Count of listings by year",
            "Average price by year",
            "Sweet Point (best balance of price + availability)",
            "Annual depreciation (YoY % change in avg price)",
        ),
        specs=[
            [{"type": "scatter"}, {"type": "histogram"}],
            [{"type": "bar"}, {"type": "scatter"}],
            [{"type": "scatter"}, {"type": "scatter"}],
        ],
        vertical_spacing=0.10,
        horizontal_spacing=0.08
    )

    def add_traces(dfx: pd.DataFrame):
        by_year, sweet_year = build_aggs(dfx)

        # Trace 0: Scatter listings
        customdata = np.stack([
            dfx["Ad Number"] if "Ad Number" in dfx.columns else pd.Series([None] * len(dfx)),
            dfx["City"] if "City" in dfx.columns else pd.Series([""] * len(dfx)),
            dfx["Model"],
            dfx["SubModel"],
            dfx["KM"] if "KM" in dfx.columns else pd.Series([None] * len(dfx)),
            dfx["Hand"] if "Hand" in dfx.columns else pd.Series([None] * len(dfx)),
            dfx["Link"] if "Link" in dfx.columns else pd.Series([""] * len(dfx)),
        ], axis=-1)

        fig.add_trace(
            go.Scatter(
                x=dfx["YearJitter"],
                y=dfx["Price (₪)"],
                mode="markers",
                marker=dict(size=6, opacity=0.33),
                name="Listings",
                customdata=customdata,
                hovertemplate=(
                    "Year: %{x:.2f}<br>"
                    "Price: ₪%{y:,.0f}<br>"
                    "Ad: %{customdata[0]}<br>"
                    "City: %{customdata[1]}<br>"
                    "Model: %{customdata[2]} %{customdata[3]}<br>"
                    "KM: %{customdata[4]}<br>"
                    "Hand: %{customdata[5]}<br>"
                    "<extra></extra>"
                )
            ),
            row=1, col=1
        )

        # Trace 1: Histogram
        fig.add_trace(
            go.Histogram(
                x=dfx["Price (₪)"],
                nbinsx=30,
                opacity=0.75,
                name="Price hist"
            ),
            row=1, col=2
        )

        # Trace 2: Count by year
        fig.add_trace(
            go.Bar(
                x=by_year["Production Year"],
                y=by_year["listings"],
                name="Count"
            ),
            row=2, col=1
        )

        # Trace 3: Avg price by year
        fig.add_trace(
            go.Scatter(
                x=by_year["Production Year"],
                y=by_year["avg_price"],
                mode="lines+markers",
                name="Avg price"
            ),
            row=2, col=2
        )

        # Trace 4: Sweet candidates (size ~ count)
        if len(by_year) > 0:
            cnt = by_year["listings"].values.astype(float)
            sizes = (cnt / (cnt.max() + 1e-9)) * 24 + 6
        else:
            sizes = []

        fig.add_trace(
            go.Scatter(
                x=by_year["Production Year"],
                y=by_year["avg_price"],
                mode="markers",
                marker=dict(size=sizes, opacity=0.55),
                name="Sweet candidates",
                hovertemplate="Year: %{x}<br>Avg: ₪%{y:,.0f}<br><extra></extra>"
            ),
            row=3, col=1
        )

        # Trace 5: Sweet point highlight
        if sweet_year is not None and sweet_year in by_year["Production Year"].values:
            sy = by_year[by_year["Production Year"] == sweet_year].iloc[0]
            fig.add_trace(
                go.Scatter(
                    x=[int(sy["Production Year"])],
                    y=[float(sy["avg_price"])],
                    mode="markers",
                    marker=dict(size=34, opacity=0.9, symbol="star"),
                    name="Sweet point",
                    hovertemplate=(
                        f"Sweet Point<br>Year: {int(sy['Production Year'])}<br>"
                        f"Avg: ₪{sy['avg_price']:,.0f}<br>"
                        f"Count: {int(sy['listings'])}<extra></extra>"
                    )
                ),
                row=3, col=1
            )
        else:
            fig.add_trace(
                go.Scatter(x=[], y=[], mode="markers", marker=dict(size=34, symbol="star"), name="Sweet point"),
                row=3, col=1
            )

        # Trace 6: Depreciation YoY %
        fig.add_trace(
            go.Scatter(
                x=by_year["Production Year"],
                y=by_year["depr_yoy_pct"],
                mode="lines+markers",
                name="YoY depreciation %",
                hovertemplate="Year: %{x}<br>YoY: %{y:.2f}%<extra></extra>"
            ),
            row=3, col=2
        )

    add_traces(df)

    # ---------- Axes formatting ----------
    fig.update_xaxes(tickmode="array", tickvals=years_all, title_text="Production Year", row=1, col=1)
    fig.update_xaxes(title_text="Price (₪)", row=1, col=2)
    fig.update_xaxes(tickmode="array", tickvals=years_all, title_text="Production Year", row=2, col=1)
    fig.update_xaxes(tickmode="array", tickvals=years_all, title_text="Production Year", row=2, col=2)
    fig.update_xaxes(tickmode="array", tickvals=years_all, title_text="Production Year", row=3, col=1)
    fig.update_xaxes(tickmode="array", tickvals=years_all, title_text="Production Year", row=3, col=2)

    fig.update_yaxes(title_text="Price (₪)", row=1, col=1)
    fig.update_yaxes(title_text="Count", row=2, col=1)
    fig.update_yaxes(title_text="Avg Price (₪)", row=2, col=2)
    fig.update_yaxes(title_text="Avg Price (₪)", row=3, col=1)
    fig.update_yaxes(title_text="YoY %", row=3, col=2)

    # year range slider on scatter (zoom)
    fig.update_xaxes(rangeslider=dict(visible=True), row=1, col=1)

    # ---------- Price quick filters (y-range of scatter) ----------
    price_buttons = [
        dict(label="Price: All", method="relayout", args=[{"yaxis.range": [ymin, ymax]}]),
        dict(label="<= 120k", method="relayout", args=[{"yaxis.range": [ymin, 120_000]}]),
        dict(label="120k–150k", method="relayout", args=[{"yaxis.range": [120_000, 150_000]}]),
        dict(label="150k–200k", method="relayout", args=[{"yaxis.range": [150_000, 200_000]}]),
        dict(label=">= 200k", method="relayout", args=[{"yaxis.range": [200_000, ymax]}]),
    ]

    # title suffix for clarity
    suffix_parts = []
    if years != "all" and years is not None:
        suffix_parts.append(f"Years={years}")
    if model != "all" and model is not None:
        suffix_parts.append(f"Model={model}")
    if submodel != "all" and submodel is not None:
        suffix_parts.append(f"SubModel={submodel}")
    suffix = (" | " + ", ".join(suffix_parts)) if suffix_parts else ""

    fig.update_layout(
        title=f"Yad2 Dashboard – Model/SubModel + Year + Price + Sweet Point + Depreciation (Single HTML){suffix}",
        height=1120,
        showlegend=False,
        margin=dict(l=40, r=40, t=100, b=40),
        updatemenus=[
            dict(
                type="buttons",
                direction="right",
                x=0.99, xanchor="right",
                y=1.13, yanchor="top",
                buttons=price_buttons
            ),
        ],
    )

    fig.update_yaxes(tickformat=",", row=1, col=1)
    fig.update_yaxes(tickformat=",", row=2, col=2)
    fig.update_yaxes(tickformat=",", row=3, col=1)

    fig.write_html(out_html, include_plotlyjs="cdn")
    return out_html


# -------------------- Examples --------------------
# 1) All (no filters)
# build_yad2_dashboard_html(years="all", model="all", submodel="all", out_html="dashboard_all.html")

# 2) Years range
# build_yad2_dashboard_html(years=(2020, 2024), out_html="dashboard_2020_2024.html")

# 3) List of years
# build_yad2_dashboard_html(years=[2021, 2022, 2024], out_html="dashboard_selected_years.html")

# 4) Filter by model & submodel + years
# build_yad2_dashboard_html(years="2020-2024", model="אאודי", submodel="Q5", out_html="dashboard_audi_q5_2020_2024.html")
