import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
import datetime
import threading
import time

class FirebaseService:
    def __init__(self, cred_path, device_id="jetson-nano-1", audio_service=None):
        self.device_id = device_id
        self.audio_service = audio_service
        self.db = None
        self.linked_user_id = None
        self.user_listener = None
        self.histories_listener = None
        
        # Initialize Firebase
        try:
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
            self.db = firestore.client()
            print("[FirebaseService] Initialized successfully.")
        except Exception as e:
            print(f"[FirebaseService] Error initializing: {e}")
            raise e

    def initialize_device(self):
        """Creates or updates the device document."""
        doc_ref = self.db.collection("devices").document(self.device_id)
        
        try:
            doc = doc_ref.get()
            
            device_data = {
                "deviceId": self.device_id,
                "deviceInfo": {
                    "model": "Jetson Nano",
                    "version": "1.0.0"
                }
            }
            
            if doc.exists:
                current_data = doc.to_dict()
                # Preserve existing fields if they exist, else set default
                if "linkedUserId" not in current_data:
                    device_data["linkedUserId"] = None
                
                if "linkedAt" not in current_data:
                    device_data["linkedAt"] = None
                    
                if "status" not in current_data:
                    device_data["status"] = "deactivate"
                
                # We merge to update deviceInfo but keep others if they exist (or set defaults if missing)
                # Actually, user said: "nếu như lúc chạy lên có dữ liệu thì giữ nguyên dữ liệu còn chưa có thì mặc định là null"
                # So we only set defaults if they are MISSING.
                # The merge=True in set() will update provided fields and keep others.
                # But we want to ensure defaults are set if missing.
                
                # Let's prepare the update dict
                update_data = {
                    "deviceId": self.device_id,
                    "deviceInfo": {
                        "model": "Jetson Nano",
                        "version": "1.0.0"
                    }
                }
                # Check and set defaults if missing in DB
                if "linkedUserId" not in current_data:
                    update_data["linkedUserId"] = None
                if "linkedAt" not in current_data:
                    update_data["linkedAt"] = None
                if "status" not in current_data:
                    update_data["status"] = "deactivate"
                    
                doc_ref.set(update_data, merge=True)
                print(f"[FirebaseService] Device {self.device_id} updated.")
                
            else:
                # New document
                device_data["linkedUserId"] = None
                device_data["linkedAt"] = None
                device_data["status"] = "deactivate"
                doc_ref.set(device_data)
                print(f"[FirebaseService] Device {self.device_id} created.")
                
        except Exception as e:
            print(f"[FirebaseService] Error initializing device: {e}")

    def start_listening(self):
        """Starts listening to device changes."""
        doc_ref = self.db.collection("devices").document(self.device_id)
        self.user_listener = doc_ref.on_snapshot(self._on_device_snapshot)
        print(f"[FirebaseService] Listening for changes on device {self.device_id}...")

    def _on_device_snapshot(self, doc_snapshot, changes, read_time):
        for doc in doc_snapshot:
            data = doc.to_dict()
            new_linked_user_id = data.get("linkedUserId")
            
            if new_linked_user_id != self.linked_user_id:
                self.linked_user_id = new_linked_user_id
                print(f"[FirebaseService] Linked User ID changed to: {self.linked_user_id}")
                
                # If we have a user, start listening to their histories
                if self.linked_user_id:
                    self._fetch_user_info()
                    self._listen_to_histories()
                else:
                    # Stop listening if unlinked
                    if self.histories_listener:
                        self.histories_listener.unsubscribe()
                        self.histories_listener = None
                        print("[FirebaseService] Unlinked. Stopped listening to histories.")

    def _fetch_user_info(self):
        try:
            user_doc = self.db.collection("users").document(self.linked_user_id).get()
            if user_doc.exists:
                print(f"[FirebaseService] User Info: {user_doc.to_dict()}")
            else:
                print(f"[FirebaseService] User {self.linked_user_id} not found in 'users' collection.")
        except Exception as e:
            print(f"[FirebaseService] Error fetching user info: {e}")

    def _listen_to_histories(self):
        if self.histories_listener:
            self.histories_listener.unsubscribe()
            
        histories_ref = self.db.collection("users").document(self.linked_user_id).collection("histories")
        # Listen for new additions
        self.histories_listener = histories_ref.on_snapshot(self._on_histories_snapshot)
        print(f"[FirebaseService] Listening to histories for user {self.linked_user_id}...")

    def _on_histories_snapshot(self, col_snapshot, changes, read_time):
        for change in changes:
            if change.type.name == 'ADDED':
                data = change.document.to_dict()
                print(f"[FirebaseService] New history added: {data}")
                
                behavior = data.get("behavior")
                priority = data.get("priority")
                level = data.get("level")
                
                if behavior and priority is not None:
                    if self.audio_service:
                        # Ensure priority is int
                        try:
                            priority = int(priority)
                        except:
                            pass
                        self.audio_service.play_sound(behavior, level, priority)
