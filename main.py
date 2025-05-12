"""
Main entrypoint for The Dyrt web scraper case study.
- Manual run: python main.py
- API run: /run-scraper
- Scheduled run: every 12 hours via APScheduler
"""

from fastapi import FastAPI, Query, Request
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from scraper import fetch_all_us_campgrounds
from scraper_async import fetch_all_async
from logging_config import setup_logger
from apscheduler.schedulers.background import BackgroundScheduler
from db.models import Base, Campground
from db.session import engine, SessionLocal
import uvicorn
import os

# Veritabanı tabloları
Base.metadata.create_all(bind=engine)

logger = setup_logger()
app = FastAPI()

# Jinja2 templates ayarı
templates = Jinja2Templates(directory="templates")

# Statik dosyalar için mount
if os.path.isdir("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def render_map(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/campgrounds-json")
def get_campgrounds_json(
    min_rating: float = Query(default=4.0, description="Minimum puan")
):
    db = SessionLocal()
    try:
        query = db.query(Campground).filter(Campground.rating >= min_rating)
        results = query.all()
        data = [
            {
                "id": c.id,
                "name": c.name,
                "latitude": c.latitude,
                "longitude": c.longitude,
                "rating": c.rating,
                "region": c.region_name
            }
            for c in results
        ]
        return JSONResponse(content=data)
    except Exception as e:
        logger.error(f"Campground JSON API hatası: {e}")
        return JSONResponse(status_code=500, content={"error": "Veriler alınamadı."})
    finally:
        db.close()

@app.get("/run-scraper")
def run_scraper():
    logger.info("Manuel HTTP tetikleme: /run-scraper")
    fetch_all_us_campgrounds()
    return {"message": "Scraper başarıyla çalıştı."}

@app.get("/run-async-scraper")
async def run_async_scraper():
    logger.info("Manuel HTTP tetikleme: /run-async-scraper")
    await fetch_all_async()
    return {"message": "Async scraper başarıyla çalıştı."}

# Otomatik scraper her 12 saatte bir çalışır
scheduler = BackgroundScheduler()
scheduler.add_job(fetch_all_us_campgrounds, "interval", hours=12)
scheduler.start()

if __name__ == "__main__":
    logger.info("Manuel komut satırı tetikleme başladı")
    uvicorn.run("main:app", host="0.0.0.0", port=8000)














