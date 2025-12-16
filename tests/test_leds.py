import Jetson.GPIO as GPIO
import time
from gtts import gTTS
import pygame
import os
import tempfile

# Pin definition
PINS = [32, 33, 35, 36, 37]

def speak(text):
    """Generates and plays TTS audio."""
    try:
        print(f"[TTS] {text}")
        tts = gTTS(text=text, lang='vi')
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as fp:
            temp_path = fp.name
            tts.save(temp_path)
        
        pygame.mixer.music.load(temp_path)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
             time.sleep(0.1)
        
        # Clean up
        pygame.mixer.music.unload() # Ensure file is released
        try:
            os.remove(temp_path)
        except:
            pass
    except Exception as e:
        print(f"[TTS Error] {e}")

def test_leds():
    print("Checking GPIO setup...")
    # Init Audio
    try:
        pygame.mixer.init()
    except Exception as e:
        print(f"Audio Init Failed: {e}")

    # Init GPIO
    try:
        GPIO.setmode(GPIO.BOARD)
        GPIO.setup(PINS, GPIO.OUT, initial=GPIO.LOW)
    except Exception as e:
        print(f"Error initializing GPIO: {e}")
        return

    print("Starting LED Test Sequence...")
    print("Press Ctrl+C to stop.\n")

    try:
        for i, pin in enumerate(PINS):
            text = f"Đang kiểm tra đèn thứ {i+1}, chân số {pin}"
            speak(text)
            
            print(f"--> Turning ON Pin {pin}")
            GPIO.output(pin, GPIO.HIGH)
            time.sleep(3) # Keep ON for 3 seconds to observe
            
            print(f"<-- Turning OFF Pin {pin}")
            GPIO.output(pin, GPIO.LOW)
            
            if i < len(PINS) - 1:
                print("Waiting 10s before next LED...")
                time.sleep(10)
        
        print("\nTest Complete!")
        speak("Đã hoàn thành kiểm tra")

    except KeyboardInterrupt:
        print("\nTest interrupted.")
    finally:
        GPIO.cleanup()
        print("GPIO Cleaned up.")

if __name__ == "__main__":
    test_leds()
