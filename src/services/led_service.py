try:
    import Jetson.GPIO as GPIO
except ImportError:
    # Check if we are potentially on a system that supports it but it's just missing, 
    # or if we are on Windows where it definitely won't work well (unless using a specific windows fork).
    # Since the user is testing on Windows, a mock is helpful.
    print("[LedService] Jetson.GPIO not found or failed to import. Using Mock GPIO.")
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
        def setup(*args, **kwargs): print(f"[MockGPIO] setup {args} {kwargs}")
        @staticmethod
        def output(pin, value): print(f"[MockGPIO] output pin={pin} val={value}")
        @staticmethod
        def cleanup(): print("[MockGPIO] cleanup")
        @staticmethod
        def wait_for_edge(*args): pass
        @staticmethod
        def input(*args): return 0
import threading
import time

class LedService:
    def __init__(self):
        # Map filenames to GPIO pins (BOARD mode)
        self.pins_map = {
            "sleepy_eye_level_1_and_yawn.wav": 32,
            "sleepy_eye_level_2.wav": 33,
            "sleepy_eye_level_3.wav": 35,
            "phone.wav": 36,
            "look_away.wav": 37
        }
        self.all_pins = list(self.pins_map.values())
        
        self.is_blinking = False
        self.blink_thread = None
        self.lock = threading.Lock()
        
        # Initialize GPIO
        try:
            GPIO.setmode(GPIO.BOARD)
            for pin in self.all_pins:
                GPIO.setup(pin, GPIO.OUT, initial=GPIO.LOW)
            print("[LedService] Initialized GPIO pins: ", self.all_pins)
        except Exception as e:
            print(f"[LedService] GPIO Init Error: {e}")

    def turn_on_file(self, filename):
        """Turns on the LED corresponding to the filename, turns others off."""
        self.stop_blinking()
        
        target_pin = self.pins_map.get(filename)
        if not target_pin:
            print(f"[LedService] No pin mapped for file: {filename}")
            self.turn_off_all()
            return

        with self.lock:
            for pin in self.all_pins:
                if pin == target_pin:
                    GPIO.output(pin, GPIO.HIGH)
                else:
                    GPIO.output(pin, GPIO.LOW)
        
        print(f"[LedService] Turned ON pin {target_pin} for {filename}")

    def turn_off_all(self):
        """Turns off all mapped LEDs."""
        with self.lock:
            for pin in self.all_pins:
                GPIO.output(pin, GPIO.LOW)

    def start_blinking(self):
        """Starts blinking all LEDs (for TTS)."""
        if self.is_blinking:
            return
            
        print("[LedService] Starting blink mode...")
        self.is_blinking = True
        self.blink_thread = threading.Thread(target=self._blink_loop)
        self.blink_thread.daemon = True
        self.blink_thread.start()

    def stop_blinking(self):
        """Stops the blinking thread."""
        if not self.is_blinking:
            return
            
        self.is_blinking = False
        if self.blink_thread and self.blink_thread.is_alive():
            self.blink_thread.join(timeout=1.0)
        self.blink_thread = None
        self.turn_off_all()
        print("[LedService] Stopped blink mode.")

    def _blink_loop(self):
        """Thread loop for blinking."""
        state = GPIO.HIGH
        while self.is_blinking:
            with self.lock:
                for pin in self.all_pins:
                    GPIO.output(pin, state)
            
            # Use small sleeps to check stop condition frequently
            for _ in range(5): # 0.5s total (5 * 0.1)
                if not self.is_blinking: break
                time.sleep(0.1)
            
            state = GPIO.LOW if state == GPIO.HIGH else GPIO.HIGH
        
        # Ensure off when exiting loop
        self.turn_off_all()

    def cleanup(self):
        self.stop_blinking()
        try:
            GPIO.cleanup()
            print("[LedService] GPIO Cleaned up.")
        except:
            pass
