import paho.mqtt.client as mqtt
import json
from datetime import datetime
from models import get_session, Device
import os
from dotenv import load_dotenv

load_dotenv()

class MQTTClient:
    def __init__(self, callback=None):
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.callback = callback
        
        # Get MQTT credentials from environment variables
        self.mqtt_broker = os.getenv('MQTT_BROKER', 'localhost')
        self.mqtt_port = int(os.getenv('MQTT_PORT', 1883))
        self.mqtt_username = os.getenv('MQTT_USERNAME')
        self.mqtt_password = os.getenv('MQTT_PASSWORD')

    def connect(self):
        if self.mqtt_username and self.mqtt_password:
            self.client.username_pw_set(self.mqtt_username, self.mqtt_password)
        
        self.client.connect(self.mqtt_broker, self.mqtt_port, 60)
        self.client.loop_start()

    def disconnect(self):
        self.client.loop_stop()
        self.client.disconnect()

    def on_connect(self, client, userdata, flags, rc):
        print(f"Connected with result code {rc}")
        # Subscribe to all device topics
        client.subscribe("home/#")

    def on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())
            topic = msg.topic
            
            # Update device in database
            session = get_session()
            device = session.query(Device).filter_by(mqtt_topic=topic).first()
            
            if device:
                device.value = str(payload.get('value', ''))
                device.status = payload.get('status', 'Unknown')
                device.is_online = True
                device.last_updated = datetime.now()
                session.commit()
                
                # Notify UI if callback is provided
                if self.callback:
                    self.callback(device)
            
            session.close()
            
        except Exception as e:
            print(f"Error processing message: {e}")

    def publish(self, topic, message):
        """Publish a message to a specific topic"""
        self.client.publish(topic, json.dumps(message))
