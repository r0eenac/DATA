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

df2 = df2[['Production Year', 'Price (₪)']].dropna()
df2['Production Year'] = pd.to_numeric(df2['Production Year'], errors='coerce')
df2['Price (₪)'] = pd.to_numeric(df2['Price (₪)'], errors='coerce')
df2 = df2.dropna()

df2 = df2[(df2['Production Year'] >= 2017) & (df2['Price (₪)'] > 1000)]

# חשוב: שנה כ-int כדי שלא יהיו 2023.5 / טיקים מוזרים
df2['Production Year'] = df2['Production Year'].round().astype(int)

# ---- חישוב ממוצעים ----
avg_prices = df2.groupby('Production Year')['Price (₪)'].mean()
years = avg_prices.index.values
avg_vals = avg_prices.values

# ---- גרף ----
fig, ax = plt.subplots(figsize=(11, 5.5), dpi=120)

# נקודות המודעות
ax.scatter(
    df2['Production Year'],
    df2['Price (₪)'],
    alpha=0.18,
    s=22,
    edgecolors='none',
    label="few ads"
)

# ממוצע לכל שנה
ax.plot(
    years,
    avg_vals,
    marker='o',
    linewidth=2.5,
    markersize=7,
    label="AVG price per year"
)

# טיקים רק בשנים שלמות (קפיצות של 1)
xmin, xmax = int(df2['Production Year'].min()), int(df2['Production Year'].max())
ax.set_xticks(np.arange(xmin, xmax + 1, 1))

# עיצוב נחמד יותר
ax.set_title("price over years trend", fontsize=14, pad=12)
ax.set_xlabel("manufacturer year", fontsize=11)
ax.set_ylabel("price (₪)", fontsize=11)

ax.grid(True, axis='y', alpha=0.25)
ax.grid(False, axis='x')

# להסיר מסגרות מיותרות
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

# פורמט מחיר: עם פסיקים
ax.ticklabel_format(style='plain', axis='y')
ax.get_yaxis().set_major_formatter(
    plt.FuncFormatter(lambda x, p: f"{int(x):,}")
)

# הערת כמות מודעות
ax.text(
    0.01, 0.98,
    f"# of ads: {len(df2):,}",
    transform=ax.transAxes,
    ha='left', va='top',
    fontsize=10,
    alpha=0.85
)

ax.legend(frameon=False, loc="best")

plt.tight_layout()
plt.show()
