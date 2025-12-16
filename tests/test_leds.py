import Jetson.GPIO as GPIO
import time

# Pin definition
PINS = [32, 33, 35, 36, 37]

def test_leds():
    print("Checking GPIO setup...")
    try:
        GPIO.setmode(GPIO.BOARD)
        GPIO.setup(PINS, GPIO.OUT, initial=GPIO.LOW)
    except Exception as e:
        print(f"Error initializing GPIO: {e}")
        return

    print("Starting LED Test Sequence...")
    print("Press Ctrl+C to stop.\n")

    try:
        # Round 1: Individual Check
        for pin in PINS:
            print(f"Testing Pin {pin} (ON)...")
            GPIO.output(pin, GPIO.HIGH)
            time.sleep(1)
            GPIO.output(pin, GPIO.LOW)
            time.sleep(0.5)
        
        # Round 2: All ON
        print("Turning ALL LEDs ON...")
        GPIO.output(PINS, GPIO.HIGH)
        time.sleep(2)
        print("Turning ALL LEDs OFF...")
        GPIO.output(PINS, GPIO.LOW)
        
        print("\nTest Complete!")

    except KeyboardInterrupt:
        print("\nTest interrupted.")
    finally:
        GPIO.cleanup()
        print("GPIO Cleaned up.")

if __name__ == "__main__":
    test_leds()
