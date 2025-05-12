from sqlalchemy import Column, String, Float, Integer, Boolean
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Campground(Base):
    __tablename__ = "campgrounds"

    id = Column(String, primary_key=True)
    type = Column(String, nullable=False)
    name = Column(String, nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    region_name = Column(String, nullable=False)
    bookable = Column(Boolean)
    photos_count = Column(Integer)
    reviews_count = Column(Integer)
    rating = Column(Float)
    






