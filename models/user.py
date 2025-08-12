from sqlalchemy import Column, Integer, String
from models.database import Base

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False)
    name = Column(String(255))
    profile_pic = Column(String(255))
    google_id = Column(String(64), unique=True)