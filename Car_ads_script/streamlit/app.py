import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="Yad2 Cars Dashboard", layout="wide")
st.title("Yad2 Cars – Interactive Dashboard")

DATA_PATH = "yad2_scraped_data.csv"
df = pd.read_csv(DATA_PATH)

# --- Basic cleanup ---
for col in ["Production Year", "Price (₪)", "KM", "Hand"]:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

for col in ["Model", "SubModel", "City", "Link"]:
    if col in df.columns:
        df[col] = df[col].fillna("").astype(str)

df = df.dropna(subset=["Production Year", "Price (₪)"])
df["Production Year"] = df["Production Year"].round().astype(int)

# --- Sidebar filters ---
st.sidebar.header("Filters")

min_year, max_year = int(df["Production Year"].min()), int(df["Production Year"].max())
year_range = st.sidebar.slider("Production Year", min_year, max_year, (min_year, max_year), step=1)

min_price, max_price = int(df["Price (₪)"].min()), int(df["Price (₪)"].max())
price_range = st.sidebar.slider("Price (₪)", min_price, max_price, (min_price, max_price))

# ✅ FIX: Model/SubModel filters (SubModel works also when Model=All)
use_model = "Model" in df.columns and df["Model"].astype(str).str.strip().ne("").any()
use_sub = "SubModel" in df.columns and df["SubModel"].astype(str).str.strip().ne("").any()

model_sel = "All"
sub_sel = "All"

if use_model:
    models = sorted([m for m in df["Model"].dropna().unique().tolist() if str(m).strip()])
    model_sel = st.sidebar.selectbox("Model", ["All"] + models)

if use_sub:
    if use_model and model_sel != "All":
        subs = sorted([s for s in df[df["Model"] == model_sel]["SubModel"].dropna().unique().tolist() if str(s).strip()])
    else:
        subs = sorted([s for s in df["SubModel"].dropna().unique().tolist() if str(s).strip()])

    sub_sel = st.sidebar.selectbox("SubModel", ["All"] + subs)

use_km = "KM" in df.columns and df["KM"].notna().any()
if use_km:
    km_min, km_max = int(df["KM"].min()), int(df["KM"].max())
    km_range = st.sidebar.slider("KM", km_min, km_max, (km_min, km_max), step=1000)
else:
    km_range = None

use_hand = "Hand" in df.columns and df["Hand"].notna().any()
if use_hand:
    hand_vals = sorted(df["Hand"].dropna().unique().tolist())
    hands = st.sidebar.multiselect("Hand", hand_vals, default=hand_vals)
else:
    hands = None

trim_outliers = st.sidebar.checkbox("Trim price outliers (1% - 99%)", value=True)

# --- Apply filters ---
f = df[
    (df["Production Year"].between(*year_range)) &
    (df["Price (₪)"].between(*price_range))
].copy()

# ✅ Apply model/submodel independently
if use_model and model_sel != "All":
    f = f[f["Model"] == model_sel]

if use_sub and sub_sel != "All":
    f = f[f["SubModel"] == sub_sel]

if use_km and km_range:
    f = f[f["KM"].between(*km_range)]

if use_hand and hands is not None:
    f = f[f["Hand"].isin(hands)]

if trim_outliers and len(f) > 10:
    p1, p99 = f["Price (₪)"].quantile([0.01, 0.99])
    f = f[(f["Price (₪)"] >= p1) & (f["Price (₪)"] <= p99)]

# Guard
if f.empty:
    st.warning("No listings match the current filters.")
    st.stop()

# --- KPIs ---
c1, c2, c3, c4 = st.columns(4)
c1.metric("Listings", f"{len(f):,}")
c2.metric("Median Price", f"₪{int(f['Price (₪)'].median()):,}")
c3.metric("Avg Price", f"₪{int(f['Price (₪)'].mean()):,}")
if use_km and f["KM"].notna().any():
    c4.metric("Median KM", f"{int(f['KM'].median()):,}")
else:
    c4.metric("Median KM", "N/A")

# --- Scatter: all listings (Year vs Price) with jitter ---
rng = np.random.default_rng(42)
x = f["Production Year"].values + rng.normal(0, 0.08, size=len(f))

fig_scatter = px.scatter(
    f.assign(YearJitter=x),
    x="YearJitter",
    y="Price (₪)",
    hover_data=[c for c in ["Ad Number", "City", "Model", "SubModel", "KM", "Hand", "Link"] if c in f.columns],
    title="Listings Scatter: Price by Year (each dot = listing)"
)
fig_scatter.update_traces(marker=dict(size=6, opacity=0.35))
fig_scatter.update_xaxes(
    tickmode="array",
    tickvals=sorted(f["Production Year"].unique()),
    title="Production Year",
)
fig_scatter.update_layout(height=520)

# --- Aggregations ---
by_year = f.groupby("Production Year").agg(
    listings=("Price (₪)", "size"),
    avg_price=("Price (₪)", "mean"),
    median_price=("Price (₪)", "median"),
).reset_index().sort_values("Production Year")

# --- Combo: count + avg price by year ---
fig_combo = px.bar(
    by_year,
    x="Production Year",
    y="listings",
    title="Listings Count by Year (bars) + Avg Price (line)"
)
fig_combo.update_layout(height=420)

fig_line = px.line(by_year, x="Production Year", y="avg_price", markers=True)
for t in fig_line.data:
    t.update(yaxis="y2")
fig_combo.add_traces(fig_line.data)

fig_combo.update_layout(
    yaxis=dict(title="Listings Count"),
    yaxis2=dict(title="Avg Price (₪)", overlaying="y", side="right", showgrid=False),
)

# ---------------- Sweet Point (economic) + Depreciation ----------------
by_year["depr_yoy_pct"] = by_year["avg_price"].pct_change() * 100

by_year["depr_from_prev_pct"] = (
    (by_year["avg_price"].shift(1) - by_year["avg_price"]) / by_year["avg_price"].shift(1)
) * 100

by_year["depr_to_next_pct"] = (
    (by_year["avg_price"] - by_year["avg_price"].shift(-1)) / by_year["avg_price"]
) * 100

by_year["availability"] = np.log1p(by_year["listings"])
MIN_LISTINGS = 5
by_year["low_count_penalty"] = np.where(by_year["listings"] < MIN_LISTINGS, 1.0, 0.0)

by_year["sweet_score"] = (
    1.2 * by_year["depr_from_prev_pct"]
    - 1.5 * by_year["depr_to_next_pct"]
    + 0.3 * by_year["availability"]
    - 2.0 * by_year["low_count_penalty"]
)

# ✅ FIX: choose sweet only from years that have BOTH prev and next (avoid edge bias)
candidates = by_year[
    by_year["depr_from_prev_pct"].notna() &
    by_year["depr_to_next_pct"].notna()
].copy()

if not candidates.empty:
    sweet_year = int(candidates.loc[candidates["sweet_score"].idxmax(), "Production Year"])
else:
    sweet_year = int(by_year.loc[by_year["avg_price"].idxmin(), "Production Year"])

# Sweet point chart (bubble by availability)
fig_sweet = px.scatter(
    by_year,
    x="Production Year",
    y="avg_price",
    size="listings",
    hover_data=["listings", "avg_price", "median_price", "sweet_score", "depr_from_prev_pct", "depr_to_next_pct"],
    title="Sweet Point: already-depreciated + low future depreciation + availability"
)
fig_sweet.update_traces(opacity=0.55)
fig_sweet.update_xaxes(tickmode="array", tickvals=by_year["Production Year"].tolist())

# Add star highlight (only if avg_price is valid)
sy = by_year[by_year["Production Year"] == sweet_year].iloc[0]
if pd.notna(sy["avg_price"]):
    fig_sweet.add_trace(
        go.Scatter(
            x=[sweet_year],
            y=[sy["avg_price"]],
            mode="markers",
            marker=dict(size=20, symbol="star"),
            name="Sweet Point"
        )
    )
fig_sweet.update_layout(height=340, showlegend=False)

# Depreciation chart
fig_depr = px.line(
    by_year,
    x="Production Year",
    y="depr_yoy_pct",
    markers=True,
    title="Annual Depreciation: YoY % change in avg price"
)
fig_depr.update_xaxes(tickmode="array", tickvals=by_year["Production Year"].tolist())
fig_depr.update_layout(height=340)

# --- Layout ---
left, right = st.columns([1.35, 1])
with left:
    st.plotly_chart(fig_scatter, use_container_width=True)
with right:
    st.plotly_chart(fig_combo, use_container_width=True)

st.subheader("Value Insights")
cA, cB = st.columns(2)
with cA:
    st.plotly_chart(fig_sweet, use_container_width=True)
with cB:
    st.plotly_chart(fig_depr, use_container_width=True)

st.caption(f"Sweet Point year (per current filters): {sweet_year}")

st.subheader("Filtered Listings")
st.dataframe(
    f.sort_values("Price (₪)").reset_index(drop=True),
    use_container_width=True,
    height=340
)
