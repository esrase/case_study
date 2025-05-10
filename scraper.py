import requests
from typing import List, Optional
from pydantic import BaseModel, HttpUrl, Field
import psycopg2
from datetime import datetime
from apscheduler.schedulers.blocking import BlockingScheduler
from tenacity import retry, stop_after_attempt, wait_fixed


class CampgroundAttributes(BaseModel):
    name: str
    latitude: float
    longitude: float
    region_name: str = Field(..., alias="region-name")
    bookable: Optional[bool]
    photos_count: int = Field(..., alias="photos-count")
    reviews_count: int = Field(..., alias="reviews-count")
    rating: Optional[float]


class CampgroundData(BaseModel):
    id: str
    type: str
    attributes: CampgroundAttributes


def insert_into_db(camp: CampgroundData):
    try:
        conn = psycopg2.connect(
            host="postgres",
            dbname="case_study",
            user="user",
            password="password",
            port=5432
        )
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO campgrounds (id, type, name, latitude, longitude, region_name, bookable, photos_count, reviews_count, rating)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
                name = EXCLUDED.name,
                latitude = EXCLUDED.latitude,
                longitude = EXCLUDED.longitude,
                region_name = EXCLUDED.region_name,
                bookable = EXCLUDED.bookable,
                photos_count = EXCLUDED.photos_count,
                reviews_count = EXCLUDED.reviews_count,
                rating = EXCLUDED.rating
        """, (
            camp.id,
            camp.type,
            camp.attributes.name,
            camp.attributes.latitude,
            camp.attributes.longitude,
            camp.attributes.region_name,
            camp.attributes.bookable,
            camp.attributes.photos_count,
            camp.attributes.reviews_count,
            camp.attributes.rating
        ))
        conn.commit()
        cursor.close()
        conn.close()
        print("✓", camp.attributes.name)
    except Exception as e:
        print(f"[ERROR] Veritabanı hatası: {e}")


def generate_us_bbox_grid(step=2.0):
    lat_min, lat_max = 24.396308, 49.384358
    lng_min, lng_max = -125.0, -66.93457

    grid = []
    lat = lat_min
    while lat < lat_max:
        lng = lng_min
        while lng < lng_max:
            grid.append((
                round(lng, 4), round(lat, 4),
                round(lng + step, 4), round(lat + step, 4)
            ))
            lng += step
        lat += step
    return grid


@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
def fetch_with_retry(url, headers, params):
    print(f"[INFO] API isteği: {params['filter[search][bbox]']}")
    response = requests.get(url, headers=headers, params=params, timeout=10)
    response.raise_for_status()
    return response


def fetch_all_us_campgrounds():
    bboxes = generate_us_bbox_grid(step=2.0)
    print(f"[INFO] Toplam {len(bboxes)} bbox işlenecek.")

    for i, (min_lng, min_lat, max_lng, max_lat) in enumerate(bboxes, start=1):
        bbox_str = f"{min_lng},{min_lat},{max_lng},{max_lat}"
        print(f"[{i}/{len(bboxes)}] → {bbox_str}")
        url = "https://thedyrt.com/api/v6/locations/search-results"
        params = {
            "filter[search][drive_time]": "any",
            "filter[search][air_quality]": "any",
            "filter[search][electric_amperage]": "any",
            "filter[search][max_vehicle_length]": "any",
            "filter[search][price]": "any",
            "filter[search][rating]": "any",
            "filter[search][bbox]": bbox_str,
            "sort": "recommended",
            "page[number]": 1,
            "page[size]": 500
        }
        headers = {"User-Agent": "Mozilla/5.0"}

        try:
            response = fetch_with_retry(url, headers, params)
            data = response.json().get("data", [])
            for item in data:
                try:
                    camp = CampgroundData(**item)
                    insert_into_db(camp)
                except Exception as ve:
                    print(f"[SKIP] Doğrulama hatası: {ve}")
        except Exception as e:
            print(f"[RETRY_FAILED] API hatası ({bbox_str}): {e}")


def scheduled_job():
    print(f"[SCHEDULED] Veri çekme işlemi başlatıldı: {datetime.utcnow()}")
    fetch_all_us_campgrounds()


def run():
    scheduler = BlockingScheduler()
    scheduler.add_job(scheduled_job, 'cron', hour=2, minute=0)  # Her gün 02:00 UTC
    print("[INFO] Zamanlayıcı başlatıldı. Her gün 02:00'de çalışacak.")
    scheduler.start()





