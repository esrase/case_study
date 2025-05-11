import requests
from typing import Optional
from pydantic import BaseModel, Field
from apscheduler.schedulers.blocking import BlockingScheduler
from tenacity import retry, stop_after_attempt, wait_fixed

from db.session import SessionLocal
from db.models import Campground as CampgroundORM
from logging_config import setup_logger

logger = setup_logger()


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
    session = SessionLocal()
    try:
        existing = session.query(CampgroundORM).filter_by(id=camp.id).first()
        if existing:
            existing.name = camp.attributes.name
            existing.latitude = camp.attributes.latitude
            existing.longitude = camp.attributes.longitude
            existing.region_name = camp.attributes.region_name
            existing.bookable = camp.attributes.bookable
            existing.photos_count = camp.attributes.photos_count
            existing.reviews_count = camp.attributes.reviews_count
            existing.rating = camp.attributes.rating
        else:
            new_camp = CampgroundORM(
                id=camp.id,
                type=camp.type,
                name=camp.attributes.name,
                latitude=camp.attributes.latitude,
                longitude=camp.attributes.longitude,
                region_name=camp.attributes.region_name,
                bookable=camp.attributes.bookable,
                photos_count=camp.attributes.photos_count,
                reviews_count=camp.attributes.reviews_count,
                rating=camp.attributes.rating
            )
            session.add(new_camp)
        session.commit()
        logger.info(f"✓ {camp.attributes.name}")
    except Exception as e:
        logger.error(f"DB Hatası: {e}")
        session.rollback()
    finally:
        session.close()


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
    logger.info(f"API isteği: {params['filter[search][bbox]']}")
    response = requests.get(url, headers=headers, params=params, timeout=10)
    response.raise_for_status()
    return response


def fetch_all_us_campgrounds():
    logger.info("🚀 Logger test mesajı: Scraper başlatıldı")
    bboxes = generate_us_bbox_grid(step=2.0)
    logger.info(f"Toplam {len(bboxes)} bbox işlenecek.")

    for i, (min_lng, min_lat, max_lng, max_lat) in enumerate(bboxes, start=1):
        bbox_str = f"{min_lng},{min_lat},{max_lng},{max_lat}"
        logger.info(f"[{i}/{len(bboxes)}] → {bbox_str}")
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
                    logger.warning(f"Doğrulama hatası: {ve}")
        except Exception as e:
            logger.error(f"API hatası ({bbox_str}): {e}")


def scheduled_job():
    from datetime import datetime
    logger.info(f"[SCHEDULED] Veri çekme işlemi başlatıldı: {datetime.utcnow()}")
    fetch_all_us_campgrounds()


def run():
    scheduler = BlockingScheduler()
    scheduler.add_job(scheduled_job, 'cron', hour=2, minute=0)
    logger.info("Zamanlayıcı başlatıldı. Her gün 02:00'de çalışacak.")
    scheduler.start()












