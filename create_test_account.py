import bcrypt
from models import get_session, User, Device
from datetime import datetime

def create_test_account():
    session = get_session()
    
    # Check if test account already exists
    existing_user = session.query(User).filter_by(username="test").first()
    if existing_user:
        print("Test account already exists!")
        return
    
    # Create test user
    password = "test123"
    password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    
    test_user = User(
        username="test",
        password_hash=password_hash
    )
    session.add(test_user)
    session.flush()  # To get the user ID
    
    # Create some test devices
    devices = [
        {
            "name": "Living Room Temperature",
            "type": "temperature",
            "value": "22.5",
            "status": "Normal",
            "unit": "°C",
            "location": "Living Room",
            "description": "Temperature sensor",
            "mqtt_topic": "home/livingroom/temperature"
        },
        {
            "name": "Kitchen Humidity",
            "type": "humidity",
            "value": "45",
            "status": "Normal",
            "unit": "%",
            "location": "Kitchen",
            "description": "Humidity sensor",
            "mqtt_topic": "home/kitchen/humidity"
        }
    ]
    
    for device_data in devices:
        device = Device(
            user_id=test_user.id,
            last_updated=datetime.now(),
            **device_data
        )
        session.add(device)
    
    session.commit()
    print("Test account created successfully!")
    print("Username: test")
    print("Password: test123")

if __name__ == "__main__":
    create_test_account()
