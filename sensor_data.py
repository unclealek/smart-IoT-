from datetime import datetime, timedelta
import matplotlib
matplotlib.use('Agg')  # Set the backend before importing pyplot
import matplotlib.pyplot as plt
import numpy as np
import io
import base64
import logging
from models import SensorReading, SensorThreshold

# Set up logging
logging.basicConfig(level=logging.INFO)

def generate_dummy_data(device_id, hours=48):
    """Generate dummy sensor readings for testing"""
    end_time = datetime.now()
    start_time = end_time - timedelta(hours=hours)
    
    # Generate timestamps every 5 minutes
    timestamps = []
    current = start_time
    while current <= end_time:
        timestamps.append(current)
        current += timedelta(minutes=5)
    
    # Generate random values with a realistic pattern
    base_value = 22.0  # Base temperature for temperature sensors
    if "humidity" in str(device_id).lower():
        base_value = 45.0  # Base humidity for humidity sensors
    
    # Add daily pattern and some random noise
    values = []
    for ts in timestamps:
        hour = ts.hour
        # Daily pattern: lower at night, higher during day
        daily_pattern = 2 * np.sin(2 * np.pi * (hour - 6) / 24)
        noise = np.random.normal(0, 0.5)
        value = base_value + daily_pattern + noise
        values.append(round(value, 1))
    
    return timestamps, values

def create_chart_image(timestamps, values, device_type="temperature", threshold=None):
    """Create a matplotlib chart and return it as a base64 encoded image"""
    logging.info(f"Creating chart with {len(timestamps)} data points")
    
    # Clear any existing plots
    plt.clf()
    
    # Create figure and axis objects with a single subplot
    fig, ax = plt.subplots(figsize=(12, 6))
    
    # Calculate marker frequency based on number of points
    # Show markers every N points to avoid overcrowding
    n_points = len(timestamps)
    marker_frequency = max(1, n_points // 20)  # Show about 20 markers
    
    # Plot the main line with markers
    line = ax.plot(timestamps, values, 'b-', label='Sensor Reading', linewidth=2)[0]
    markers = ax.plot(timestamps[::marker_frequency], values[::marker_frequency], 
                     'bo', markersize=6, alpha=0.7)[0]
    
    # Add annotations for marker points
    for i in range(0, len(timestamps), marker_frequency):
        # Format value with one decimal place
        value_text = f"{values[i]:.1f}"
        if device_type == "temperature":
            value_text += "°C"
        elif device_type == "humidity":
            value_text += "%"
            
        # Add annotation slightly above the point
        ax.annotate(value_text,
                   (timestamps[i], values[i]),
                   xytext=(0, 10),
                   textcoords='offset points',
                   ha='center',
                   va='bottom',
                   fontsize=8,
                   bbox=dict(boxstyle='round,pad=0.5', fc='white', ec='gray', alpha=0.7))
    
    # Add threshold lines if they exist
    if threshold:
        if threshold.max_value is not None:
            ax.axhline(y=threshold.max_value, color='r', linestyle='--', label='Max Threshold')
            ax.annotate(f'Max: {threshold.max_value}', 
                       xy=(timestamps[0], threshold.max_value),
                       xytext=(10, 10),
                       textcoords='offset points',
                       color='red',
                       bbox=dict(boxstyle='round,pad=0.5', fc='white', ec='red', alpha=0.7))
        if threshold.min_value is not None:
            ax.axhline(y=threshold.min_value, color='g', linestyle='--', label='Min Threshold')
            ax.annotate(f'Min: {threshold.min_value}',
                       xy=(timestamps[0], threshold.min_value),
                       xytext=(10, -20),
                       textcoords='offset points',
                       color='green',
                       bbox=dict(boxstyle='round,pad=0.5', fc='white', ec='green', alpha=0.7))
    
    # Customize the chart
    ax.grid(True, linestyle='--', alpha=0.7)
    ax.set_title(f'{device_type.capitalize()} Readings Over Time', pad=20)
    ax.set_xlabel('Time')
    
    if device_type == "temperature":
        ax.set_ylabel('Temperature (°C)')
    elif device_type == "humidity":
        ax.set_ylabel('Humidity (%)')
    else:
        ax.set_ylabel('Value')
    
    # Format x-axis
    plt.gcf().autofmt_xdate()  # Rotate and align the tick labels
    
    # Add legend
    ax.legend()
    
    # Adjust layout to prevent label cutoff
    plt.tight_layout()
    
    # Convert plot to base64 string
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
    plt.close('all')  # Close all figures
    
    buffer.seek(0)
    image_png = buffer.getvalue()
    buffer.close()
    
    graphic = base64.b64encode(image_png).decode()
    
    return graphic

def get_recent_readings(session, device_id, hours=48):
    """Get recent readings or generate dummy data if no readings exist"""
    since = datetime.now() - timedelta(hours=hours)
    readings = session.query(SensorReading).filter(
        SensorReading.device_id == device_id,
        SensorReading.timestamp >= since
    ).order_by(SensorReading.timestamp.desc()).all()
    
    if not readings:
        logging.info(f"No readings found for device {device_id}, generating dummy data...")
        # Generate and return dummy data
        timestamps, values = generate_dummy_data(device_id, hours)
        logging.info(f"Generated {len(timestamps)} dummy readings")
        logging.info(f"Sample values: {values[:5]}")
        
        dummy_readings = []
        for ts, val in zip(timestamps, values):
            reading = SensorReading(
                device_id=device_id,
                value=val,
                timestamp=ts
            )
            dummy_readings.append(reading)
        return dummy_readings
    
    logging.info(f"Found {len(readings)} real readings")
    return readings
