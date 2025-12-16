import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
import time
import datetime

# Config
CRED_PATH = r"src/configs/lucky-union-472503-c7-firebase-adminsdk-fbsvc-708fc927d9.json"
DEVICE_ID = "jetson-nano-iot-test"
USER_ID = "test_user_sim"

def main():
    print("Starting Simulation...")
    
    # Initialize Firebase
    try:
        cred = credentials.Certificate(CRED_PATH)
        firebase_admin.initialize_app(cred)
        db = firestore.client()
        print("[Sim] Firebase initialized.")
    except Exception as e:
        print(f"[Sim] Error initializing Firebase: {e}")
        return

    # 1. Create/Update User
    print(f"[Sim] Creating/Updating user {USER_ID}...")
    user_ref = db.collection("users").document(USER_ID)
    user_ref.set({
        "username": "Test User Simulation",
        "createdAt": datetime.datetime.now()
    }, merge=True)

    # 2. Link Device
    print(f"[Sim] Linking device {DEVICE_ID} to {USER_ID}...")
    device_ref = db.collection("devices").document(DEVICE_ID)
    device_ref.set({
        "linkedUserId": USER_ID,
        "status": "activate",
        "linkedAt": datetime.datetime.now().isoformat()
    }, merge=True)
    
    print("[Sim] Device linked. Waiting 15 seconds for main app to pick it up...")
    time.sleep(15)

    # 3. Mock Behaviors
    histories_ref = user_ref.collection("histories")

    # Scenario 1: Yawn (Priority 3)
    print("[Sim] Adding Behavior: Yawn (Priority 3)")
    histories_ref.add({
        "behavior": "yawn",
        "priority": 3,
        "level": 1,
        "timestamp": datetime.datetime.now()
    })
    print("[Sim] Waiting 5 seconds...")
    time.sleep(5)

    # Scenario 2: Phone (Priority 2) - Should interrupt Yawn if it was playing (or just play)
    print("[Sim] Adding Behavior: Phone (Priority 2)")
    histories_ref.add({
        "behavior": "phone",
        "priority": 2,
        "level": 1,
        "timestamp": datetime.datetime.now()
    })
    print("[Sim] Waiting 5 seconds...")
    time.sleep(5)

    # Scenario 3: Sleepy Eye (Priority 1) - Should interrupt Phone
    print("[Sim] Adding Behavior: Sleepy Eye (Priority 1, Level 3)")
    histories_ref.add({
        "behavior": "sleepy_eye",
        "priority": 1,
        "level": 3,
        "timestamp": datetime.datetime.now()
    })
    print("[Sim] Waiting 5 seconds...")
    time.sleep(5)

    # Scenario 4: Look Away (Priority 2) - Should NOT interrupt Sleepy Eye (Priority 1)
    print("[Sim] Adding Behavior: Look Away (Priority 2)")
    histories_ref.add({
        "behavior": "look_away",
        "priority": 2,
        "level": 1,
        "timestamp": datetime.datetime.now()
    })
    
    print("[Sim] Simulation steps completed.")

if __name__ == "__main__":
    main()
