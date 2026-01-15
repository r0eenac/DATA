#pip install streamlit plotly
import requests
import time
import json
import random
import logging
import pandas as pd
from bs4 import BeautifulSoup

man = 35
mod = 10476


class VehicleScraper:
    def __init__(self, manufacturer=man, model=mod, max_pages=10,
                 min_delay=2.5, max_delay=5.5, verbose=False):
        self.manufacturer = manufacturer
        self.model = model
        self.max_pages = max_pages
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.verbose = verbose

        self.session = requests.Session()
        self.all_listings = []

        self.pages_attempted = 0
        self.pages_successful = 0
        self.stop_reason = ""

        # Headers to mimic a real browser
        self.headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "Cache-Control": "max-age=0",
            "Connection": "keep-alive",
            "DNT": "1",
            "Referer": "https://www.yad2.co.il/",
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/99.0.4844.74 Safari/537.36"
            ),
        }

        # logger (לא basicConfig כאן כדי לא "לנעול" את ההגדרות)
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO if self.verbose else logging.WARNING)

        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
            self.logger.addHandler(handler)
            self.logger.propagate = False  # כדי שלא יודפס כפול

    def build_url(self, page_num: int) -> str:
        base_url = "https://www.yad2.co.il/vehicles/cars"
        params = {
            "manufacturer": self.manufacturer,
            "model": self.model,
            "hand": "0-2",
            "page": page_num,
        }
        return f"{base_url}?{'&'.join(f'{k}={v}' for k, v in params.items())}"

    def extract_json_from_html(self, html_content: str):
        soup = BeautifulSoup(html_content, "html.parser")
        script_tag = soup.find("script", id="__NEXT_DATA__")
        if script_tag is None or not script_tag.string:
            self.logger.warning("Could not find __NEXT_DATA__ in HTML.")
            return None

        try:
            return json.loads(script_tag.string)
        except json.JSONDecodeError as e:
            self.logger.warning(f"JSON Decode Error: {e}")
            return None

    def _find_listings_data(self, next_data: dict):
        try:
            queries = next_data["props"]["pageProps"]["dehydratedState"]["queries"]
        except KeyError:
            return None

        wanted_categories = {"private", "commercial", "solo", "platinum"}

        for q in queries:
            data = (q.get("state") or {}).get("data")
            if isinstance(data, dict) and wanted_categories.intersection(data.keys()):
                return data

        return None

    def _safe_text(self, obj, path, default=""):
        cur = obj
        for k in path:
            if not isinstance(cur, dict):
                return default
            cur = cur.get(k)
            if cur is None:
                return default
        return cur if cur is not None else default

    # ✅ FIX: robust KM extraction from nested structures
    def _extract_km(self, item: dict):
        # common direct fields
        for key in ("km", "KM", "kilometers", "kilometres", "mileage"):
            if key in item and item.get(key) is not None:
                return item.get(key)

        # common nested containers
        for container in ("vehicle", "vehicleData", "vehicleDetails", "car", "metaData", "characteristics"):
            sub = item.get(container)
            if isinstance(sub, dict):
                for key in ("km", "KM", "kilometers", "kilometres", "mileage"):
                    if key in sub and sub.get(key) is not None:
                        return sub.get(key)

        # last resort: deep search up to a reasonable depth
        def deep_find(obj, depth=0, max_depth=6):
            if depth > max_depth:
                return None
            if isinstance(obj, dict):
                for k, v in obj.items():
                    if k in ("km", "KM", "kilometers", "kilometres", "mileage") and v is not None:
                        return v
                    found = deep_find(v, depth + 1, max_depth)
                    if found is not None:
                        return found
            elif isinstance(obj, list):
                for v in obj:
                    found = deep_find(v, depth + 1, max_depth)
                    if found is not None:
                        return found
            return None

        return deep_find(item)

    def fetch_page(self, page_num: int) -> bool:
        url = self.build_url(page_num)
        if self.verbose:
            self.logger.info(f"Fetching page {page_num}: {url}")

        try:
            time.sleep(random.uniform(self.min_delay, self.max_delay))
            resp = self.session.get(url, headers=self.headers, timeout=25, allow_redirects=True)
            resp.raise_for_status()

            if "__NEXT_DATA__" not in resp.text:
                self.logger.warning(f"Page {page_num} response seems incomplete (no __NEXT_DATA__).")
                return False

            next_data = self.extract_json_from_html(resp.text)
            if not next_data:
                return False

            listings_data = self._find_listings_data(next_data)
            if not listings_data:
                self.logger.warning(f"Could not locate listings data in page {page_num} payload.")
                return False

            for category in ["private", "commercial", "solo", "platinum"]:
                items = listings_data.get(category, [])
                if not isinstance(items, list):
                    continue

                for item in items:
                    dates = item.get("dates") or {}
                    vehicle_dates = item.get("vehicleDates") or {}

                    token = item.get("token")
                    link = f"https://www.yad2.co.il/vehicles/item/{token}" if token else ""

                    self.all_listings.append({
                        "Ad Number": item.get("adNumber"),
                        "Price (₪)": item.get("price"),
                        "City": self._safe_text(item, ["address", "city", "text"], ""),
                        "Model": self._safe_text(item, ["model", "text"], ""),
                        "SubModel": self._safe_text(item, ["subModel", "text"], ""),
                        "Production Year": vehicle_dates.get("yearOfProduction"),
                        "KM": self._extract_km(item),  # ✅ FIXED HERE
                        "Hand": self._safe_text(item, ["hand", "id"], ""),
                        "Listing Type": category,
                        "Created At": dates.get("createdAt"),
                        "Updated At": dates.get("updatedAt"),
                        "Description": self._safe_text(item, ["metaData", "description"], ""),
                        "Link": link
                    })

            return True

        except requests.exceptions.RequestException as e:
            self.logger.warning(f"Request error on page {page_num}: {e}")
            return False
        except Exception as e:
            self.logger.warning(f"Unexpected parsing error on page {page_num}: {e}")
            return False

    def scrape_pages(self):
        for page in range(1, self.max_pages + 1):
            self.pages_attempted += 1
            ok = self.fetch_page(page)

            if not ok:
                self.stop_reason = f"נעצר בעמוד {page} (תגובה לא מלאה / חסימה אפשרית)"
                break

            self.pages_successful += 1

        if not self.all_listings:
            if not self.stop_reason:
                self.stop_reason = "לא נמצאו מודעות"
            return None

        return pd.DataFrame(self.all_listings)


def run_scraper(manufacturer=35, model=10476, max_pages=10, verbose=False):
    scraper = VehicleScraper(
        manufacturer=manufacturer,
        model=model,
        max_pages=max_pages,
        verbose=verbose
    )

    df = scraper.scrape_pages()

    if df is None or df.empty:
        print(f"⚠️ לא נאספו מודעות. {scraper.stop_reason}")
        return df

    # שמירה לקובץ
    df.to_csv("yad2_scraped_data.csv", index=False, encoding="utf-8")

    # --- סיכום יפה בעברית, עם שם דגם מתוך הדאטה ---
    model_name = None
    if "Model" in df.columns:
        s = df["Model"].dropna()
        if not s.empty:
            model_name = s.mode().iloc[0]  # השם הנפוץ ביותר

    years = df.get("Production Year", pd.Series(dtype=float)).dropna()
    year_min = int(years.min()) if not years.empty else None
    year_max = int(years.max()) if not years.empty else None

    year_text = "לא ידוע"
    if year_min is not None and year_max is not None:
        year_text = str(year_min) if year_min == year_max else f"{year_min}-{year_max}"

    car_text = f"{model_name}" if model_name else f"(manufacturer={manufacturer}, model={model})"

    print(
        f"חיפשתי מכונית מסוג {car_text}, שנתון {year_text}. "
        f"סרקתי {scraper.pages_successful} עמודים (ניסיתי {scraper.pages_attempted}). "
        f"סה\"כ {len(df)} מודעות. "
        f"{('סיבה לעצירה: ' + scraper.stop_reason) if scraper.stop_reason else ''}"
    )
    print("✅ נשמר כקובץ yad2_scraped_data.csv")

    return df


