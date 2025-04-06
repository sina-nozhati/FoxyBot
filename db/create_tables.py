#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import logging
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# اضافه کردن مسیر پروژه به سیستم 
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config import DATABASE_URL
from db.models import Base

# تنظیمات لاگینگ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def create_tables():
    """ایجاد جداول دیتابیس"""
    try:
        # ایجاد موتور دیتابیس
        engine = create_engine(DATABASE_URL)
        
        # ایجاد جداول
        logger.info("Creating database tables...")
        Base.metadata.create_all(engine)
        
        # تست دیتابیس
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()
        connection = session.connection()
        session.close()
        
        logger.info("Database tables created successfully!")
        return True
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")
        return False

if __name__ == "__main__":
    create_tables() 