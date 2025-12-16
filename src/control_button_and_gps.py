import Jetson.GPIO as GPIO
import requests
import threading
import time

# --- CẤU HÌNH ---
BUTTON_PIN = 29  # Board Pin 29
LED_PIN = 31     # Board Pin 31
# URL API chính của bạn (ví dụ server nhận cảnh báo)
MAIN_API_URL = "https://httpbin.org/get" 
# URL dịch vụ lấy tọa độ miễn phí (IP Geolocation)
GEO_API_URL = "http://ip-api.com/json/"

# Biến toàn cục bộ đếm thời gian
led_timer = None

def setup():
    """Cấu hình GPIO"""
    GPIO.setmode(GPIO.BOARD)
    GPIO.setup(LED_PIN, GPIO.OUT, initial=GPIO.LOW)
    # LƯU Ý: Jetson Nano không hỗ trợ pull_up_down bằng phần mềm ổn định.
    # Bạn NÊN lắp điện trở kéo lên 10kΩ bên ngoài cho nút nhấn.
    GPIO.setup(BUTTON_PIN, GPIO.IN) 

def turn_off_led_task():
    """Hàm tắt đèn sau 30s"""
    print("⏳ [Timer] Đã hết 30s, tắt đèn LED.")
    GPIO.output(LED_PIN, GPIO.LOW)

# --- HÀM MỚI THÊM: LẤY TỌA ĐỘ ---
def get_coordinates():
    """Lấy tọa độ Latitude, Longitude dựa trên IP mạng"""
    print("📍 Đang lấy dữ liệu địa lý...")
    try:
        # Gọi đến dịch vụ IP Geolocation (timeout 3s để tránh chờ lâu)
        response = requests.get(GEO_API_URL, timeout=3)
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'success':
                lat = data.get('lat')
                lon = data.get('lon')
                city = data.get('city')
                return lat, lon, city
            else:
                print(f"⚠️ Lỗi dịch vụ địa lý: {data.get('message')}")
        else:
             print(f"⚠️ Lỗi HTTP địa lý: {response.status_code}")
    except Exception as e:
        print(f"❌ Không thể kết nối dịch vụ địa lý: {e}")
    
    # Trả về None nếu thất bại
    return None, None, None

def handle_button_press():
    """Hàm xử lý chính khi nhấn nút"""
    global led_timer
    
    print("\n-----------------------------------")
    print("🟢 PHÁT HIỆN NHẤN NÚT! Bắt đầu xử lý...")
    
    # BƯỚC 1: Lấy và Log tọa độ ra màn hình
    lat, lon, city = get_coordinates()
    if lat is not None:
        print(f"✅ TỌA ĐỘ HIỆN TẠI: Thành phố: {city} | Lat: {lat}, Lon: {lon}")
        # (Tùy chọn) Bạn có thể gửi kèm tọa độ này vào MAIN_API_URL nếu muốn
        # payload = {'lat': lat, 'lon': lon}
    else:
        print("⚠️ Không lấy được tọa độ. Tiếp tục các bước sau.")

    # BƯỚC 2: Gọi API chính tới Server
    print(f"📡 Đang gọi API chính: {MAIN_API_URL} ...")
    try:
        # Nếu muốn gửi kèm tọa độ, thêm params=payload vào dòng dưới
        response = requests.get(MAIN_API_URL, timeout=5)
        
        if response.status_code == 200:
            print("✅ Server chính phản hồi OK (200).")
            
            # BƯỚC 3: Xử lý đèn LED và Timer
            print("💡 Bật đèn LED.")
            GPIO.output(LED_PIN, GPIO.HIGH)
            
            # Reset timer nếu đang chạy
            if led_timer is not None:
                print("Put lại bộ đếm thời gian cũ.")
                led_timer.cancel()
            
            # Tạo timer mới 30s
            led_timer = threading.Timer(30.0, turn_off_led_task)
            led_timer.start()
            print("⏳ Đã đặt lịch tắt đèn sau 30s.")
            
        else:
            print(f"⚠️ Server chính lỗi: Mã {response.status_code}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Lỗi kết nối tới Server chính: {e}")
    print("-----------------------------------\n")

def main():
    setup()
    print("🚀 Hệ thống sẵn sàng. Nhấn nút để thực hiện chuỗi tác vụ...")
    # Nhắc nhở quan trọng về phần cứng
    print("⚠️ LƯU Ý: Nếu hệ thống tự chạy khi không nhấn, hãy lắp thêm điện trở kéo lên (Pull-up resistor) 10kΩ cho nút nhấn.")
    
    try:
        while True:
            # Chờ cạnh xuống (khi bắt đầu nhấn)
            GPIO.wait_for_edge(BUTTON_PIN, GPIO.FALLING)
            
            # Chống rung (Debounce)
            time.sleep(0.2) # Chờ 200ms
            
            # Kiểm tra lại trạng thái nút.
            # Nếu vẫn là LOW thì mới coi là một lần nhấn hợp lệ.
            if GPIO.input(BUTTON_PIN) == GPIO.LOW: 
                handle_button_press()
                # Chờ nút nhả ra để tránh gọi liên tục (tùy chọn)
                # while GPIO.input(BUTTON_PIN) == GPIO.LOW: time.sleep(0.1)

    except KeyboardInterrupt:
        print("\nĐang thoát chương trình...")
    finally:
        if led_timer is not None:
            led_timer.cancel()
        GPIO.cleanup()

if __name__ == "__main__":
    main()