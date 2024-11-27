import flet as ft
import bcrypt
from datetime import datetime, timedelta
from models import get_session, User, Device
from mqtt_client import MQTTClient
from sensor_data import SensorReading, SensorThreshold
from sensor_details import SensorDetailsView
import json
import random

class SmartHomeApp:
    def __init__(self):
        self.session = get_session()
        self.current_user = None
        self.mqtt_client = None
        
    def initialize(self, page: ft.Page):
        self.page = page
        self.page.title = "Smart Home Dashboard"
        self.page.theme_mode = ft.ThemeMode.LIGHT
        self.page.padding = 20
        self.page.spacing = 20
        
        self.setup_auth_views()
        self.show_login()

    def setup_auth_views(self):
        # Login View
        self.username_login = ft.TextField(
            label="Username",
            width=300,
            border_color=ft.colors.BLUE_400
        )
        self.password_login = ft.TextField(
            label="Password",
            password=True,
            can_reveal_password=True,
            width=300,
            border_color=ft.colors.BLUE_400
        )
        self.login_view = ft.Column(
            controls=[
                ft.Text("Welcome Back!", size=32, weight=ft.FontWeight.BOLD),
                ft.Text("Login to your Smart Home Dashboard", size=16, color=ft.colors.GREY_400),
                self.username_login,
                self.password_login,
                ft.ElevatedButton(
                    text="Login",
                    width=300,
                    on_click=self.handle_login
                ),
                ft.TextButton(
                    text="Don't have an account? Register",
                    on_click=lambda _: self.show_register()
                )
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=20
        )

        # Register View
        self.username_register = ft.TextField(
            label="Username",
            width=300,
            border_color=ft.colors.BLUE_400
        )
        self.password_register = ft.TextField(
            label="Password",
            password=True,
            can_reveal_password=True,
            width=300,
            border_color=ft.colors.BLUE_400
        )
        self.confirm_password = ft.TextField(
            label="Confirm Password",
            password=True,
            can_reveal_password=True,
            width=300,
            border_color=ft.colors.BLUE_400
        )
        self.register_view = ft.Column(
            controls=[
                ft.Text("Create Account", size=32, weight=ft.FontWeight.BOLD),
                ft.Text("Register for Smart Home Access", size=16, color=ft.colors.GREY_400),
                self.username_register,
                self.password_register,
                self.confirm_password,
                ft.ElevatedButton(
                    text="Register",
                    width=300,
                    on_click=self.handle_register
                ),
                ft.TextButton(
                    text="Already have an account? Login",
                    on_click=lambda _: self.show_login()
                )
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=20
        )

    def create_device_card(self, device):
        def on_card_click(e):
            details_view = SensorDetailsView(self.page, device, self.session, lambda _: self.show_home())
            self.page.clean()
            self.page.add(details_view.build())

        def on_switch_change(e):
            try:
                # Update device state
                device.state = e.control.value
                self.session.commit()

                # Prepare MQTT message based on device type
                mqtt_message = {
                    "state": "ON" if device.state else "OFF"
                }

                # Add device-specific commands
                if device.type == "light":
                    mqtt_message["command"] = "ON" if device.state else "OFF"
                elif device.type == "curtain":
                    mqtt_message["command"] = "OPEN" if device.state else "CLOSE"
                elif device.type == "door":
                    mqtt_message["command"] = "UNLOCK" if device.state else "LOCK"
                elif device.type == "camera":
                    mqtt_message["command"] = "START" if device.state else "STOP"

                # Publish MQTT message
                if self.mqtt_client:
                    self.mqtt_client.publish(
                        f"device/{device.id}/control",
                        json.dumps(mqtt_message)
                    )

                # Update UI to reflect new state
                e.control.value = device.state
                e.control.update()

                # Show success message
                self.page.show_snack_bar(
                    ft.SnackBar(
                        content=ft.Text(f"{device.name} turned {'on' if device.state else 'off'}")
                    )
                )
            except Exception as err:
                print(f"Error changing device state: {err}")
                # Revert switch state on error
                e.control.value = not e.control.value
                e.control.update()
                self.page.show_snack_bar(
                    ft.SnackBar(
                        content=ft.Text(f"Error changing {device.name} state: {str(err)}")
                    )
                )

        # Create the icon based on device type
        icon_map = {
            "temperature": ft.icons.THERMOSTAT,
            "humidity": ft.icons.WATER_DROP,
            "camera": ft.icons.VIDEOCAM,
            "light": ft.icons.LIGHTBULB,
            "door": ft.icons.DOOR_SLIDING,
            "curtain": ft.icons.BLINDS,
        }

        # Get current device state
        device_state = False
        if hasattr(device, 'state'):
            if isinstance(device.state, bool):
                device_state = device.state
            elif isinstance(device.state, str):
                device_state = device.state.lower() in ['true', '1', 't', 'y', 'yes', 'on']

        # Create the main content column
        main_content = ft.Column(
            controls=[
                # Icon container with increased size
                ft.Container(
                    content=ft.Icon(
                        icon_map.get(device.type, ft.icons.DEVICE_UNKNOWN),
                        size=32,  # Increased from 24
                        color=ft.colors.BLUE_400,
                    ),
                    margin=ft.margin.only(bottom=10),  # Increased from 5
                ),
                # Device name with increased size
                ft.Text(
                    device.name,
                    size=18,  # Increased from 16
                    weight=ft.FontWeight.BOLD,
                    text_align=ft.TextAlign.CENTER,
                ),
                # Device type with adjusted size
                ft.Text(
                    device.type.capitalize(),
                    size=14,  # Increased from 12
                    color=ft.colors.GREY_400,
                    text_align=ft.TextAlign.CENTER,
                ),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=8,  # Increased from 5
        )

        # Add status or control based on device type
        status_control = None
        if device.type in ["temperature", "humidity"]:
            # Get latest reading
            latest_reading = (
                self.session.query(SensorReading)
                .filter_by(device_id=device.id)
                .order_by(SensorReading.timestamp.desc())
                .first()
            )
            if latest_reading:
                # Create value display with large text
                status_control = ft.Column(
                    controls=[
                        ft.Text(
                            f"{latest_reading.value:.1f}",
                            size=32,  # Increased from 24
                            weight=ft.FontWeight.BOLD,
                            color=ft.colors.BLUE_400,
                            text_align=ft.TextAlign.CENTER,
                        ),
                        ft.Text(
                            device.unit,
                            size=16,  # Increased from 14
                            color=ft.colors.GREY_400,
                            text_align=ft.TextAlign.CENTER,
                        )
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=4,  # Increased from 2
                )
            else:
                status_control = ft.Text(
                    "No data",
                    size=24,  # Increased from 20
                    color=ft.colors.GREY_400,
                    text_align=ft.TextAlign.CENTER,
                )
        elif device.type in ["light", "camera", "door", "curtain"]:
            status_control = ft.Switch(
                value=device_state,
                active_color=ft.colors.BLUE_400,
                inactive_thumb_color=ft.colors.GREY_400,
                on_change=on_switch_change,
                scale=1.2,  # Added scale to make switch bigger
            )

        if status_control:
            main_content.controls.append(
                ft.Container(
                    content=status_control,
                    margin=ft.margin.only(top=10),  # Increased from 5
                )
            )

        # Create the card content with dynamic sizing
        card_content = ft.Container(
            content=main_content,
            padding=ft.padding.all(25),
            alignment=ft.alignment.center,
            expand=True,  # Allow content to expand
        )

        # Create the card with consistent styling
        card = ft.Card(
            content=card_content,
            elevation=3,
            surface_tint_color=ft.colors.BLUE_50,
        )

        # Wrap all cards in a container for consistent sizing
        card_container = ft.Container(
            content=card,
            margin=ft.margin.all(5),
            padding=ft.padding.all(5),
            expand=True,
            ink=True if device.type in ["temperature", "humidity"] else False,
            on_click=on_card_click if device.type in ["temperature", "humidity"] else None,
            bgcolor=ft.colors.TRANSPARENT,
            border_radius=12,
            # Set minimum size using width/height
            width=200,
            height=150,
        )

        return card_container

    def generate_dummy_readings(self):
        """Generate 24 hours of dummy readings for temperature and humidity sensors"""
        from datetime import datetime, timedelta
        import random

        # Get all temperature and humidity sensors
        sensors = (
            self.session.query(Device)
            .filter(Device.type.in_(["temperature", "humidity"]))
            .all()
        )

        # Generate readings for each sensor
        for sensor in sensors:
            # Delete existing readings
            self.session.query(SensorReading).filter_by(device_id=sensor.id).delete()
            
            # Generate 24 readings, one for each hour
            base_time = datetime.now() - timedelta(hours=24)
            base_value = 22 if sensor.type == "temperature" else 50  # Base temperature or humidity
            
            for hour in range(24):
                timestamp = base_time + timedelta(hours=hour)
                # Add some random variation
                if sensor.type == "temperature":
                    value = base_value + random.uniform(-2, 2)  # Temperature varies by ±2°C
                else:
                    value = base_value + random.uniform(-10, 10)  # Humidity varies by ±10%
                
                reading = SensorReading(
                    device_id=sensor.id,
                    value=round(value, 1),
                    timestamp=timestamp
                )
                self.session.add(reading)
        
        self.session.commit()

    def setup_home_view(self):
        # Get user's devices from database
        devices = self.session.query(Device).filter_by(user_id=self.current_user.id).all()
        
        # Generate dummy readings if none exist
        readings_count = self.session.query(SensorReading).count()
        if readings_count == 0:
            self.generate_dummy_readings()
        
        # Group devices by location
        devices_by_location = {}
        for device in devices:
            if device.location not in devices_by_location:
                devices_by_location[device.location] = []
            devices_by_location[device.location].append(device)

        # Create the main container
        main_column = ft.Column(
            scroll=ft.ScrollMode.AUTO,
            spacing=20,
            expand=True
        )

        # Add search bar
        search_bar = ft.TextField(
            prefix_icon=ft.icons.SEARCH,
            hint_text="Search devices...",
            border_radius=20,
            expand=True,
            height=45,
            border_color=ft.colors.BLUE_400,
        )
        
        # Add view toggle
        view_toggle = ft.IconButton(
            icon=ft.icons.GRID_VIEW,
            tooltip="Toggle view",
            icon_color=ft.colors.BLUE_400,
        )
        
        # Top bar with search and controls
        top_bar = ft.Container(
            content=ft.Row(
                controls=[
                    search_bar,
                    view_toggle,
                    ft.IconButton(
                        icon=ft.icons.ADD,
                        tooltip="Add Device",
                        icon_color=ft.colors.BLUE_400,
                        on_click=self.show_add_device_dialog
                    ),
                ],
                spacing=10,
            ),
            padding=ft.padding.only(bottom=20)
        )
        main_column.controls.append(top_bar)

        # Add devices grouped by location
        for location in sorted(devices_by_location.keys()):
            # Create location section
            location_devices = devices_by_location[location]
            
            # Create grid for location's devices
            location_grid = ft.GridView(
                expand=1,
                max_extent=250,
                spacing=15,
                run_spacing=15,
                padding=15,
            )
            
            # Add devices to grid
            for device in location_devices:
                location_grid.controls.append(self.create_device_card(device))
            
            # Add location section to main column
            main_column.controls.extend([
                ft.Container(
                    content=ft.Text(
                        location,
                        size=20,
                        weight=ft.FontWeight.BOLD,
                    ),
                    padding=ft.padding.only(left=10, top=10)
                ),
                ft.Container(
                    content=location_grid,
                    padding=10
                )
            ])

        # Wrap in a container for padding
        main_container = ft.Container(
            content=main_column,
            padding=20,
            expand=True,
        )

        # Clear the page and add the new view
        self.page.clean()
        self.page.add(
            ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Container(
                            content=ft.Row(
                                controls=[
                                    ft.Text("Smart Home Dashboard", 
                                           size=32, 
                                           weight=ft.FontWeight.BOLD),
                                    ft.IconButton(
                                        icon=ft.icons.LOGOUT,
                                        tooltip="Logout",
                                        on_click=self.handle_logout
                                    )
                                ],
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                            ),
                            padding=ft.padding.only(left=20, right=20, top=20, bottom=10)
                        ),
                        main_container
                    ],
                    expand=True,
                ),
                expand=True,
            )
        )

    def show_add_device_dialog(self, e):
        def close_dialog(e):
            self.page.dialog.open = False
            self.page.update()

        def add_device(e):
            name = name_field.value
            device_type = type_dropdown.value
            location = location_field.value

            # Validate input
            if not name or not device_type or not location:
                self.page.show_snack_bar(
                    ft.SnackBar(content=ft.Text("Please fill in all fields"))
                )
                return

            # Set unit based on device type
            unit = ""
            if device_type == "temperature":
                unit = "°C"
            elif device_type == "humidity":
                unit = "%"

            try:
                # Create new device
                new_device = Device(
                    name=name,
                    type=device_type,
                    location=location,
                    unit=unit,
                    state=False,
                    user_id=self.current_user.id
                )
                self.session.add(new_device)
                self.session.commit()

                # Create threshold settings for sensor types
                if device_type in ["temperature", "humidity"]:
                    threshold = SensorThreshold(
                        device_id=new_device.id,
                        min_value=None,
                        max_value=None,
                        alert_enabled=False
                    )
                    self.session.add(threshold)
                    self.session.commit()

                # Show success message
                self.page.show_snack_bar(
                    ft.SnackBar(content=ft.Text(f"Device {name} added successfully"))
                )

                # Clear form
                name_field.value = ""
                type_dropdown.value = None
                location_field.value = ""
                name_field.update()
                type_dropdown.update()
                location_field.update()

                # Refresh device grid
                self.update_device_grid()

            except Exception as err:
                print(f"Error adding device: {err}")
                self.page.show_snack_bar(
                    ft.SnackBar(content=ft.Text(f"Error adding device: {str(err)}"))
                )

        name_field = ft.TextField(label="Device Name", width=300)
        type_dropdown = ft.Dropdown(
            label="Device Type",
            width=300,
            options=[
                ft.dropdown.Option("temperature"),
                ft.dropdown.Option("humidity"),
                ft.dropdown.Option("light"),
                ft.dropdown.Option("curtain"),
                ft.dropdown.Option("door"),
                ft.dropdown.Option("window"),
                ft.dropdown.Option("camera")
            ]
        )
        location_field = ft.TextField(label="Location", width=300)

        self.page.dialog = ft.AlertDialog(
            title=ft.Text("Add New Device"),
            content=ft.Column(
                controls=[
                    name_field,
                    type_dropdown,
                    location_field
                ],
                spacing=10,
                scroll=ft.ScrollMode.AUTO,
                height=400
            ),
            actions=[
                ft.TextButton("Cancel", on_click=close_dialog),
                ft.TextButton("Add", on_click=add_device)
            ]
        )
        self.page.dialog.open = True
        self.page.update()

    def show_device_details(self, e, device):
        details_view = SensorDetailsView(
            self.page,
            device,
            self.session,
            lambda _: self.show_home()
        )
        self.page.clean()
        self.page.add(details_view.build())

    def update_device_ui(self, device):
        """Update device card in UI when MQTT message is received"""
        try:
            # Store reading in database
            if hasattr(device, 'value') and device.value is not None:
                try:
                    value = float(device.value) if str(device.value).replace('.', '').isdigit() else 0
                    reading = SensorReading(
                        device_id=device.id,
                        value=value,
                        timestamp=datetime.now()
                    )
                    self.session.add(reading)
                    self.session.commit()
                except (ValueError, AttributeError) as err:
                    print(f"Error storing reading: {err}")

            # Check thresholds
            threshold = (
                self.session.query(SensorThreshold)
                .filter_by(device_id=device.id)
                .first()
            )
            
            if threshold and threshold.alert_enabled:
                try:
                    value = float(device.value) if str(device.value).replace('.', '').isdigit() else 0
                    if (threshold.min_value is not None and value < threshold.min_value) or \
                       (threshold.max_value is not None and value > threshold.max_value):
                        self.page.show_snack_bar(
                            ft.SnackBar(
                                content=ft.Text(f"Alert: {device.name} value {value:.1f} is outside threshold range!")
                            )
                        )
                except (ValueError, AttributeError) as err:
                    print(f"Error checking threshold: {err}")

            # Update UI
            if hasattr(self, 'devices_grid'):
                for control in self.devices_grid.controls:
                    if isinstance(control.content, ft.Container) and \
                       isinstance(control.content.content, ft.Column) and \
                       len(control.content.content.controls) > 1 and \
                       control.content.content.controls[1].value == device.name:
                        new_card = self.create_device_card(device)
                        index = self.devices_grid.controls.index(control)
                        self.devices_grid.controls[index] = new_card
                        self.page.update()
                        break
        except Exception as err:
            print(f"Error in update_device_ui: {err}")

    def show_login(self):
        self.page.clean()
        self.page.add(
            ft.Container(
                content=self.login_view,
                alignment=ft.alignment.center
            )
        )

    def show_register(self):
        self.page.clean()
        self.page.add(
            ft.Container(
                content=self.register_view,
                alignment=ft.alignment.center
            )
        )

    def show_home(self):
        """Show the home view."""
        self.page.clean()
        self.setup_home_view()
        self.page.update()

    def handle_login(self, e):
        user = (
            self.session.query(User)
            .filter_by(username=self.username_login.value)
            .first()
        )
        
        if user and bcrypt.checkpw(
            self.password_login.value.encode('utf-8'),
            user.password_hash
        ):
            self.current_user = user
            self.show_home()
            self.page.show_snack_bar(
                ft.SnackBar(content=ft.Text(f"Welcome back, {user.username}!"))
            )
        else:
            self.page.show_snack_bar(
                ft.SnackBar(content=ft.Text("Invalid username or password"))
            )

    def handle_register(self, e):
        if self.password_register.value != self.confirm_password.value:
            self.page.show_snack_bar(
                ft.SnackBar(content=ft.Text("Passwords do not match"))
            )
            return

        existing_user = (
            self.session.query(User)
            .filter_by(username=self.username_register.value)
            .first()
        )
        
        if existing_user:
            self.page.show_snack_bar(
                ft.SnackBar(content=ft.Text("Username already exists"))
            )
            return

        password_hash = bcrypt.hashpw(
            self.password_register.value.encode('utf-8'),
            bcrypt.gensalt()
        )
        
        new_user = User(
            username=self.username_register.value,
            password_hash=password_hash
        )
        self.session.add(new_user)
        self.session.commit()
        
        self.current_user = new_user
        self.show_home()
        self.page.show_snack_bar(
            ft.SnackBar(content=ft.Text("Registration successful!"))
        )

    def handle_logout(self, e):
        self.current_user = None
        self.show_login()
        self.page.show_snack_bar(
            ft.SnackBar(content=ft.Text("Logged out successfully"))
        )

class SensorDetailsView:
    def __init__(self, page: ft.Page, device, session, on_back):
        self.page = page
        self.device = device
        self.session = session
        self.on_back = on_back
        self.update_interval = None
        
        # Get or create threshold settings
        self.threshold = (
            self.session.query(SensorThreshold)
            .filter_by(device_id=self.device.id)
            .first()
        )
        if not self.threshold:
            self.threshold = SensorThreshold(
                device_id=self.device.id,
                min_value=None,
                max_value=None,
                alert_enabled=False
            )
            self.session.add(self.threshold)
            self.session.commit()

        # Create threshold controls
        self.min_threshold = ft.TextField(
            label="Min Value",
            value=str(self.threshold.min_value) if self.threshold.min_value is not None else "",
            width=100,
            text_align=ft.TextAlign.RIGHT,
            suffix_text=self.device.unit,
            on_change=self.update_thresholds
        )
        self.max_threshold = ft.TextField(
            label="Max Value",
            value=str(self.threshold.max_value) if self.threshold.max_value is not None else "",
            width=100,
            text_align=ft.TextAlign.RIGHT,
            suffix_text=self.device.unit,
            on_change=self.update_thresholds
        )
        self.alert_switch = ft.Switch(
            label="Enable Alerts",
            value=self.threshold.alert_enabled,
            active_color=ft.colors.BLUE_400,
            on_change=self.toggle_alerts
        )

    def update_thresholds(self, e):
        try:
            # Update min threshold
            min_val = self.min_threshold.value.strip()
            self.threshold.min_value = float(min_val) if min_val else None

            # Update max threshold
            max_val = self.max_threshold.value.strip()
            self.threshold.max_value = float(max_val) if max_val else None

            # Validate thresholds
            if (self.threshold.min_value is not None and 
                self.threshold.max_value is not None and 
                self.threshold.min_value > self.threshold.max_value):
                raise ValueError("Min value cannot be greater than max value")

            self.session.commit()
            
            # Show success message
            self.page.show_snack_bar(
                ft.SnackBar(
                    content=ft.Text("Thresholds updated successfully")
                )
            )
        except ValueError as err:
            # Show error message
            self.page.show_snack_bar(
                ft.SnackBar(
                    content=ft.Text(f"Invalid threshold value: {str(err)}")
                )
            )
            # Reset to previous values
            self.min_threshold.value = str(self.threshold.min_value) if self.threshold.min_value is not None else ""
            self.max_threshold.value = str(self.threshold.max_value) if self.threshold.max_value is not None else ""
            self.min_threshold.update()
            self.max_threshold.update()

    def toggle_alerts(self, e):
        self.threshold.alert_enabled = e.control.value
        self.session.commit()
        
        # Show status message
        self.page.show_snack_bar(
            ft.SnackBar(
                content=ft.Text(
                    f"Alerts {'enabled' if self.threshold.alert_enabled else 'disabled'} for {self.device.name}"
                )
            )
        )

    def create_chart(self):
        # Get the last 24 hours of readings
        readings = (
            self.session.query(SensorReading)
            .filter_by(device_id=self.device.id)
            .order_by(SensorReading.timestamp.desc())
            .limit(24)
            .all()
        )
        
        if not readings:
            return ft.Column(
                controls=[
                    ft.Icon(ft.icons.SHOW_CHART, size=40, color=ft.colors.GREY_400),
                    ft.Text("No data available yet", color=ft.colors.GREY_400),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER,
                expand=True,
            )
        
        # Prepare data for the chart
        timestamps = [reading.timestamp.strftime("%H:%M") for reading in reversed(readings)]
        values = [reading.value for reading in reversed(readings)]
        
        # Calculate axis values
        min_val = min(values)
        max_val = max(values)
        step = (max_val - min_val) / 5  # Create 5 steps
        
        # Generate axis labels with proper rounding
        y_axis_values = []
        current = min_val
        while current <= max_val:
            y_axis_values.append(current)
            current += step
        
        # Create the chart
        return ft.LineChart(
            data_series=[
                ft.LineChartData(
                    data_points=[
                        ft.LineChartDataPoint(x, y) 
                        for x, y in enumerate(values)
                    ],
                    stroke_width=2,
                    color=ft.colors.BLUE_400,
                    curved=True,
                    stroke_cap_round=True,
                )
            ],
            border=ft.border.all(1, ft.colors.GREY_400),
            horizontal_grid_lines=ft.ChartGridLines(
                interval=1,
                color=ft.colors.GREY_200,
                width=1,
            ),
            vertical_grid_lines=ft.ChartGridLines(
                interval=1,
                color=ft.colors.GREY_200,
                width=1,
            ),
            left_axis=ft.ChartAxis(
                labels=[
                    ft.ChartAxisLabel(
                        value=i,
                        label=ft.Text(f"{i:.1f}")
                    )
                    for i in y_axis_values
                ],
                labels_size=40,
            ),
            bottom_axis=ft.ChartAxis(
                labels=[
                    ft.ChartAxisLabel(
                        value=i,
                        label=ft.Text(timestamps[i])
                    )
                    for i in range(0, len(timestamps), 4)
                ],
                labels_size=40,
                labels_interval=4,
            ),
            expand=True,
            min_y=min_val,
            max_y=max_val,
            min_x=0,
            max_x=len(values) - 1,
            tooltip_bgcolor=ft.colors.with_opacity(0.8, ft.colors.BLUE_GREY_100),
        )

    def build(self):
        # Get latest reading
        latest_reading = (
            self.session.query(SensorReading)
            .filter_by(device_id=self.device.id)
            .order_by(SensorReading.timestamp.desc())
            .first()
        )
        
        # Create stats cards
        if latest_reading:
            current_value = f"{latest_reading.value} {self.device.unit}"
            last_updated = latest_reading.timestamp.strftime("%H:%M:%S")
        else:
            current_value = "No data"
            last_updated = "Never"
            
        stats_row = ft.Row(
            controls=[
                ft.Card(
                    content=ft.Container(
                        content=ft.Column(
                            controls=[
                                ft.Text("Current Value", size=14, color=ft.colors.GREY_400),
                                ft.Text(
                                    current_value,
                                    size=24,
                                    weight=ft.FontWeight.BOLD,
                                    color=ft.colors.BLUE_400,
                                ),
                            ],
                            spacing=5,
                        ),
                        padding=15,
                    )
                ),
                ft.Card(
                    content=ft.Container(
                        content=ft.Column(
                            controls=[
                                ft.Text("Last Updated", size=14, color=ft.colors.GREY_400),
                                ft.Text(
                                    last_updated,
                                    size=24,
                                    weight=ft.FontWeight.BOLD,
                                    color=ft.colors.BLUE_400,
                                ),
                            ],
                            spacing=5,
                        ),
                        padding=15,
                    )
                ),
            ],
            alignment=ft.MainAxisAlignment.SPACE_AROUND,
        )

        # Create threshold settings card
        threshold_card = ft.Card(
            content=ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Text(
                            "Threshold Settings",
                            size=16,
                            weight=ft.FontWeight.BOLD,
                        ),
                        ft.Row(
                            controls=[
                                self.min_threshold,
                                ft.Icon(
                                    name=ft.icons.ARROW_FORWARD,
                                    color=ft.colors.GREY_400,
                                ),
                                self.max_threshold,
                            ],
                            alignment=ft.MainAxisAlignment.CENTER,
                        ),
                        self.alert_switch,
                    ],
                    spacing=15,
                ),
                padding=20,
            )
        )

        # Create main view
        return ft.Column(
            controls=[
                ft.Container(
                    content=ft.Row(
                        controls=[
                            ft.IconButton(
                                icon=ft.icons.ARROW_BACK,
                                icon_color=ft.colors.BLUE_400,
                                on_click=self.on_back,
                            ),
                            ft.Text(
                                f"{self.device.name} - {self.device.type.capitalize()}",
                                size=20,
                                weight=ft.FontWeight.BOLD,
                            ),
                        ],
                    ),
                    padding=10,
                ),
                stats_row,
                threshold_card,
                ft.Container(
                    content=ft.Text(
                        "24-Hour History",
                        size=16,
                        weight=ft.FontWeight.BOLD,
                    ),
                    padding=ft.padding.only(left=10, top=20, bottom=10),
                ),
                ft.Container(
                    content=self.create_chart(),
                    expand=True,
                    padding=10,
                ),
            ],
            expand=True,
        )

    def dispose(self):
        if self.update_interval:
            self.update_interval.stop()

def main(page: ft.Page):
    app = SmartHomeApp()
    app.initialize(page)

if __name__ == "__main__":
    ft.app(target=main)
