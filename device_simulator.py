import paho.mqtt.client as mqtt
import json
import random
import time
from datetime import datetime
import threading

class DeviceSimulator:
    def __init__(self):
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        
        # Device states
        self.devices = {
            # Temperature sensors
            "home/living_room/temperature": {"value": 22.0, "type": "temperature", "unit": "°C"},
            "home/kitchen/temperature": {"value": 23.0, "type": "temperature", "unit": "°C"},
            "home/master_bedroom/temperature": {"value": 21.5, "type": "temperature", "unit": "°C"},
            "home/kid1_bedroom/temperature": {"value": 22.0, "type": "temperature", "unit": "°C"},
            "home/kid2_bedroom/temperature": {"value": 21.8, "type": "temperature", "unit": "°C"},
            
            # Humidity sensors
            "home/living_room/humidity": {"value": 45.0, "type": "humidity", "unit": "%"},
            "home/kitchen/humidity": {"value": 48.0, "type": "humidity", "unit": "%"},
            "home/master_bedroom/humidity": {"value": 46.0, "type": "humidity", "unit": "%"},
            
            # Cameras
            "home/living_room/camera": {"value": "Active", "type": "camera", "motion_detected": False},
            "home/outside/camera": {"value": "Active", "type": "camera", "motion_detected": False},
             
            # Lights
            "home/living_room/light": {"value": "OFF", "type": "light"},
            "home/kitchen/light": {"value": "OFF", "type": "light"},
            "home/master_bedroom/light": {"value": "OFF", "type": "light"},
            "home/kid1_bedroom/light": {"value": "OFF", "type": "light"},
            "home/kid2_bedroom/light": {"value": "OFF", "type": "light"},
            
            # Curtains
            "home/living_room/curtain": {"value": "50", "type": "curtain", "unit": "%"},
            
            # Doors
            "home/entrance/door": {"value": "LOCKED", "type": "door"},
            "home/back/door": {"value": "LOCKED", "type": "door"}
        }
        
        # Subscribe to control topics
        self.control_topics = [topic + "/control" for topic in self.devices.keys()]

    def on_connect(self, client, userdata, flags, rc):
        print(f"Connected with result code {rc}")
        # Subscribe to all control topics
        for topic in self.control_topics:
            client.subscribe(topic)
            print(f"Subscribed to {topic}")

    def on_message(self, client, userdata, msg):
        try:
            # Extract base topic (remove /control)
            base_topic = msg.topic.replace("/control", "")
            if base_topic in self.devices:
                payload = json.loads(msg.payload.decode())
                command = payload.get("command")
                
                if command:
                    self.handle_command(base_topic, command)
                    
        except Exception as e:
            print(f"Error handling message: {e}")

    def handle_command(self, topic, command):
        device = self.devices[topic]
        
        if device["type"] == "light":
            if command in ["ON", "OFF"]:
                device["value"] = command
                
        elif device["type"] == "curtain":
            if command == "OPEN":
                device["value"] = "100"
            elif command == "CLOSE":
                device["value"] = "0"
            elif command.startswith("SET"):
                try:
                    value = int(command.split(":")[1])
                    if 0 <= value <= 100:
                        device["value"] = str(value)
                except:
                    pass
                
        elif device["type"] == "door":
            if command in ["LOCK", "UNLOCK"]:
                device["value"] = "LOCKED" if command == "LOCK" else "UNLOCKED"
        
        # Publish updated state
        self.publish_state(topic)

    def simulate_sensors(self):
        while True:
            for topic, device in self.devices.items():
                if device["type"] == "temperature":
                    # Simulate temperature changes
                    current = float(device["value"])
                    device["value"] = round(current + random.uniform(-0.3, 0.3), 1)
                    
                elif device["type"] == "humidity":
                    # Simulate humidity changes
                    current = float(device["value"])
                    device["value"] = round(current + random.uniform(-1, 1), 1)
                    
                elif device["type"] == "camera":
                    # Simulate random motion detection
                    if random.random() < 0.1:  # 10% chance of motion
                        device["motion_detected"] = True
                        device["value"] = "Motion Detected"
                    else:
                        device["motion_detected"] = False
                        device["value"] = "Active"
                
                self.publish_state(topic)
            
            # Wait before next update
            time.sleep(5)

    def publish_state(self, topic):
        device = self.devices[topic]
        message = {
            "value": str(device["value"]),
            "status": "Online",
            "timestamp": datetime.now().isoformat()
        }
        
        if device["type"] == "camera" and device["motion_detected"]:
            message["alert"] = "Motion detected!"
            
        self.client.publish(topic, json.dumps(message))

    def run(self):
        # Connect to MQTT broker
        self.client.connect("localhost", 1883, 60)
        
        # Start sensor simulation in a separate thread
        simulator_thread = threading.Thread(target=self.simulate_sensors)
        simulator_thread.daemon = True
        simulator_thread.start()
        
        # Start MQTT loop
        self.client.loop_forever()

if __name__ == "__main__":
    simulator = DeviceSimulator()
    print("Starting device simulator...")
    simulator.run()
