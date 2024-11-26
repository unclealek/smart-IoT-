# Smart Home Monitoring System

A modern IoT device monitoring system built with Flet, featuring user authentication and device monitoring capabilities.

## Features

- User Authentication (Login/Register)
- Secure password hashing with bcrypt
- Dark mode UI
- IoT Device monitoring dashboard
- Responsive grid layout for devices
- Real-time device status updates

## Requirements

- Python 3.7+
- Flet
- bcrypt

## Installation

1. Install the required packages:
```bash
pip install -r requirements.txt
```

2. Run the application:
```bash
python main.py
```

## Usage

1. Register a new account using the registration form
2. Login with your credentials
3. View and monitor your IoT devices on the dashboard
4. Use the logout button when finished

## Device Types Currently Supported

- Temperature sensors
- Humidity sensors
- Security cameras
- Smart lights

## Note

This is a demo version with mock IoT devices. To connect real IoT devices, you'll need to modify the `devices` list in the `setup_home_view` method with your actual IoT device data.
# smart-IoT-
