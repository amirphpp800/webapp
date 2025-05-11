import random
import subprocess
import platform
import time
import threading
import os
import requests
import asyncio
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.core.window import Window
from kivy.uix.tabbedpanel import TabbedPanel, TabbedPanelItem
from kivy.clock import Clock
from kivy.lang import Builder
from kivy.properties import StringProperty, BooleanProperty, ListProperty, NumericProperty
from kivy.graphics import Color, Rectangle
from kivy.config import Config
from kivy.uix.gridlayout import GridLayout
from kivy.uix.progressbar import ProgressBar
from functools import partial
from concurrent.futures import ThreadPoolExecutor
from threading import Lock

# Environment fixes
os.environ['KIVY_WINDOW'] = 'sdl2'
os.environ['KIVY_GL_BACKEND'] = 'sdl2'
Config.set('graphics', 'multisamples', '0')  # Fix for GL issues
Config.set('input', 'mouse', 'mouse,multitouch_on_demand')  # Fix for mouse issues
Config.set('kivy', 'keyboard_mode', 'systemanddock')  # Better keyboard on mobile
Config.set('graphics', 'resizable', False)  # Prevent resizing issues
Config.set('graphics', 'width', 360)  # Default mobile width
Config.set('graphics', 'height', 640)  # Default mobile height

# Set elegant dark theme colors
Window.clearcolor = (0.13, 0.15, 0.2, 1)  # Dark blue-gray background

# Define UI with KV language
Builder.load_string('''
<RoundedButton@Button>:
    background_color: 0, 0, 0, 0
    background_normal: ''
    min_state_time: 0.1
    size_hint_y: None
    height: "54dp"  # Bigger touch target for mobile
    font_size: "18sp"  # Larger text for mobile
    padding: [15, 15]
    canvas.before:
        Color:
            rgba: (0.27, 0.44, 0.93, 1) if self.state == 'normal' else (0.22, 0.36, 0.83, 1)
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [10, 10, 10, 10]
        Color:
            rgba: (0.32, 0.49, 0.98, 0.2)
        SmoothLine:
            rounded_rectangle: [self.x, self.y, self.width, self.height, 10, 10, 10, 10]
            width: 1.5

<ResultRow>:
    cols: 4
    spacing: 2
    size_hint_y: None
    height: "45dp"
    canvas.before:
        Color:
            rgba: 0.18, 0.20, 0.25, 1
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [6, 6, 6, 6]
        Color:
            rgba: 0.27, 0.30, 0.35, 0.7
        Line:
            rounded_rectangle: [self.x, self.y, self.width, self.height, 6, 6, 6, 6]
            width: 1

    Label:
        text: root.ip_address
        size_hint_x: 0.4
        color: 0.95, 0.95, 0.95, 1
        font_size: '16sp'
        bold: True
        canvas.before:
            Color:
                rgba: 0.25, 0.25, 0.3, 0.5
            Line:
                points: [self.x + self.width, self.y, self.x + self.width, self.y + self.height]
                width: 1

    Label:
        text: root.ping_result
        size_hint_x: 0.2
        color: (0.3, 0.9, 0.3, 1) if "ms" in root.ping_result else (0.9, 0.3, 0.3, 1)
        font_size: '16sp'
        canvas.before:
            Color:
                rgba: 0.25, 0.25, 0.3, 0.5
            Line:
                points: [self.x + self.width, self.y, self.x + self.width, self.y + self.height]
                width: 1

    Label:
        text: root.country
        size_hint_x: 0.3
        color: 0.95, 0.95, 0.95, 1
        font_size: '16sp'
        halign: 'left'
        text_size: self.width - dp(10), None
        shorten: True
        shorten_from: 'right'
        valign: 'middle'
        canvas.before:
            Color:
                rgba: 0.25, 0.25, 0.3, 0.5
            Line:
                points: [self.x + self.width, self.y, self.x + self.width, self.y + self.height]
                width: 1

<IPApp>:
    orientation: 'vertical'
    spacing: 12
    padding: 20

    canvas.before:
        Color:
            rgba: 0.13, 0.15, 0.2, 1  # Dark blue-gray background
        Rectangle:
            pos: self.pos
            size: self.size

    BoxLayout:
        size_hint_y: None
        height: "70dp"
        orientation: 'vertical'
        
        canvas.before:
            Color:
                rgba: 0.17, 0.19, 0.25, 1  # Slightly lighter than background
            RoundedRectangle:
                pos: self.pos
                size: self.size
                radius: [10, 10, 10, 10]

        Label:
            text: "IP Scanner & Ping Test"
            font_size: '24sp'
            bold: True
            color: 0.95, 0.95, 0.95, 1
            size_hint_y: None
            height: "35dp"

        Label:
            id: internet_status
            text: "Internet Status: Checking..."
            font_size: '18sp'
            color: (0.2, 0.9, 0.2, 1) if "Connected" in self.text else (0.9, 0.2, 0.2, 1)
            size_hint_y: None 
            height: "35dp"

    BoxLayout:
        size_hint_y: None
        height: "74dp"
        spacing: 15
        padding: [15, 5, 15, 5]  # Left, top, right, bottom padding

        Button:
            id: scan_button
            text: "Start Scanning"
            font_size: '18sp'
            bold: True
            size_hint_x: 0.5
            size_hint_y: 1
            background_color: 0.2, 0.7, 0.2, 1
            on_release: root.toggle_scanning()
            canvas.before:
                Color:
                    rgba: self.background_color
                RoundedRectangle:
                    pos: self.pos
                    size: self.size
                    radius: [10, 10, 10, 10]
                # Add a glow effect
                Color:
                    rgba: 0.2, 0.7, 0.2, 0.2
                RoundedRectangle:
                    pos: [self.x-2, self.y-2]
                    size: [self.width+4, self.height+4]
                    radius: [12, 12, 12, 12]

        Button:
            text: "Exit"
            font_size: '18sp'
            bold: True
            size_hint_x: 0.5
            size_hint_y: 1
            background_color: 0.9, 0.2, 0.2, 1
            on_release: app.stop()
            canvas.before:
                Color:
                    rgba: self.background_color
                RoundedRectangle:
                    pos: self.pos
                    size: self.size
                    radius: [10, 10, 10, 10]
                # Add a glow effect
                Color:
                    rgba: 0.9, 0.2, 0.2, 0.2
                RoundedRectangle:
                    pos: [self.x-2, self.y-2]
                    size: [self.width+4, self.height+4]
                    radius: [12, 12, 12, 12]

    TabbedPanel:
        do_default_tab: False
        tab_width: self.width / 2
        tab_height: "48dp"
        tab_pos: 'top_mid'
        background_color: (0.16, 0.18, 0.22, 1)

        canvas.before:
            Color:
                rgba: 0.16, 0.18, 0.22, 1
            RoundedRectangle:
                pos: self.pos
                size: self.size
                radius: [10, 10, 10, 10]
            # Border for the panel
            Color:
                rgba: 0.22, 0.25, 0.3, 1
            Line:
                rounded_rectangle: [self.x, self.y, self.width, self.height, 10, 10, 10, 10]
                width: 1

        TabbedPanelItem:
            text: "Current Scan"
            font_size: '18sp'
            background_color: [0.27, 0.44, 0.93, 1] if self.state == 'down' else [0.18, 0.20, 0.25, 1]
            
            BoxLayout:
                orientation: 'vertical'
                padding: 15
                spacing: 12

                BoxLayout:
                    orientation: 'horizontal'
                    size_hint_y: None
                    height: "35dp"
                    spacing: 5

                    Label:
                        text: "Scan Progress:"
                        size_hint_x: 0.4
                        font_size: '18sp'
                        color: 0.95, 0.95, 0.95, 1
                        bold: True

                    Label:
                        text: f"{root.successful_scans} found / {root.total_scans} scanned"
                        size_hint_x: 0.6
                        font_size: '18sp'
                        color: 0.95, 0.95, 0.95, 1

                # Customized progress bar with gradient
                BoxLayout:
                    size_hint_y: None
                    height: "24dp"
                    padding: [2, 2, 2, 2]
                    
                    canvas.before:
                        Color:
                            rgba: 0.22, 0.24, 0.28, 1  # Background of progress bar
                        RoundedRectangle:
                            pos: self.pos
                            size: self.size
                            radius: [6, 6, 6, 6]
                        # Progress indicator
                        Color:
                            rgba: 0.27, 0.44, 0.93, 1  # Blue gradient
                        RoundedRectangle:
                            pos: self.pos
                            size: [self.width * (root.scan_progress_value / 100), self.height]
                            radius: [6, 6, 6, 6]

                Label:
                    text: "Scan Status:"
                    size_hint_y: None
                    height: "35dp"
                    font_size: '18sp'
                    color: 0.95, 0.95, 0.95, 1
                    bold: True
                    halign: 'left'
                    text_size: self.size

                # Custom scroll view with styled background
                BoxLayout:
                    canvas.before:
                        Color:
                            rgba: 0.15, 0.17, 0.21, 1
                        RoundedRectangle:
                            pos: self.pos
                            size: self.size
                            radius: [8, 8, 8, 8]
                        Color:
                            rgba: 0.22, 0.25, 0.3, 1
                        Line:
                            rounded_rectangle: [self.x, self.y, self.width, self.height, 8, 8, 8, 8]
                            width: 1
                    
                    ScrollView:
                        do_scroll_x: False
                        do_scroll_y: True
                        effect_cls: "ScrollEffect"  # Smoother scrolling
                        bar_width: 8
                        bar_color: [0.27, 0.44, 0.93, 0.7]  # Blue scrollbar
                        bar_inactive_color: [0.27, 0.44, 0.93, 0.3]
                        scroll_type: ['bars', 'content']

                        Label:
                            id: result_label
                            text: root.scan_status
                            font_size: '16sp'
                            color: 0.9, 0.9, 0.9, 1
                            size_hint_y: None
                            text_size: self.width - dp(20), None
                            height: self.texture_size[1] + dp(20)
                            halign: 'left'
                            padding: [10, 10]
                            markup: True  # Enable markup for colored text

        TabbedPanelItem:
            text: "Results"
            font_size: '18sp'
            background_color: [0.27, 0.44, 0.93, 1] if self.state == 'down' else [0.18, 0.20, 0.25, 1]

            BoxLayout:
                orientation: 'vertical'
                padding: 15
                spacing: 12

                # Header with gradient background
                BoxLayout:
                    size_hint_y: None
                    height: "45dp"
                    padding: [5, 0, 5, 0]
                    
                    canvas.before:
                        Color:
                            rgba: 0.18, 0.22, 0.28, 1
                        RoundedRectangle:
                            pos: self.pos
                            size: self.size
                            radius: [8, 8, 8, 8]

                    Label:
                        text: "IP Address"
                        size_hint_x: 0.4
                        font_size: '17sp'
                        bold: True
                        color: 0.95, 0.95, 0.95, 1

                    Label:
                        text: "Ping"
                        size_hint_x: 0.2
                        font_size: '17sp'
                        bold: True
                        color: 0.95, 0.95, 0.95, 1

                    Label:
                        text: "Country"
                        size_hint_x: 0.3
                        font_size: '17sp'
                        bold: True
                        color: 0.95, 0.95, 0.95, 1

                    Label:
                        text: "Copy"
                        size_hint_x: 0.1
                        font_size: '17sp'
                        bold: True
                        color: 0.95, 0.95, 0.95, 1

                # Styled scroll view for results
                BoxLayout:
                    canvas.before:
                        Color:
                            rgba: 0.15, 0.17, 0.21, 1
                        RoundedRectangle:
                            pos: self.pos
                            size: self.size
                            radius: [8, 8, 8, 8]
                        Color:
                            rgba: 0.22, 0.25, 0.3, 1
                        Line:
                            rounded_rectangle: [self.x, self.y, self.width, self.height, 8, 8, 8, 8]
                            width: 1
                    
                    ScrollView:
                        do_scroll_x: False
                        do_scroll_y: True
                        effect_cls: "ScrollEffect"  # Smoother scrolling
                        bar_width: 8
                        bar_color: [0.27, 0.44, 0.93, 0.7]  # Blue scrollbar
                        bar_inactive_color: [0.27, 0.44, 0.93, 0.3]
                        scroll_type: ['bars', 'content']

                        GridLayout:
                            id: results_grid
                            cols: 1
                            spacing: 8
                            padding: [5, 5, 5, 5]
                            size_hint_y: None
                            height: self.minimum_height

                # Styled buttons with gradient and glow effect
                BoxLayout:
                    size_hint_y: None
                    height: "50dp"
                    spacing: 15
                    padding: [5, 0, 5, 0]

                    Button:
                        text: "Clear Results"
                        font_size: '16sp'
                        bold: True
                        size_hint_x: 0.5
                        background_color: 0, 0, 0, 0
                        on_release: root.clear_results()
                        
                        canvas.before:
                            Color:
                                rgba: 0.9, 0.3, 0.3, 1
                            RoundedRectangle:
                                pos: self.pos
                                size: self.size
                                radius: [8, 8, 8, 8]
                            # Glow effect
                            Color:
                                rgba: 0.9, 0.3, 0.3, 0.2
                            RoundedRectangle:
                                pos: [self.x-2, self.y-2]
                                size: [self.width+4, self.height+4]
                                radius: [10, 10, 10, 10]

                    Button:
                        text: "Export Results"
                        font_size: '16sp'
                        bold: True
                        size_hint_x: 0.5
                        background_color: 0, 0, 0, 0
                        on_release: root.export_results()
                        
                        canvas.before:
                            Color:
                                rgba: 0.27, 0.44, 0.93, 1
                            RoundedRectangle:
                                pos: self.pos
                                size: self.size
                                radius: [8, 8, 8, 8]
                            # Glow effect
                            Color:
                                rgba: 0.27, 0.44, 0.93, 0.2
                            RoundedRectangle:
                                pos: [self.x-2, self.y-2]
                                size: [self.width+4, self.height+4]
                                radius: [10, 10, 10, 10]
''')

# Improved cache with LRU functionality
class LRUCache:
    def __init__(self, capacity=1000):
        self.cache = {}
        self.capacity = capacity
        self.access_order = []
        self.lock = threading.Lock()

    def get(self, key):
        with self.lock:
            if key in self.cache:
                # Move to end (most recently used)
                self.access_order.remove(key)
                self.access_order.append(key)
                return self.cache[key]
            return None

    def put(self, key, value):
        with self.lock:
            if key in self.cache:
                # Update existing key
                self.cache[key] = value
                self.access_order.remove(key)
                self.access_order.append(key)
            else:
                # Check capacity
                if len(self.cache) >= self.capacity:
                    # Remove least recently used
                    oldest = self.access_order.pop(0)
                    self.cache.pop(oldest)

                # Add new item
                self.cache[key] = value
                self.access_order.append(key)

# Create LRU cache for country info
country_cache = LRUCache(capacity=1000)

# Session for reusing connections
ip_api_session = requests.Session()
ip_api_session.headers.update({
    'User-Agent': 'IPScanner/1.0',
    'Accept': 'application/json'
})

# Pre-compile regular expressions for performance
import re
ttl_regex = re.compile(r'ttl=|time=', re.IGNORECASE)

def format_country_name(country_name):
    """Format country name to ensure consistent display"""
    if not country_name or country_name == "Unknown":
        return "Unknown"

    # Limit length for display purposes
    if len(country_name) > 15:
        return country_name[:15]

    return country_name

def generate_random_ip(min_octet1=0, max_octet1=255, exclude_private=False):
    """Generate a random IP with filtering options"""
    while True:
        # Generate first octet within range
        first = random.randint(min_octet1, max_octet1)

        # Generate remaining octets
        ip = f"{first}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}"

        # Check if we should skip private IPs
        if exclude_private and is_private_ip(ip):
            continue

        return ip

def is_private_ip(ip):
    """Check if an IP address is in a private range"""
    octets = [int(o) for o in ip.split('.')]

    # Check private IP ranges
    if octets[0] == 10:
        return True
    if octets[0] == 172 and 16 <= octets[1] <= 31:
        return True
    if octets[0] == 192 and octets[1] == 168:
        return True
    if octets[0] == 127:  # Loopback
        return True
    if octets[0] == 169 and octets[1] == 254:  # Link-local
        return True

    return False

def ping_test(ip_address, timeout=3):
    """Test if an IP address responds to ping with optimized performance."""
    try:
        start_time = time.time()
        param = '-n' if platform.system().lower() == 'windows' else '-c'

        # Optimize command for faster execution
        if platform.system().lower() == 'windows':
            cmd = ['ping', '-w', str(int(timeout * 1000)), '-n', '1', ip_address]
        else:
            # Using -c 1 for one ping request, -I to use default interface
            cmd = ['ping', '-W', str(int(timeout)), '-c', '1', ip_address]

        output = subprocess.check_output(
            cmd, 
            universal_newlines=True, 
            stderr=subprocess.STDOUT,
            timeout=timeout + 1  # Add buffer to timeout
        )

        end_time = time.time()
        response_time = round((end_time - start_time) * 1000)

        # Look for actual ping time in the output if available
        time_match = re.search(r'time=(\d+\.?\d*)', output)
        if time_match:
            return True, f"{time_match.group(1)}ms"

        # Use regex for faster pattern matching
        if ttl_regex.search(output):
            return True, f"{response_time}ms"
        return False, "Failed"
    except subprocess.CalledProcessError:
        return False, "Failed"
    except subprocess.TimeoutExpired:
        return False, "Timeout"
    except Exception as e:
        error_msg = str(e)
        if "No such file" in error_msg:
            return False, "Network error"
        return False, f"Error: {error_msg[:20]}"

async def async_ping_test(ip_address, timeout=3):
    """Asynchronous ping test implementation with better error handling."""
    param = '-n' if platform.system().lower() == 'windows' else '-c'

    try:
        # Optimize command
        if platform.system().lower() == 'windows':
            cmd = ['ping', '-w', str(int(timeout * 1000)), '-n', '1', ip_address]
        else:
            cmd = ['ping', '-W', str(int(timeout)), '-c', '1', ip_address]

        # Use a timeout for the entire process
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        # Set a timeout using asyncio
        try:
            start_time = time.time()
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            end_time = time.time()
            response_time = round((end_time - start_time) * 1000)

            stdout_str = stdout.lower() if stdout else b""
            if proc.returncode == 0 and (b"ttl=" in stdout_str or b"time=" in stdout_str):
                return True, f"{response_time}ms"
            return False, "Failed"
        except asyncio.TimeoutError:
            # Kill the process if it's still running
            try:
                proc.kill()
            except:
                pass
            return False, "Timeout"
    except Exception as e:
        return False, f"Error: {str(e)[:20]}"

# Use a semaphore to limit concurrent API requests
country_api_semaphore = asyncio.Semaphore(5)  # Max 5 concurrent API requests

async def get_country_from_ip_async(ip_address):
    """Asynchronous version of country lookup"""
    # Check cache first
    cached = country_cache.get(ip_address)
    if cached:
        return cached

    try:
        async with country_api_semaphore:  # Limit concurrent requests
            # Use aiohttp for async requests
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"https://api.iplocation.net/?ip={ip_address}", 
                    timeout=3
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        country = data.get("country_name", "Unknown")
                        formatted_country = format_country_name(country)

                        # Cache the result
                        country_cache.put(ip_address, formatted_country)
                        return formatted_country
            return "Unknown"
    except Exception:
        return "Unknown"

def get_country_from_ip(ip_address):
    """Get country information for an IP address using API with caching."""
    # Check cache first - faster lookup
    cached = country_cache.get(ip_address)
    if cached:
        return cached

    try:
        # Use session for connection pooling
        response = ip_api_session.get(
            f"https://api.iplocation.net/?ip={ip_address}", 
            timeout=3
        )

        if response.status_code == 200:
            data = response.json()
            country = data.get("country_name", "Unknown")
            formatted_country = format_country_name(country)

            # Cache the result
            country_cache.put(ip_address, formatted_country)
            return formatted_country
        return "Unknown"
    except Exception:
        return "Unknown"

def is_mobile():
    """Better detection for mobile devices"""
    try:
        # Check environment variables first (faster)
        if 'ANDROID_DATA' in os.environ or 'ANDROID_BOOTLOGO' in os.environ:
            return True

        # Check platform
        if platform.system().startswith('Linux') and 'ANDROID_BOOTLOGO' in os.environ:
            return True

        # Check Kivy's Window properties
        if hasattr(Window, '_is_mobile') and Window._is_mobile:
            return True
    except:
        pass
    return False

class ResultRow(GridLayout):
    ip_address = StringProperty("")
    ping_result = StringProperty("")
    country = StringProperty("")

    def __init__(self, **kwargs):
        super(ResultRow, self).__init__(**kwargs)
        # Add a button after initialization
        copy_btn = Button(
            text="📋", 
            size_hint_x=0.1,
            background_color=(0.3, 0.5, 0.9, 1)
        )
        copy_btn.bind(on_release=lambda x: self.copy_ip())
        self.add_widget(copy_btn)

    def copy_ip(self):
        try:
            from kivy.core.clipboard import Clipboard
            Clipboard.copy(self.ip_address)
            # Show a brief feedback popup
            from kivy.uix.popup import Popup
            from kivy.uix.label import Label
            popup = Popup(
                title='',
                content=Label(text=f'IP {self.ip_address} copied!'),
                size_hint=(0.7, 0.2),
                auto_dismiss=True
            )
            popup.open()
            # Auto close after 1 second
            Clock.schedule_once(lambda dt: popup.dismiss(), 1)
        except Exception as e:
            print(f"Failed to copy to clipboard: {e}")

class IPApp(BoxLayout):
    current_ip = StringProperty("")
    scan_status = StringProperty("Click 'Start Scanning' to begin scanning random IPs")
    scanning = BooleanProperty(False)
    total_scans = NumericProperty(0)
    successful_scans = NumericProperty(0)
    scan_progress_value = NumericProperty(0)

    # Configuration options
    min_octet1 = NumericProperty(0)
    max_octet1 = NumericProperty(255)
    exclude_private = BooleanProperty(False)
    country_filter = StringProperty("")
    ping_timeout = NumericProperty(3)

    def __init__(self, **kwargs):
        super(IPApp, self).__init__(**kwargs)
        self.scan_event = None
        self.ping_queue = []
        self.skip_scan_stop_check = False
        self.scan_status_lock = threading.Lock()
        self.results_lock = threading.Lock()
        self.status_buffer = []
        self.status_update_event = None
        self._enable_country_lookup = True

        # Create a thread pool with adaptive sizing based on platform
        max_workers = 20 if not is_mobile() else 5
        self.executor = ThreadPoolExecutor(max_workers=max_workers)

        # Last update timestamp for status to prevent too frequent updates
        self._last_status_update = 0

        # Create an async event loop for the application
        self._event_loop = None

        # Setup periodic status updates to improve UI responsiveness
        self.status_update_event = Clock.schedule_interval(self.flush_status_buffer, 0.5)

        # Check internet first
        Clock.schedule_once(self.check_internet_connectivity, 0)

        # Load settings if available
        self.load_settings()

    def load_settings(self):
        """Load saved settings if available"""
        try:
            import json
            settings_path = os.path.join(App.get_running_app().user_data_dir, 'settings.json')

            if os.path.exists(settings_path):
                with open(settings_path, 'r') as f:
                    settings = json.load(f)

                # Apply settings
                self.min_octet1 = settings.get('min_octet1', 0)
                self.max_octet1 = settings.get('max_octet1', 255)
                self.exclude_private = settings.get('exclude_private', False)
                self.country_filter = settings.get('country_filter', "")
                self.ping_timeout = settings.get('ping_timeout', 3)
                self._enable_country_lookup = settings.get('enable_country_lookup', True)
        except:
            # Use defaults if loading fails
            pass

    def save_settings(self):
        """Save current settings"""
        try:
            import json
            settings = {
                'min_octet1': self.min_octet1,
                'max_octet1': self.max_octet1,
                'exclude_private': self.exclude_private,
                'country_filter': self.country_filter,
                'ping_timeout': self.ping_timeout,
                'enable_country_lookup': self._enable_country_lookup
            }

            settings_path = os.path.join(App.get_running_app().user_data_dir, 'settings.json')
            with open(settings_path, 'w') as f:
                json.dump(settings, f)
        except:
            # Silently fail if saving fails
            pass

    def check_internet_connectivity(self, dt):
        def _check_connectivity():
            try:
                # Faster connectivity check - only basic TCP connection
                import socket
                socket.create_connection(("8.8.8.8", 53), timeout=3)
                Clock.schedule_once(lambda dt: setattr(self.ids.internet_status, 'text', "Internet Status: Connected"), 0)
            except:
                try:
                    # Fallback to HTTP request
                    requests.head("https://www.google.com", timeout=3)
                    Clock.schedule_once(lambda dt: setattr(self.ids.internet_status, 'text', "Internet Status: Connected"), 0)
                except:
                    Clock.schedule_once(lambda dt: setattr(self.ids.internet_status, 'text', "Internet Status: Not Connected"), 0)

        threading.Thread(target=_check_connectivity, daemon=True).start()

    def toggle_scanning(self):
        if not self.scanning:
            self.start_scanning()
        else:
            self.stop_scanning()

    def start_scanning(self):
        self.scanning = True
        self.skip_scan_stop_check = True  # Prevent immediate stop on mobile
        self.scan_status = "Scanning started...\n"
        self.ids.scan_button.text = "Stop Scanning"
        self.ids.scan_button.background_color = (0.8, 0.2, 0.2, 1)

        # Reset counters
        self.total_scans = 0
        self.successful_scans = 0
        self.scan_progress_value = 0

        # Ensure we close any existing event loop
        self._cleanup_event_loop()

        # Start scanning with appropriate method based on platform
        if is_mobile():
            # Simpler, sequential scanning for mobile
            self.scan_event = Clock.schedule_interval(lambda dt: self.scan_next_ip(), 0.5)
        else:
            # Create a new event loop for the async scanning
            self._event_loop = asyncio.new_event_loop()
            # Run the parallel scanner in a separate thread
            threading.Thread(
                target=self._run_async_scanner,
                daemon=True
            ).start()

        # Reset skip_scan_stop_check after a delay
        Clock.schedule_once(lambda dt: setattr(self, 'skip_scan_stop_check', False), 1)

    def _cleanup_event_loop(self):
        """Clean up the event loop if it exists"""
        if self._event_loop is not None:
            try:
                # Close the loop properly
                if not self._event_loop.is_closed():
                    if self._event_loop.is_running():
                        # This needs to be called from another thread
                        self._event_loop.call_soon_threadsafe(self._event_loop.stop)
                    self._event_loop.close()
            except:
                pass
            self._event_loop = None

    def _run_async_scanner(self):
        """Run the async scanner in its own thread with its own event loop"""
        try:
            loop = self._event_loop
            if loop is None:
                return

            asyncio.set_event_loop(loop)
            loop.run_until_complete(self._parallel_scan_runner())
        except Exception as e:
            self.add_status_update(f"Scanner error: {str(e)}\n")
        finally:
            # Clean up
            self._cleanup_event_loop()

    def stop_scanning(self):
        if self.skip_scan_stop_check:
            return

        self.scanning = False
        self.add_status_update("Scanning stopped.\n")
        self.ids.scan_button.text = "Start Scanning"
        self.ids.scan_button.background_color = (0.2, 0.6, 0.2, 1)

        # Cancel any scheduled events
        if self.scan_event:
            self.scan_event.cancel()
            self.scan_event = None

        # Clean up event loop
        self._cleanup_event_loop()

        # Flush any remaining status updates
        self.flush_status_buffer(None)

    def add_status_update(self, status_text):
        """Add status update to buffer with rate limiting"""
        current_time = time.time()

        # Check if we should throttle updates (more than 20 per second)
        if current_time - self._last_status_update < 0.05:
            # Too frequent, only update buffer for successful scans
            if "Success" in status_text:
                with self.scan_status_lock:
                    self.status_buffer.append(status_text)
            return

        # Update timestamp
        self._last_status_update = current_time

        # Add to buffer
        with self.scan_status_lock:
            self.status_buffer.append(status_text)

    def flush_status_buffer(self, dt):
        """Update UI with batched status updates for better performance"""
        with self.scan_status_lock:
            if not self.status_buffer:
                return

            # Combine all status updates
            combined_update = "".join(self.status_buffer)
            self.status_buffer = []

        # Update the status text (only keep recent entries)
        max_length = 5000  # Maximum characters to keep
        new_text = self.scan_status + combined_update

        # Smart truncation to keep latest entries
        if len(new_text) > max_length:
            # Find the last few complete lines that fit in max_length
            truncated = new_text[-max_length:]
            # Find the first newline to get complete lines
            newline_pos = truncated.find('\n')
            if newline_pos != -1:
                truncated = truncated[newline_pos+1:]
            self.scan_status = "...[earlier logs truncated]...\n" + truncated
        else:
            self.scan_status = new_text

    async def _parallel_scan_runner(self):
        """Run parallel scanning using async methods"""
        try:
            # Determine optimal batch size based on platform
            concurrent_tasks = 20 if not is_mobile() else 5

            # Keep scanning as long as the flag is set
            while self.scanning:
                # Process in batches for better control
                await self._test_multiple_ips_async(count=concurrent_tasks)

                # Small pause between batches to prevent system overload
                await asyncio.sleep(0.1)

                # Check if we're still scanning
                if not self.scanning:
                    break

        except Exception as e:
            self.add_status_update(f"Parallel scanning error: {str(e)}\n")

    def scan_next_ip(self):
        """Single IP scan method (used on mobile)"""
        if not self.scanning:
            return

        # Generate random IP with filters and update UI
        self.current_ip = generate_random_ip(
            min_octet1=self.min_octet1,
            max_octet1=self.max_octet1, 
            exclude_private=self.exclude_private
        )
        self.add_status_update(f"Testing {self.current_ip}...\n")

        # Start ping test in a separate thread to avoid blocking UI
        self.executor.submit(self._test_current_ip)

    def _test_current_ip(self):
        """Test a single IP address"""
        try:
            # Increment total scans counter
            Clock.schedule_once(lambda dt: self._increment_total_scans(), 0)

            # Perform ping test with current timeout setting
            success, ping_result = ping_test(self.current_ip, timeout=self.ping_timeout)

            if success:
                # Get country info if enabled
                country = "Unknown"
                if self._enable_country_lookup:
                    country = get_country_from_ip(self.current_ip)

                # Filter by country if specified
                if self.country_filter and self.country_filter.lower() not in country.lower():
                    return

                # Update scan status
                status_update = f"Success: {self.current_ip} - Ping: {ping_result} - Country: {country}\n"

                # Add to results list
                result = {
                    'ip': self.current_ip,
                    'ping': ping_result,
                    'country': country
                }

                # Update UI in main thread
                Clock.schedule_once(lambda dt: self._update_success_result(status_update, result), 0)
            else:
                # Update scan status for failed ping
                status_update = f"Failed: {self.current_ip} - {ping_result}\n"
                self.add_status_update(status_update)

        except Exception as e:
            status_update = f"Error during scan: {str(e)}\n"
            self.add_status_update(status_update)

    async def _test_multiple_ips_async(self, count=10):
        """Test multiple IPs in parallel using asyncio for better performance."""
        try:
            # Generate multiple random IPs with filters
            ips = [
                generate_random_ip(
                    min_octet1=self.min_octet1, 
                    max_octet1=self.max_octet1, 
                    exclude_private=self.exclude_private
                ) for _ in range(count)
            ]

            # Update status with batch start
            self.add_status_update(f"Testing batch of {count} IPs...\n")

            # Test them all concurrently with current timeout settings
            tasks = [async_ping_test(ip, timeout=self.ping_timeout) for ip in ips]
            results = await asyncio.gather(*tasks)

            # Process results
            for i, (success, ping_result) in enumerate(results):
                # Increment total counter
                Clock.schedule_once(lambda dt: self._increment_total_scans(), 0)

                ip = ips[i]

                if success:
                    # Get country info if enabled
                    country = "Unknown"
                    if self._enable_country_lookup:
                        # Use async version when possible
                        if self._event_loop and not self._event_loop.is_closed():
                            country = await get_country_from_ip_async(ip)
                        else:
                            # Fallback to sync version
                            country_future = self.executor.submit(get_country_from_ip, ip)
                            country = country_future.result()

                    # Filter by country if specified
                    if self.country_filter and self.country_filter.lower() not in country.lower():
                        continue

                    # Update scan status
                    status_update = f"Success: {ip} - Ping: {ping_result} - Country: {country}\n"

                    # Add to results list
                    result = {
                        'ip': ip,
                        'ping': ping_result,
                        'country': country
                    }

                    # Update UI in main thread
                    Clock.schedule_once(
                        lambda dt, r=result, s=status_update: self._update_success_result(s, r), 
                        0
                    )
                else:
                    # Update scan status for failed ping (with less frequency for performance)
                    if random.random() < 0.2:  # Only log about 20% of failures to reduce spam
                        status_update = f"Failed: {ip} - {ping_result}\n"
                        self.add_status_update(status_update)

        except Exception as e:
            self.add_status_update(f"Error during async scan: {str(e)}\n")

    def _increment_total_scans(self):
        """Increment total scan counter and update progress"""
        self.total_scans += 1
        self._update_progress()

    def _increment_successful_scans(self):
        """Increment successful scan counter and update progress"""
        self.successful_scans += 1
        self._update_progress()

    def _update_progress(self):
        """Update progress bar"""
        # Update progress if we have scans
        if self.total_scans > 0:
            # Calculate progress percentage (success rate)
            self.scan_progress_value = (self.successful_scans / max(1, self.total_scans)) * 100

    def _update_success_result(self, status_text, result):
        """Handle successful scan result"""
        # Update scan status
        self.add_status_update(status_text)

        # Increment successful scan counter
        self._increment_successful_scans()

        # Add to results grid
        with self.results_lock:
            results_grid = self.ids.results_grid
            row = ResultRow()
            row.ip_address = result['ip']
            row.ping_result = result['ping'] 
            row.country = result['country']

            # Add to beginning for newest-first ordering
            results_grid.add_widget(row, index=len(results_grid.children))

            # Limit results to prevent memory issues
            max_results = 200
            if len(results_grid.children) > max_results:
                # Remove oldest results
                while len(results_grid.children) > max_results:
                    results_grid.remove_widget(results_grid.children[0])

    def clear_results(self):
        """Clear all results from the grid"""
        with self.results_lock:
            self.ids.results_grid.clear_widgets()
            self.add_status_update("Results cleared.\n")

    def export_results(self):
        """Export results to a file"""
        try:
            with self.results_lock:
                results = []
                for child in reversed(self.ids.results_grid.children):
                    results.append({
                        'ip': child.ip_address,
                        'ping': child.ping_result,
                        'country': child.country
                    })

            if not results:
                self.add_status_update("No results to export.\n")
                return

            # Determine export path based on platform
            if is_mobile():
                # On mobile, save to app directory
                export_path = os.path.join(App.get_running_app().user_data_dir, "ip_scan_results.txt")
            else:
                # On desktop, save to current directory
                export_path = os.path.join(os.getcwd(), "ip_scan_results.txt")

            # Write results to file
            with open(export_path, 'w') as f:
                f.write("IP Address,Ping,Country\n")
                for result in results:
                    f.write(f"{result['ip']},{result['ping']},{result['country']}\n")

            self.add_status_update(f"Results exported to: {export_path}\n")

            # Show confirmation popup
            from kivy.uix.popup import Popup
            from kivy.uix.label import Label
            popup = Popup(
                title='Export Completed',
                content=Label(text=f'Results exported to:\n{export_path}'),
                size_hint=(0.8, 0.3)
            )
            popup.open()
            # Auto close after 3 seconds
            Clock.schedule_once(lambda dt: popup.dismiss(), 3)

        except Exception as e:
            self.add_status_update(f"Export failed: {str(e)}\n")

class IPScannerApp(App):
    title = 'DNS Finder IPv4'

    # App settings
    enable_country_lookup = True
    enable_sound = False
    ping_timeout = 3
    min_octet1 = 0
    max_octet1 = 255
    exclude_private = False
    country_filter = ""

    def build(self):
        # Load settings first
        self.load_settings()

        # Create main layout with padding to fix the empty space issue
        layout = BoxLayout(orientation='vertical', padding=[0, 0, 0, 0])

        # Add main app
        main_app = IPApp()
        layout.add_widget(main_app)

        # Add footer
        footer = Label(
            text='Created by Goje Pro Max',
            size_hint_y=None,
            height='40dp',
            color=(0.7, 0.7, 0.7, 1),
            font_size='14sp',
            halign='center',
            valign='middle'
        )
        footer.bind(size=footer.setter('text_size'))
        layout.add_widget(footer)

        # Add settings and filter buttons
        header_box = main_app.children[-1]  # First box in the main app layout

        # Create a container for buttons to ensure proper alignment
        buttons_container = BoxLayout(
            orientation='horizontal',
            size_hint=(None, None),
            size=(100, 50),
            pos_hint={'right': 0.99, 'top': 0.99},
            spacing=10
        )

        # Create settings button
        settings_button = Button(
            text='⚙️',
            size_hint=(None, None),
            size=(50, 50),
            background_color=(0.3, 0.3, 0.3, 1)
        )
        settings_button.bind(on_release=lambda x: self.open_settings_popup())
        buttons_container.add_widget(settings_button)

        # Add filter button
        filter_button = Button(
            text='🔍',
            size_hint=(None, None),
            size=(50, 50),
            background_color=(0.3, 0.3, 0.3, 1)
        )
        filter_button.bind(on_release=lambda x: self.open_filter_popup())
        buttons_container.add_widget(filter_button)

        # Add the container to the header
        header_box.add_widget(buttons_container)

        # Mobile detection and configuration
        if is_mobile():
            # Mobile-specific adjustments
            Window.softinput_mode = 'below_target'  # Move window content up when keyboard appears
            Config.set('graphics', 'resizable', 0)
            # Use full screen on mobile
            Window.fullscreen = 'auto'

            # Adjust for mobile screens
            from kivy.metrics import dp
            Window.clearcolor = (0.1, 0.1, 0.12, 1)

            # Additional mobile adjustments
            main_app.padding = dp(10)
            main_app.spacing = dp(8)
        else:
            # Desktop sizing
            Window.size = (700, 730)

        return layout

    def on_start(self):
        """Handle application startup"""
        # Set up error handling
        if not is_mobile():  # Skip for mobile to avoid permission issues
            try:
                # Setup logging to file
                import logging
                log_path = os.path.join(self.user_data_dir, 'app_log.txt')
                logging.basicConfig(
                    filename=log_path,
                    level=logging.ERROR,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                )
            except Exception:
                pass  # Silent fail if logging setup fails

    def on_stop(self):
        """Clean up resources when the app is closed"""
        # Get main app reference
        for child in self.root.children:
            if isinstance(child, IPApp):
                # Stop scanning if running
                if child.scanning:
                    child.stop_scanning()
                # Close thread pool properly
                if hasattr(child, 'executor'):
                    child.executor.shutdown(wait=False)
                break

    def save_settings(self):
        """Save settings to file"""
        try:
            import json
            settings = {
                'enable_country_lookup': self.enable_country_lookup,
                'enable_sound': self.enable_sound,
                'ping_timeout': self.ping_timeout,
                'min_octet1': self.min_octet1,
                'max_octet1': self.max_octet1,
                'exclude_private': self.exclude_private,
                'country_filter': self.country_filter
            }

            settings_path = os.path.join(self.user_data_dir, 'settings.json')
            with open(settings_path, 'w') as f:
                json.dump(settings, f)
        except Exception as e:
            print(f"Failed to save settings: {e}")

    def load_settings(self):
        """Load settings from file"""
        try:
            import json
            settings_path = os.path.join(self.user_data_dir, 'settings.json')

            if os.path.exists(settings_path):
                with open(settings_path, 'r') as f:
                    settings = json.load(f)

                # Apply loaded settings
                self.enable_country_lookup = settings.get('enable_country_lookup', True)
                self.enable_sound = settings.get('enable_sound', False)
                self.ping_timeout = settings.get('ping_timeout', 3)
                self.min_octet1 = settings.get('min_octet1', 0)
                self.max_octet1 = settings.get('max_octet1', 255)
                self.exclude_private = settings.get('exclude_private', False)
                self.country_filter = settings.get('country_filter', "")

                # Update the main app if it exists
                for child in self.root.children if hasattr(self, 'root') and self.root else []:
                    if isinstance(child, IPApp):
                        child._enable_country_lookup = self.enable_country_lookup
                        child.ping_timeout = self.ping_timeout
                        child.min_octet1 = self.min_octet1
                        child.max_octet1 = self.max_octet1
                        child.exclude_private = self.exclude_private
                        child.country_filter = self.country_filter
                        break
        except Exception as e:
            print(f"Failed to load settings: {e}")

    def open_settings_popup(self):
        """Open settings popup"""
        try:
            from kivy.uix.popup import Popup
            from kivy.uix.boxlayout import BoxLayout
            from kivy.uix.button import Button
            from kivy.uix.switch import Switch
            from kivy.uix.label import Label
            from kivy.uix.slider import Slider

            # Create settings layout
            layout = BoxLayout(orientation='vertical', spacing=10, padding=10)

            # Add settings options
            # Enable/disable country lookup
            country_row = BoxLayout(size_hint_y=None, height='50dp')
            country_row.add_widget(Label(text='Country Lookup', size_hint_x=0.7))
            country_switch = Switch(active=self.enable_country_lookup)
            country_switch.bind(active=lambda instance, value: setattr(self, 'enable_country_lookup', value))
            country_row.add_widget(country_switch)
            layout.add_widget(country_row)

            # Enable/disable sound notifications
            sound_row = BoxLayout(size_hint_y=None, height='50dp')
            sound_row.add_widget(Label(text='Sound Notifications', size_hint_x=0.7))
            sound_switch = Switch(active=self.enable_sound)
            sound_switch.bind(active=lambda instance, value: setattr(self, 'enable_sound', value))
            sound_row.add_widget(sound_switch)
            layout.add_widget(sound_row)

            # Ping timeout slider
            timeout_layout = BoxLayout(orientation='vertical', size_hint_y=None, height='80dp')
            timeout_label = Label(text=f'Ping Timeout: {self.ping_timeout}s')
            timeout_layout.add_widget(timeout_label)
            timeout_slider = Slider(min=1, max=10, value=self.ping_timeout, step=1)
            timeout_slider.bind(value=lambda instance, value: self._update_timeout(timeout_label, value))
            timeout_layout.add_widget(timeout_slider)
            layout.add_widget(timeout_layout)

            # Save button
            save_button = Button(text='Save Settings', size_hint_y=None, height='50dp')
            save_button.bind(on_release=lambda x: self._save_and_close_settings(popup))
            layout.add_widget(save_button)

            # Create and open popup
            popup = Popup(title='Settings', content=layout, size_hint=(0.9, 0.7))
            popup.open()
        except Exception as e:
            print(f"Failed to open settings: {e}")

    def _update_timeout(self, label, value):
        """Update timeout setting and label"""
        self.ping_timeout = int(value)
        label.text = f'Ping Timeout: {self.ping_timeout}s'

    def _save_and_close_settings(self, popup):
        """Save settings and close popup"""
        # Save settings
        self.save_settings()

        # Update the main app
        for child in self.root.children:
            if isinstance(child, IPApp):
                child._enable_country_lookup = self.enable_country_lookup
                child.ping_timeout = self.ping_timeout
                break

        # Close popup
        popup.dismiss()

    def open_filter_popup(self):
        """Open filter settings popup"""
        try:
            from kivy.uix.popup import Popup
            from kivy.uix.boxlayout import BoxLayout
            from kivy.uix.button import Button
            from kivy.uix.textinput import TextInput
            from kivy.uix.label import Label
            from kivy.uix.checkbox import CheckBox

            # Create filter layout
            layout = BoxLayout(orientation='vertical', spacing=10, padding=10)

            # IP range input
            layout.add_widget(Label(text='IP Range Filter', size_hint_y=None, height='30dp'))

            # First octet range
            octet1_layout = BoxLayout(size_hint_y=None, height='40dp')
            octet1_layout.add_widget(Label(text='First octet range:', size_hint_x=0.4))

            min_octet1 = TextInput(
                text=str(self.min_octet1), 
                input_filter='int', 
                multiline=False, 
                size_hint_x=0.3
            )
            octet1_layout.add_widget(min_octet1)

            octet1_layout.add_widget(Label(text='to', size_hint_x=0.1))

            max_octet1 = TextInput(
                text=str(self.max_octet1), 
                input_filter='int', 
                multiline=False, 
                size_hint_x=0.3
            )
            octet1_layout.add_widget(max_octet1)
            layout.add_widget(octet1_layout)

            # Exclude private IPs
            private_layout = BoxLayout(size_hint_y=None, height='40dp')
            private_layout.add_widget(Label(text='Exclude private IPs:', size_hint_x=0.7))
            exclude_private = CheckBox(active=self.exclude_private)
            private_layout.add_widget(exclude_private)
            layout.add_widget(private_layout)

            # Country filter
            country_layout = BoxLayout(size_hint_y=None, height='40dp')
            country_layout.add_widget(Label(text='Filter by country:', size_hint_x=0.4))
            country_filter = TextInput(text=self.country_filter, multiline=False, size_hint_x=0.6)
            country_layout.add_widget(country_filter)
            layout.add_widget(country_layout)

            # Apply button
            apply_button = Button(text='Apply Filters', size_hint_y=None, height='50dp')
            apply_button.bind(on_release=lambda x: self._apply_filters(
                popup, min_octet1, max_octet1, exclude_private, country_filter
            ))
            layout.add_widget(apply_button)

            # Create and open popup
            popup = Popup(title='IP Filters', content=layout, size_hint=(0.9, 0.7))
            popup.open()
        except Exception as e:
            print(f"Failed to open filter settings: {e}")

    def _apply_filters(self, popup, min_octet1, max_octet1, exclude_private, country_filter):
        """Apply IP filter settings"""
        try:
            # Get values from inputs
            min_val = int(min_octet1.text)
            max_val = int(max_octet1.text)

            # Validate ranges
            min_val = max(0, min(255, min_val))
            max_val = max(0, min(255, max_val))

            # Ensure min <= max
            if min_val > max_val:
                min_val, max_val = max_val, min_val

            # Update settings
            self.min_octet1 = min_val
            self.max_octet1 = max_val
            self.exclude_private = exclude_private.active
            self.country_filter = country_filter.text

            # Save settings
            self.save_settings()

            # Update main app
            for child in self.root.children:
                if isinstance(child, IPApp):
                    child.min_octet1 = self.min_octet1
                    child.max_octet1 = self.max_octet1
                    child.exclude_private = self.exclude_private
                    child.country_filter = self.country_filter
                    break

            # Show confirmation
            from kivy.uix.popup import Popup
            from kivy.uix.label import Label
            confirm = Popup(
                title='Filters Applied',
                content=Label(text='IP filter settings have been updated.'),
                size_hint=(0.8, 0.2)
            )
            confirm.open()
            # Auto close after 2 seconds
            Clock.schedule_once(lambda dt: confirm.dismiss(), 2)

            # Close filter popup
            popup.dismiss()
        except ValueError:
            # Show error for invalid input
            from kivy.uix.popup import Popup
            from kivy.uix.label import Label
            error = Popup(
                title='Invalid Input',
                content=Label(text='Please enter valid numbers for IP range.'),
                size_hint=(0.8, 0.2)
            )
            error.open()
            # Auto close after 2 seconds
            Clock.schedule_once(lambda dt: error.dismiss(), 2)

def on_pause():
    """Handle application pause (for mobile)"""
    # Keep app running when paused on mobile
    return True

def on_resume():
    """Handle application resume (for mobile)"""
    # Check internet status when resuming
    app = App.get_running_app()
    for child in app.root.children:
        if isinstance(child, IPApp):
            child.check_internet_connectivity(0)
            break
    return True

def catch_exceptions(exc_type, exc_value, exc_traceback):
    """Global exception handler to log uncaught exceptions"""
    import logging
    import traceback
    logging.error("Uncaught exception", 
                 exc_info=(exc_type, exc_value, exc_traceback))
    # Print to console as well
    print("".join(traceback.format_exception(exc_type, exc_value, exc_traceback)))
    return True  # Prevent default exception handler

if __name__ == "__main__":
    try:
        # Set up global exception handler
        import sys
        sys.excepthook = catch_exceptions

        # Run the application
        IPScannerApp().run()
    except Exception as e:
        print(f"Application error: {e}")
        import traceback
        traceback.print_exc()