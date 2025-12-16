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
        # Order for chase effect: 32 -> 33 -> 35 -> 36 -> 37
        self.sorted_pins = sorted(self.all_pins)
        
        self.is_running_effect = False
        self.effect_thread = None
        self.lock = threading.Lock()
        
        # Initialize GPIO
        try:
            cur_mode = GPIO.getmode()
            if cur_mode is None:
                GPIO.setmode(GPIO.BOARD)
            elif cur_mode != GPIO.BOARD:
                print(f"[LedService] Warning: GPIO mode is {cur_mode}, expected BOARD ({GPIO.BOARD})")
                # Attempt to set it anyway or trust it? Safer to try setting or erroring.
                # If we are sharing with something else setting BCM, we are in trouble.
                # Asking for BOARD.
                try:
                     GPIO.setmode(GPIO.BOARD)
                except Exception as e:
                     print(f"[LedService] Could not switch mode: {e}")

            for pin in self.all_pins:
                GPIO.setup(pin, GPIO.OUT, initial=GPIO.LOW)
            
            # CRITICAL: Ensure all lights are OFF immediately on startup
            self.turn_off_all()
            
            print("[LedService] Initialized GPIO pins: ", self.all_pins)
        except Exception as e:
            print(f"[LedService] GPIO Init Error: {e}")

    def turn_on_file(self, filename):
        """Turns on the LED corresponding to the filename, turns others off."""
        self.stop_effect()
        
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
        try:
            with self.lock:
                for pin in self.all_pins:
                    GPIO.output(pin, GPIO.HIGH) # According to some active-low setups, but usually LOW is OFF.
                    # Wait, user said "cắm điện vào thì các đèn lại sáng lên" -> implies they might be active LOW or just floating HIGH.
                    # BUT usually GPIO.LOW is 0V (OFF).
                    # If the user says "plug in and they light up", maybe the initialized state was wrong or they are Active LOW relays?
                    # "phát sáng đèn tương ứng là được" -> indicates positive logic usually.
                    # Let's assume High=On, Low=Off.
                    # If they were ON at startup, maybe GPIO.setup defaults?
                    # The previous code had `initial=GPIO.LOW`.
                    # I will stick to LOW = OFF.
                    GPIO.output(pin, GPIO.LOW)
        except Exception as e:
            print(f"[LedService] Error turning off: {e}")

    def start_chasing(self):
        """Starts the running light (chase) effect for TTS."""
        if self.is_running_effect:
            return
            
        print("[LedService] Starting chase effect...")
        self.is_running_effect = True
        self.effect_thread = threading.Thread(target=self._chase_loop)
        self.effect_thread.daemon = True
        self.effect_thread.start()

    def stop_effect(self):
        """Stops any running effect (blink/chase)."""
        if not self.is_running_effect:
            return
            
        self.is_running_effect = False
        if self.effect_thread and self.effect_thread.is_alive():
            self.effect_thread.join(timeout=1.0)
        self.effect_thread = None
        self.turn_off_all()
        print("[LedService] Stopped effect.")

    def _chase_loop(self):
        """Thread loop for chase effect."""
        idx = 0
        while self.is_running_effect:
            target_pin = self.sorted_pins[idx]
            
            with self.lock:
                for pin in self.all_pins:
                    # Only the target pin is ON, others OFF
                    GPIO.output(pin, GPIO.HIGH if pin == target_pin else GPIO.LOW)
            
            # Speed of chase: 0.1s per LED
            for _ in range(2): # 0.1s total (2 * 0.05)
                if not self.is_running_effect: break
                time.sleep(0.05)
            
            idx = (idx + 1) % len(self.sorted_pins)
        
        # Ensure off when exiting loop
        self.turn_off_all()

    def cleanup(self):
        self.stop_effect()
        try:
            GPIO.cleanup()
            print("[LedService] GPIO Cleaned up.")
        except:
            pass
