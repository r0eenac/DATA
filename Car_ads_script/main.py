import data_extracter
man = 35
mod = 10476
df = data_extracter.run_scraper(manufacturer=man, model=mod, max_pages=10, verbose=False)
import plot_price_over_year
import plot_price_drop
import plot_sweet_point
import plot_price_Distribution_by_Production_Year
import build_dashboard_plotly
out = build_dashboard_plotly.build_yad2_dashboard_html(
    years="2020-2026",
    model="all",
    submodel="all",
    out_html="dashboard.html"
)
print("Saved to:", out)


#### ------------------------------------------------------------------###
# in order to run the streamlit app which generates the dashboard.html file , follow the instructions below:
# 1. open the terminal in the project folder
# 2. run the following command:
# pip install streamlit plotly
# 3. run the following command:
# streamlit run app.py
# a new chrome or the defaulted browser will automatically opened with the dashboard"

# KM is currently unavailable due to YAD2 recently changes made.
#### ------------------------------------------------------------------###



