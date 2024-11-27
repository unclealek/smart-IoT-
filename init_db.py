from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, User, Device, SensorThreshold
import bcrypt

# Create database
engine = create_engine('sqlite:///smart_home.db')
Base.metadata.drop_all(engine)  # Reset database
Base.metadata.create_all(engine)

# Create session
Session = sessionmaker(bind=engine)
session = Session()

# Create test user if it doesn't exist
test_user = session.query(User).filter_by(username='test').first()
if not test_user:
    password = bcrypt.hashpw('test123'.encode('utf-8'), bcrypt.gensalt())
    test_user = User(username='test', password_hash=password)
    session.add(test_user)
    session.commit()

# Define sensor defaults for different room types
room_defaults = {
    'Living Room': {
        'temperature': ('22.0', '°C'),
        'humidity': ('45.0', '%'),
        'curtain': False,  # False = closed, True = open
        'camera': False    # False = off, True = on
    },
    'Outside': {
        'camera': False    # False = off, True = on
    },
    'Master Bedroom': {
        'temperature': ('21.0', '°C'),
        'humidity': ('40.0', '%'),
        'curtain': True  # Start with curtains open
    },
    'Kids Room': {  # Common settings for both kid rooms
        'temperature': ('21.5', '°C'),
        'humidity': ('42.0', '%'),
        'curtain': False  # Start with curtains closed
    }
}

# Define rooms and map them to their sensor defaults
rooms = {
    'Living Room': 'Living Room',
    'Outside': 'Outside',
    'Master Bedroom': 'Master Bedroom',
    'Kid1 Bedroom': 'Kids Room',  # Use Kids Room defaults
    'Kid2 Bedroom': 'Kids Room'   # Use Kids Room defaults
}

# Create devices for each room
for room_name, room_type in rooms.items():
    # Get defaults for this room type
    defaults = room_defaults[room_type]
    
    # Create camera for Living Room and Outside
    if room_name in ['Living Room', 'Outside']:
        camera_device = Device(
            name=f"{room_name} Camera",
            type='camera',
            state=defaults['camera'],  # True = on, False = off
            status='active',
            is_online=True,
            is_enabled=True,
            location=room_name,
            description=f"Security camera for {room_name}",
            user_id=test_user.id
        )
        session.add(camera_device)
        session.commit()
    
    # Skip other sensors for Outside area
    if room_name == 'Outside':
        continue
        
    # Create temperature sensor
    temp_device = Device(
        name=f"{room_name} Temperature Sensor",
        type='temperature',
        value=float(defaults['temperature'][0]),
        status='active',
        is_online=True,
        is_enabled=True,
        location=room_name,
        description=f"Temperature sensor for {room_name}",
        unit=defaults['temperature'][1],
        user_id=test_user.id
    )
    session.add(temp_device)
    session.commit()
    
    # Add temperature thresholds
    temp_threshold = SensorThreshold(
        device_id=temp_device.id,
        min_value=18.0,
        max_value=26.0,
        alert_enabled=True
    )
    session.add(temp_threshold)
    session.commit()
    
    # Create humidity sensor
    humid_device = Device(
        name=f"{room_name} Humidity Sensor",
        type='humidity',
        value=float(defaults['humidity'][0]),
        status='active',
        is_online=True,
        is_enabled=True,
        location=room_name,
        description=f"Humidity sensor for {room_name}",
        unit=defaults['humidity'][1],
        user_id=test_user.id
    )
    session.add(humid_device)
    session.commit()
    
    # Add humidity thresholds
    humid_threshold = SensorThreshold(
        device_id=humid_device.id,
        min_value=30.0,
        max_value=60.0,
        alert_enabled=True
    )
    session.add(humid_threshold)
    session.commit()
    
    # Create curtain control
    curtain_device = Device(
        name=f"{room_name} Curtain Control",
        type='curtain',
        state=defaults['curtain'],  # True = open, False = closed
        status='active',
        is_online=True,
        is_enabled=True,
        location=room_name,
        description=f"Curtain control for {room_name}",
        user_id=test_user.id
    )
    session.add(curtain_device)
    session.commit()

print("Database initialized with test data including cameras, kid bedrooms, and curtain controls!")
