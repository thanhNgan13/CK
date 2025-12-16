import pygame
import os
import threading

class AudioService:
    def __init__(self, assets_path="assets/audios", led_service=None):
        self.assets_path = assets_path
        self.led_service = led_service
        self.current_priority = float('inf')
        self.lock = threading.Lock()
        
        # Initialize pygame mixer
        pygame.mixer.init()
        
        # Map behavior and level to filenames
        # behavior: { level: filename } or just filename if no level
        # Based on user description:
        # behavior: sleepy_eye (has levels), yawn, phone, look_away
        self.audio_map = {
            "sleepy_eye": {
                "1": "sleepy_eye_level_1_and_yawn.wav",
                "2": "sleepy_eye_level_2.wav",
                "3": "sleepy_eye_level_3.wav"
            },
            "yawn": "sleepy_eye_level_1_and_yawn.wav", # Assuming shared based on filename
            "phone": "phone.wav",
            "look_away": "look_away.wav"
        }

    def _get_audio_path(self, behavior, level=None):
        filename = None
        if behavior == "sleepy_eye":
            filename = self.audio_map.get(behavior, {}).get(str(level))
        else:
            filename = self.audio_map.get(behavior)
            
        if filename:
            return os.path.join(self.assets_path, filename)
        return None

    def play_sound(self, behavior, level, priority):
        """
        Plays sound if priority is higher (lower value) than current playing sound.
        """
        with self.lock:
            print(f"[AudioService] Request to play: {behavior}, level={level}, priority={priority}")
            
            # Check if busy and priority comparison
            if pygame.mixer.music.get_busy():
                if priority < self.current_priority:
                    print(f"[AudioService] Interrupting current sound (p={self.current_priority}) for new sound (p={priority})")
                    pygame.mixer.music.stop()
                else:
                    print(f"[AudioService] Ignoring new sound (p={priority}) as it is not higher priority than current (p={self.current_priority})")
                    return

            audio_path = self._get_audio_path(behavior, level)
            if not audio_path or not os.path.exists(audio_path):
                print(f"[AudioService] Error: Audio file not found for {behavior} level {level} at {audio_path}")
                self.current_priority = float('inf')
                return

            try:
                pygame.mixer.music.load(audio_path)
                pygame.mixer.music.play()
                
                # Turn on LED for this file
                if self.led_service:
                    filename = os.path.basename(audio_path)
                    print(f"[AudioService] LED Request: Turn on for {filename}")
                    self.led_service.turn_on_file(filename)
                
                # Check for special case: sleepy_eye level 3 -> queue stop_car_warning
                if behavior == "sleepy_eye" and str(level) == "3":
                    warning_path = os.path.join(self.assets_path, "stop_car_warning.wav")
                    if os.path.exists(warning_path):
                        print(f"[AudioService] Queuing warning sound: {warning_path}")
                        pygame.mixer.music.queue(warning_path)
                    else:
                        print(f"[AudioService] Warning sound not found at {warning_path}")

                self.current_priority = priority
                # Reset priority when done? 
                # Ideally we'd want to know when it finishes to reset priority, 
                # but for now, next play will check get_busy().
                # If get_busy() is false, we can treat current_priority as effectively reset (or we logic it out).
                # Actually, if !get_busy(), we should allow any priority.
            except Exception as e:
                print(f"[AudioService] Error playing sound: {e}")
                self.current_priority = float('inf')

    def check_status(self):
        """Optional: Reset priority if music stopped playing naturally"""
        with self.lock:
            if not pygame.mixer.music.get_busy():
                self.current_priority = float('inf')
                # Ensure LEDs are off if audio stopped
                if self.led_service:
                    self.led_service.stop_effect()
                    self.led_service.turn_off_all()

    def speak(self, text, priority=0, lang='vi'):
        """
        Generates TTS audio and plays it.
        """
        from gtts import gTTS
        import tempfile
        
        with self.lock:
            print(f"[AudioService] Request to speak: '{text}' (p={priority})")
            
            if pygame.mixer.music.get_busy():
                if priority < self.current_priority:
                     print(f"[AudioService] Interrupting current sound for TTS")
                     pygame.mixer.music.stop()
                else:
                     print(f"[AudioService] TTS ignored due to lower priority")
                     return

            try:
                # Generate TTS
                tts = gTTS(text=text, lang=lang)
                
                # Save to a named temp file that we can read
                # gTTS write_to_fp might be better but pygame needs a file usually
                # On windows, tempfile with delete=True sometimes causes permission issues if still open
                # So we use delete=False and generic name?
                # Or just use a fixed temp file name in assets maybe to be safe on Windows?
                # Let's try tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
                
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
                temp_path = temp_file.name
                temp_file.close() # Close so gTTS can write to it
                
                tts.save(temp_path)
                
                
                if self.led_service:
                    self.led_service.start_chasing()
                
                pygame.mixer.music.load(temp_path)
                pygame.mixer.music.play()
                
                self.current_priority = priority
                
                # We can't easily delete the file while it's playing in pygame on Windows.
                # It might remain until next restart or be overwritten. 
                # For this simple project, letting OS clean temp or overwriting same path is acceptable.
                
            except Exception as e:
                print(f"[AudioService] Error in speak: {e}")
                self.current_priority = float('inf')
