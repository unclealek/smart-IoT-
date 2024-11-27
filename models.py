from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

# Create a configured "Session" class
engine = create_engine('sqlite:///smart_home.db')
Base = declarative_base()

class Device(Base):
    __tablename__ = 'devices'
    
    id = Column(Integer, primary_key=True)
    name = Column(String)
    type = Column(String)
    mqtt_topic = Column(String)
    location = Column(String)
    description = Column(String)
    unit = Column(String)
    state = Column(Boolean, default=False)
    readings = relationship("SensorReading", back_populates="device")
    threshold = relationship("SensorThreshold", back_populates="device", uselist=False)
    user_id = Column(Integer, ForeignKey('users.id'))
    user = relationship("User", back_populates="devices")

class SensorReading(Base):
    __tablename__ = 'sensor_readings'
    
    id = Column(Integer, primary_key=True)
    device_id = Column(Integer, ForeignKey('devices.id'))
    value = Column(Float)
    timestamp = Column(DateTime, default=datetime.now)
    device = relationship("Device", back_populates="readings")

class SensorThreshold(Base):
    __tablename__ = 'sensor_thresholds'
    
    id = Column(Integer, primary_key=True)
    device_id = Column(Integer, ForeignKey('devices.id'), unique=True)
    min_value = Column(Float, nullable=True)
    max_value = Column(Float, nullable=True)
    alert_enabled = Column(Boolean, default=False)
    device = relationship("Device", back_populates="threshold")

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True)
    password_hash = Column(String)
    devices = relationship("Device", back_populates="user")

# Create all tables in the engine
Base.metadata.create_all(engine)

# Create a configured "Session" class
Session = sessionmaker(bind=engine)

def get_session():
    return Session()
