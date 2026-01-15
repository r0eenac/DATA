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


df_spot = load_yad2_data()

df_spot = df_spot[['Production Year', 'Price (₪)']].dropna()
df_spot = df_spot[
    (df_spot['Production Year'] > 2019) &
    (df_spot['Price (₪)'] > 1000)
]

avg_prices = df_spot.groupby('Production Year')['Price (₪)'].mean().sort_index()

# ירידת ערך באחוזים משנה לשנה
price_drop_pct = avg_prices.pct_change() * 100
# מסתכלים רק על שנים שבהן הייתה ירידת מחיר (שלילית)
drops_only = price_drop_pct[price_drop_pct < 0]

# sweet spot = הירידה הכי קטנה (הכי קרובה ל-0)
sweet_year = drops_only.idxmax()
sweet_drop = drops_only.loc[sweet_year]
print(
    f"🔍 ה-Sweet Spot לרכישה הוא שנת {sweet_year}.\n"
    f"בירידת ערך של כ-{abs(sweet_drop):.1f}% בלבד לעומת השנה הקודמת.\n"
    f"משנה זו והלאה ירידת הערך מתמתנת משמעותית."
)
import matplotlib.pyplot as plt

plt.figure(figsize=(10,5))
plt.plot(price_drop_pct.index, price_drop_pct.values, 'o-', label='Yearly Price Change (%)')

plt.axvline(
    sweet_year,
    linestyle='--',
    linewidth=2,
    label=f'Sweet Spot: {sweet_year}'
)

plt.axhline(0, color='black', linewidth=0.8)
plt.xlabel("Production Year")
plt.ylabel("Year-over-Year Price Change (%)")
plt.title("Vehicle Depreciation – Finding the Sweet Spot")
plt.grid(True)
plt.legend()
plt.show()
