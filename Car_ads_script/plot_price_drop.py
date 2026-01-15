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


df3 = load_yad2_data()


# Ensure 'Production Year' and 'Price (₪)' columns exist and filter out invalid data
df3 = df3[['Production Year', 'Price (₪)']].dropna()
df3 = df3[df3['Production Year'] > 0]  # Remove invalid years
df3 = df3[df3['Price (₪)'] > 0]  # Remove invalid prices
df3 = df3[df3['Production Year'] > 2019 ]
df3 = df3[df3['Price (₪)'] >1000 ]
# Group by 'Production Year' and calculate the average price
avg_prices = df3.groupby('Production Year')['Price (₪)'].mean()

# Calculate year-over-year price drop percentage
price_drop = avg_prices.pct_change() * 100  # Convert to percentage

# Plot the year-over-year price drop
plt.figure(figsize=(10, 5))
plt.plot(price_drop.index, price_drop, 's-', color="red", label="Yearly Price Drop (%)")

# Labels and title
plt.xlabel("Production Year")
plt.ylabel("Price Drop (%)")
plt.title("Year-over-Year Vehicle Price Drop")
plt.axhline(0, color='black', linestyle='--', linewidth=0.8)  # Reference line at 0%
plt.grid(True, linestyle="--", alpha=0.6)
plt.legend()

# Show the plot
plt.show()
