import threading
import time
import json
import requests
import serial
import pynmea2
import os

try:
    import Jetson.GPIO as GPIO
except ImportError:
    print("[SosService] Jetson.GPIO not found. Using Mock.")
    class GPIO:
        BOARD = 'BOARD'
        OUT = 'OUT'
        IN = 'IN' 
        LOW = 0
        HIGH = 1
        FALLING = 'FALLING'
        @staticmethod
        def setmode(*args): pass
        @staticmethod
        def setup(*args, **kwargs): pass
        @staticmethod
        def output(*args): pass
        @staticmethod
        def input(*args): return 1
        @staticmethod
        def wait_for_edge(*args): time.sleep(1)
        @staticmethod
        def cleanup(): pass

class SosService:
    def __init__(self, device_id="jetson-nano-iot"):
        self.device_id = device_id
        
        # Hardware Config
        self.BUTTON_PIN = 29
        self.LED_PIN = 31
        
        # API Config
        self.MAIN_API_URL = "https://iotapi.chathub.info.vn/api/alerts/create"
        
        # GPS Config
        self.GPS_PORT = '/dev/ttyACM0'
        self.GPS_BAUDRATE = 9600
        self.GPS_TIMEOUT = 2
        self.GPS_MAX_READ_LINES = 30
        
        # IP Geo Config
        self.IP_GEO_URL = "http://ip-api.com/json/"
        
        self.running = False
        self.thread = None
        self.led_timer = None
        
        # Init GPIO
        try:
            GPIO.setmode(GPIO.BOARD)
            # Input button with pull-up resistor (hardware)
            GPIO.setup(self.BUTTON_PIN, GPIO.IN) 
            # Status LED
            GPIO.setup(self.LED_PIN, GPIO.OUT, initial=GPIO.LOW)
            print("[SosService] GPIO Initialized.")
        except Exception as e:
            print(f"[SosService] GPIO Init Error: {e}")

    def start(self):
        """Starts the button monitoring thread."""
        if self.running:
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._monitor_loop)
        self.thread.daemon = True
        self.thread.start()
        print("[SosService] Started monitoring thread.")

    def stop(self):
        """Stops the monitoring thread."""
        self.running = False
        if self.led_timer:
            self.led_timer.cancel()
        
        # Note: wait_for_edge is blocking, so the thread might not exit immediately 
        # until the next event or timeout if configured. 
        # For this simple implementation, we rely on daemon thread to be killed on main exit.
        print("[SosService] Stopping service...")

    def _monitor_loop(self):
        print("[SosService] Waiting for button press...")
        while self.running:
            try:
                # Basic debounce/edge detection
                # Using wait_for_edge with a small timeout would be better to allow checking self.running,
                # but Jetson.GPIO's wait_for_edge might not support timeout on all versions smoothly.
                # We will block here. If usage is high, we can change to polling or event callbacks.
                GPIO.wait_for_edge(self.BUTTON_PIN, GPIO.FALLING)
                
                # Debounce
                time.sleep(0.2)
                if GPIO.input(self.BUTTON_PIN) == GPIO.LOW:
                    self._handle_button_press()
                    
            except Exception as e:
                # If wait_for_edge fails (e.g. on mock), sleep to prevent CPU spin
                print(f"[SosService] Monitor loop error: {e}")
                time.sleep(1)

    def _turn_off_led(self):
        print("[SosService] Timer done, turning off LED.")
        try:
            GPIO.output(self.LED_PIN, GPIO.LOW)
        except:
             pass

    def _get_gps_coordinates(self):
        """Try USB GPS."""
        print(f"[SosService] Connecting to GPS {self.GPS_PORT}...")
        ser = None
        try:
            ser = serial.Serial(self.GPS_PORT, self.GPS_BAUDRATE, timeout=self.GPS_TIMEOUT)
            for i in range(self.GPS_MAX_READ_LINES):
                try:
                    line = ser.readline().decode('utf-8', errors='ignore').strip()
                    if line.startswith(('$GNGGA', '$GPGGA')):
                        msg = pynmea2.parse(line)
                        if msg.gps_qual > 0:
                            return msg.latitude, msg.longitude, 'USB_GPS'
                except pynmea2.ParseError: continue
        except Exception as e:
            print(f"[SosService] GPS Error: {e}")
        finally:
            if ser and ser.is_open: ser.close()
        return None, None, None

    def _get_ip_coordinates(self):
        """Fallback to IP Geolocation."""
        print("[SosService] Trying IP Geolocation...")
        try:
            response = requests.get(self.IP_GEO_URL, timeout=4)
            if response.status_code == 200 and response.json().get('status') == 'success':
                data = response.json()
                return data.get('lat'), data.get('lon'), 'IP_Geo'
        except Exception as e:
            print(f"[SosService] IP Geo Error: {e}")
        return None, None, None

    def _handle_button_press(self):
        print("\n" + "="*40)
        print("[SosService] 🟢 SOS BUTTON PRESSED!")
        
        # 1. Get Location
        lat, lon, source = self._get_gps_coordinates()
        if lat is None:
            lat, lon, source = self._get_ip_coordinates()
            
        final_lat = lat if lat is not None else 0.0
        final_lon = lon if lon is not None else 0.0
        final_source = source if source is not None else "Unknown"
        
        print(f"[SosService] Location: {final_lat}, {final_lon} (Source: {final_source})")

        # 2. Payload
        api_payload = {
          "deviceId": self.device_id,
          "location": {
            "latitude": final_lat,
            "longitude": final_lon
          },
          "metadata": {
              "source": final_source
          }
        }

        # 3. Send API
        print(f"[SosService] Sending Alert to {self.MAIN_API_URL}...")
        try:
            response = requests.post(self.MAIN_API_URL, json=api_payload, timeout=10)
            print(f"[SosService] Status Code: {response.status_code}")
            
            if response.status_code in [200, 201]:
                print("[SosService] ✅ SOS Sent Successfully!")
                
                # Turn ON LED
                GPIO.output(self.LED_PIN, GPIO.HIGH)
                
                # Schedule OFF
                if self.led_timer:
                    self.led_timer.cancel()
                self.led_timer = threading.Timer(30.0, self._turn_off_led)
                self.led_timer.start()
            else:
                print(f"[SosService] ⚠️ Failed: {response.text}")
                
        except Exception as e:
            print(f"[SosService] ❌ Network Error: {e}")
        print("="*40 + "\n")
