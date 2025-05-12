# models.py
from sqlalchemy import Column, String, DateTime
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Shop(Base):
    __tablename__ = "shops"
    shop_id      = Column(String, primary_key=True)
    shop_url     = Column(String, nullable=False)
    shop_secret  = Column(String, nullable=False)
    sw_version   = Column(String, nullable=True)
    api_key      = Column(String, nullable=True)
    secret_key   = Column(String, nullable=True)
    confirmed_at = Column(DateTime, nullable=True)
