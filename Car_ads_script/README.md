# 🚗 Yad2 Car Market Analytics & Dashboard

A comprehensive data engineering and analysis project that scrapes used car listings from Yad2 (Israel's largest classifieds site), processes the data, and visualizes market trends to find the best purchasing opportunities.

## 📌 Features

* **Advanced Web Scraper**: Mimics browser behavior to extract data from Yad2 (bypassing basic anti-bot protections).
* **Data Cleaning**: parsing prices, years, and removing outliers.
* **Market Analysis**:
    * **Price vs. Year**: Visualizing depreciation curves.
    * **"Sweet Spot" Algorithm**: Identifies the specific production year with the best balance between price drop (depreciation) and vehicle age.
    * **Year-over-Year Depreciation**: Calculates the annual percentage loss in value.
* **Interactive Dashboard**: Built with **Streamlit** and **Plotly** for exploring the data dynamically.
* **Static Report**: Generates a standalone HTML report (`dashboard.html`).

## 📂 Project Structure

```text
├── data_extracter.py        # Main scraping logic (requests + BeautifulSoup)
├── streamlit\app.py                   # Interactive Streamlit Dashboard
├── build_dashboard_plotly.py# Generates the static HTML dashboard
├── main.ipynb               # Jupyter Notebook to orchestrate the process
├── plot_*.py                # Auxiliary plotting scripts for specific metrics
├── yad2_data_sample.csv     # Template file showing required CSV structure
└── README.md                # Project documentation
```


## ⚙️ Installation
Clone the repository:
```bash
git clone [https://github.com/your-username/yad2-car-analytics.git](https://github.com/your-username/yad2-car-analytics.git)
cd yad2-car-analytics
```
Install dependencies: It is recommended to use a virtual environment.
```bash
pip install pandas requests beautifulsoup4 plotly streamlit matplotlib jupyter
```
## requirements - 
```text

pandas
requests
beautifulsoup4
plotly
streamlit
matplotlib
jupyter / cursor or any other platform
numpy
```
## 🚀 Usage
1. Scrape the Data
First, you need to collect fresh data. The scraper is configured to search for a specific car model (defined by Manufacturer and Model ID).

Open data_extracter.py (or run via main.ipynb) and adjust the IDs if needed:

```python
# Example IDs (Subaru Forester)
man = 35    # Manufacturer ID (Subaru)
mod = 10476 # Model ID (Forester)
```
Run the scraper:

```python
python data_extracter.py
```

This will generate a file named yad2_scraped_data.csv.

2. Run the Dashboard
Once you have the CSV file, you can launch the interactive dashboard:

```bash
streamlit run app.py
```

This will open a local web server (usually at http://localhost:8501) where you can filter by price, year, and view the "Sweet Spot" analysis.
<img width="1000" height="400" alt="image" src="https://github.com/user-attachments/assets/fdf2bbef-976e-47da-80a2-0dae97b6fdc3" />

3. Generate Static HTML
To generate a portable HTML report:

```bash
python main.ipynb
# Or run the specific script:
python build_dashboard_plotly.py
```

## 🛡️ Avoiding Blocks & Network Issues
Yad2 employs strict anti-bot measures. Making too many requests in a short time from the same IP address may result in a temporary block (HTTP 403/429 errors).

Recommendations to avoid getting blocked:

Use a VPN: If you are blocked, switching your IP address via a VPN usually resolves the issue immediately.

Rotating Proxies / Reverse Proxy: For heavy usage, it is highly recommended to route traffic through a rotating proxy service or a reverse proxy to distribute requests across multiple IPs.

Respect Delays: The script includes random delays (min_delay / max_delay) between requests. Do not remove them.
# 📊 Data Privacy & Git
Note: The raw scraped data (yad2_scraped_data.csv) is not included in this repository to respect privacy and data ownership. 
A sample file yad2_data_sample.csv is provided to demonstrate the expected schema.

##⚠️ Disclaimer
This project is for educational and research purposes only.

Web scraping may violate the Terms of Service of the target website.

The author is not responsible for any misuse of this tool or potential blocking of IP addresses.

Please use responsibly and insert reasonable delays between requests (already implemented in the code).

Author: Roee Nachman
