import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import os

def load_yad2_data(filename='yad2_scraped_data.csv'):
    """
    Load Yad2 scraped data with validation.
    
    Parameters:
    -----------
    filename : str
        CSV file path
    
    Returns:
    --------
    pd.DataFrame
        Raw dataframe from CSV
    
    Raises:
    -------
    FileNotFoundError
        If CSV doesn't exist
    """
    if not os.path.exists(filename):
        raise FileNotFoundError(f"File not found: {filename}")
    
    df = pd.read_csv(filename, encoding='utf-8-sig')
    
    # Validate required columns exist
    required_cols = ['Production Year', 'Price (₪)']
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        raise ValueError(f"Missing columns: {missing}")
    
    return df


df2 = load_yad2_data()


# ---- Clean data ----
df2 = df2[['Production Year', 'Price (₪)']].dropna()
df2['Production Year'] = pd.to_numeric(df2['Production Year'], errors='coerce')
df2['Price (₪)'] = pd.to_numeric(df2['Price (₪)'], errors='coerce')
df2 = df2.dropna()

df2 = df2[(df2['Production Year'] >= 2020) & (df2['Price (₪)'] > 1000)]
df2['Production Year'] = df2['Production Year'].round().astype(int)

# OPTIONAL: remove extreme low/high outliers (helps scale a lot)
p1, p99 = df2['Price (₪)'].quantile([0.01, 0.99])
df2_plot = df2[(df2['Price (₪)'] >= p1) & (df2['Price (₪)'] <= p99)].copy()

# ---- Jitter on X to avoid overplotting ----
rng = np.random.default_rng(42)
jitter = rng.normal(0, 0.06, size=len(df2_plot))  # small horizontal noise
x = df2_plot['Production Year'].values + jitter
y = df2_plot['Price (₪)'].values

# ---- Plot ----
fig, ax = plt.subplots(figsize=(12, 5.5), dpi=190)

ax.scatter(x, y, s=18, alpha=0.58, edgecolors='none')

years = np.arange(df2_plot['Production Year'].min(), df2_plot['Production Year'].max() + 1, 1)
ax.set_xticks(years)
ax.set_xlim(years.min() - 0.5, years.max() + 0.5)

ax.set_title("Used Car Listings: Price Distribution by Production Year", pad=12, fontsize=14)
ax.set_xlabel("Production Year")
ax.set_ylabel("Price (ILS)")

# Price formatting with commas
ax.ticklabel_format(style='plain', axis='y')
ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, p: f"{int(v):,}"))

# Clean look
ax.grid(True, axis='y', alpha=0.22)
ax.grid(False, axis='x')
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

# Note how many points plotted (after outlier trim)
ax.text(
    0.01, 0.98,
    f"Listings plotted: {len(df2_plot):,} (trimmed 1%-99% price range)",
    transform=ax.transAxes,
    ha='left', va='top',
    fontsize=10,
    alpha=0.85
)

plt.tight_layout()
plt.show()
