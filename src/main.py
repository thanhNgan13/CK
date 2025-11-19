import os
import time
import signal
import sys
from services.firebase_service import FirebaseService
from services.audio_service import AudioService

# Config
CRED_PATH = r"src/configs/lucky-union-472503-c7-firebase-adminsdk-fbsvc-708fc927d9.json"
ASSETS_PATH = r"assets/audios"

def main():
    print("Starting Device Client...")
    
    # Initialize Audio Service
    audio_service = AudioService(assets_path=ASSETS_PATH)
    
    # Initialize Firebase Service
    try:
        firebase_service = FirebaseService(cred_path=CRED_PATH, audio_service=audio_service)
        firebase_service.initialize_device()
        firebase_service.start_listening()
    except Exception as e:
        print(f"Failed to initialize Firebase Service: {e}")
        return

    print("Device Client Running. Press Ctrl+C to exit.")
    
    # Keep main thread alive
    try:
        while True:
            time.sleep(1)
            audio_service.check_status()
    except KeyboardInterrupt:
        print("\nStopping Device Client...")
        sys.exit(0)

if __name__ == "__main__":
    # Ensure we are running from the project root or adjust paths
    # The user seems to be running from d:\DUT_ITF\Semester_9th\IoT\CK
    # so relative paths should work if run from there.
    main()
