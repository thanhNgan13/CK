import Jetson.GPIO as GPIO
import requests
import threading
import time

# --- CẤU HÌNH ---
BUTTON_PIN = 29  # Chân số 29 trên board
LED_PIN = 31     # Chân số 31 trên board
API_URL = "https://httpbin.org/get" # URL ví dụ (server giả lập), hãy thay bằng API thật của bạn

# Biến toàn cục để quản lý bộ đếm thời gian tắt đèn
led_timer = None

def setup():
    # Sử dụng chế độ đánh số chân theo BOARD (số vật lý trên mạch)
    GPIO.setmode(GPIO.BOARD)
    
    # Cấu hình LED là OUTPUT, mặc định tắt (LOW)
    GPIO.setup(LED_PIN, GPIO.OUT, initial=GPIO.LOW)
    
    # Cấu hình Button là INPUT, dùng điện trở kéo lên (PULL_UP)
    # Khi không nhấn = HIGH, Khi nhấn = LOW
    GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

def turn_off_led_task():
    """Hàm này sẽ được gọi sau 30s"""
    print("⏳ Đã hết 30s, tắt đèn LED.")
    GPIO.output(LED_PIN, GPIO.LOW)

def call_api_and_handle_led():
    global led_timer
    
    print("📡 Đang gọi API...")
    try:
        # Gửi request (giả sử là GET, bạn có thể đổi thành POST)
        response = requests.get(API_URL, timeout=5)
        
        # Kiểm tra nếu Server trả về thành công (HTTP 200)
        if response.status_code == 200:
            print("✅ Server phản hồi OK. Bật đèn LED!")
            
            # Bật đèn ngay lập tức
            GPIO.output(LED_PIN, GPIO.HIGH)
            
            # LOGIC QUAN TRỌNG:
            # Nếu đang có một bộ đếm tắt đèn cũ đang chạy, hãy hủy nó đi
            # để tính lại 30s từ thời điểm phản hồi MỚI NHẤT.
            if led_timer is not None:
                led_timer.cancel()
            
            # Tạo bộ đếm mới: Sau 30s sẽ chạy hàm turn_off_led_task
            led_timer = threading.Timer(30.0, turn_off_led_task)
            led_timer.start()
            
        else:
            print(f"⚠️ Server lỗi: {response.status_code}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Lỗi kết nối: {e}")

def main():
    setup()
    print("🚀 Hệ thống sẵn sàng. Nhấn nút để gửi request...")
    
    try:
        while True:
            # Chờ sự kiện nhấn nút (cạnh xuống - falling edge)
            # Dùng wait_for_edge giúp tiết kiệm CPU hơn vòng lặp while liên tục
            GPIO.wait_for_edge(BUTTON_PIN, GPIO.FALLING)
            
            # Xử lý chống rung phím (Debounce) đơn giản bằng cách chờ 200ms
            time.sleep(0.2)
            if GPIO.input(BUTTON_PIN) == GPIO.LOW: # Kiểm tra lại xem có thực sự đang nhấn không
                call_api_and_handle_led()
                
    except KeyboardInterrupt:
        print("\nĐang thoát chương trình...")
    finally:
        # Dọn dẹp GPIO khi thoát để tránh lỗi cho lần chạy sau
        if led_timer is not None:
            led_timer.cancel()
        GPIO.cleanup()

if __name__ == "__main__":
    main()