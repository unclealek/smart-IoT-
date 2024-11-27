import flet as ft
from sensor_data import get_recent_readings, create_chart_image
from models import SensorThreshold
from datetime import datetime

class SensorDetailsView:
    def __init__(self, page: ft.Page, device, session, on_back):
        self.page = page
        self.device = device
        self.session = session
        self.on_back = on_back
        
        # Get or create threshold
        self.threshold = (
            session.query(SensorThreshold)
            .filter_by(device_id=device.id)
            .first()
        )
        if not self.threshold:
            self.threshold = SensorThreshold(device_id=device.id)
            session.add(self.threshold)
            session.commit()

        # Create a ScrollableControl
        self.scroll = ft.Column(
            scroll=ft.ScrollMode.AUTO,
            expand=True,
            spacing=20,
        )

        self.container = ft.Container(
            content=self.scroll,
            expand=True,
            padding=20
        )

        # Initialize components
        self.init_components()
        
        # Update chart initially
        self.update_chart(None)

    def build(self):
        return self.container

    def init_components(self):
        # Back button
        back_btn = ft.IconButton(
            icon=ft.icons.ARROW_BACK,
            on_click=self.on_back
        )

        # Header section
        header = ft.Row(
            controls=[
                back_btn,
                ft.Text(f"{self.device.name} Details", size=20, weight=ft.FontWeight.BOLD),
            ],
            alignment=ft.MainAxisAlignment.START
        )

        # Device Info
        device_info = ft.Card(
            content=ft.Container(
                padding=10,
                content=ft.Column(
                    controls=[
                        ft.Text("Device Information", weight=ft.FontWeight.BOLD),
                        ft.Text(f"Type: {self.device.type}"),
                        ft.Text(f"Location: {self.device.location}"),
                        ft.Text(f"Last Updated: {self.device.last_updated.strftime('%Y-%m-%d %H:%M:%S') if self.device.last_updated else 'Never'}")
                    ]
                )
            )
        )

        # Settings
        settings_card = ft.Card(
            content=ft.Container(
                padding=10,
                content=ft.Column(
                    controls=[
                        ft.Text("Settings", weight=ft.FontWeight.BOLD),
                        ft.Row(
                            controls=[
                                ft.TextField(
                                    label="Minimum Threshold",
                                    value=str(self.threshold.min_value) if self.threshold.min_value else "",
                                    width=200,
                                    helper_text=f"Minimum {self.device.type} value"
                                ),
                                ft.TextField(
                                    label="Maximum Threshold",
                                    value=str(self.threshold.max_value) if self.threshold.max_value else "",
                                    width=200,
                                    helper_text=f"Maximum {self.device.type} value"
                                )
                            ]
                        ),
                        ft.Row(
                            controls=[
                                ft.Switch(
                                    label="Enable Alerts",
                                    value=self.threshold.alert_enabled,
                                    active_color=ft.colors.BLUE_400
                                ),
                                ft.TextField(
                                    label="Alert Email",
                                    value=self.threshold.alert_email if self.threshold.alert_email else "",
                                    width=300,
                                    helper_text="Email for alerts"
                                )
                            ]
                        ),
                        ft.Switch(
                            label="Enable Sensor",
                            value=self.device.is_enabled,
                            active_color=ft.colors.GREEN_400
                        ),
                        ft.ElevatedButton(
                            text="Save Settings",
                            on_click=lambda e: self.save_settings(e)
                        )
                    ]
                )
            )
        )

        # Chart controls
        self.time_dropdown = ft.Dropdown(
            width=200,
            options=[
                ft.dropdown.Option("1", "Last Hour"),
                ft.dropdown.Option("6", "Last 6 Hours"),
                ft.dropdown.Option("24", "Last 24 Hours"),
                ft.dropdown.Option("168", "Last 7 Days"),
            ],
            value="24",
            label="Time Range",
            on_change=self.update_chart
        )

        self.refresh_btn = ft.IconButton(
            icon=ft.icons.REFRESH,
            on_click=self.update_chart
        )

        chart_controls = ft.Row(
            controls=[
                self.time_dropdown,
                self.refresh_btn
            ],
            alignment=ft.MainAxisAlignment.START
        )

        # Chart image
        self.chart_image = ft.Image(
            src_base64="",
            width=800,
            height=400,
            fit=ft.ImageFit.CONTAIN
        )

        # Add all components to the scroll view
        self.scroll.controls = [
            header,
            device_info,
            settings_card,
            chart_controls,
            self.chart_image
        ]

    def update_chart(self, e):
        try:
            hours = int(self.time_dropdown.value)
            print(f"Updating chart for {hours} hours")
            
            readings = get_recent_readings(self.session, self.device.id, hours)
            print(f"Got {len(readings)} readings")
            
            if readings:
                timestamps = [r.timestamp for r in readings]
                values = [r.value for r in readings]
                
                # Get threshold if it exists
                threshold = self.session.query(SensorThreshold).filter_by(device_id=self.device.id).first()
                
                # Create chart image
                print("Generating chart image...")
                chart_data = create_chart_image(timestamps, values, self.device.type, threshold)
                
                # Set the image source with proper data URI
                self.chart_image.src_base64 = chart_data
                print("Chart image updated")
            else:
                print("No readings found")
                
            self.page.update()
            
        except Exception as e:
            print(f"Error updating chart: {str(e)}")
            import traceback
            traceback.print_exc()

    def save_settings(self, e):
        try:
            # Get the controls from the settings card
            settings_card = self.scroll.controls[2]
            controls = settings_card.content.content.controls
            
            # Update threshold values
            min_threshold = controls[1].controls[0]
            max_threshold = controls[1].controls[1]
            alert_switch = controls[2].controls[0]
            alert_email = controls[2].controls[1]
            enable_switch = controls[3]
            
            self.threshold.min_value = float(min_threshold.value) if min_threshold.value else None
            self.threshold.max_value = float(max_threshold.value) if max_threshold.value else None
            self.threshold.alert_enabled = alert_switch.value
            self.threshold.alert_email = alert_email.value
            
            # Update device status
            self.device.is_enabled = enable_switch.value
            
            self.session.commit()
            self.page.show_snack_bar(
                ft.SnackBar(content=ft.Text("Settings saved successfully!"))
            )
        except ValueError:
            self.page.show_snack_bar(
                ft.SnackBar(content=ft.Text("Please enter valid threshold values!"))
            )
