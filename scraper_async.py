import asyncio
import aiohttp
from db.session import SessionLocal
from db.models import Campground as CampgroundORM
from pydantic import BaseModel, Field
from typing import Optional
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
            existing.rating = camp.attributes.rating or 0.0
        else:
            session.add(CampgroundORM(
                id=camp.id,
                type=camp.type,
                name=camp.attributes.name,
                latitude=camp.attributes.latitude,
                longitude=camp.attributes.longitude,
                region_name=camp.attributes.region_name,
                bookable=camp.attributes.bookable,
                photos_count=camp.attributes.photos_count,
                reviews_count=camp.attributes.reviews_count,
                rating=camp.attributes.rating or 0.0
            ))
        session.commit()
    except Exception as e:
        logger.error(f"DB hatası: {e}")
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
            grid.append((round(lng, 4), round(lat, 4), round(lng + step, 4), round(lat + step, 4)))
            lng += step
        lat += step
    return grid

async def fetch_bbox(session, bbox_str):
    url = "https://thedyrt.com/api/v6/locations/search-results"
    params = {
        "filter[search][bbox]": bbox_str,
        "page[number]": 1,
        "page[size]": 500
    }
    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        async with session.get(url, params=params, headers=headers) as response:
            if response.status == 200:
                json_data = await response.json()
                for item in json_data.get("data", []):
                    try:
                        camp = CampgroundData(**item)
                        insert_into_db(camp)
                    except Exception as ve:
                        logger.warning(f"Veri doğrulama hatası: {ve}")
            else:
                logger.warning(f"BBOX {bbox_str} - HTTP hata: {response.status}")
    except Exception as e:
        logger.error(f"BBOX {bbox_str} - İstek hatası: {e}")

async def fetch_all_async():
    logger.info("🚀 Async scraper başlatıldı.")
    bboxes = generate_us_bbox_grid()
    async with aiohttp.ClientSession() as session:
        await asyncio.gather(*[fetch_bbox(session, f"{x1},{y1},{x2},{y2}") for (x1, y1, x2, y2) in bboxes])


        


