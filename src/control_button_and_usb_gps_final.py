import Jetson.GPIO as GPIO
import requests
import threading
import time
import serial
import pynmea2
import json # Import thêm thư viện json để in log cho đẹp

# ==========================================
# --- CẤU HÌNH CHÍNH (QUAN TRỌNG) ---
# ==========================================
BUTTON_PIN = 29   # Board Pin 29 (Nút nhấn)
LED_PIN = 31      # Board Pin 31 (Đèn LED)

# 1. Cấu hình API Server THẬT
MAIN_API_URL = "https://iotapi.chathub.info.vn/api/alerts/create"
# Đặt ID định danh cho Jetson Nano này (Server sẽ biết tin nhắn từ đâu tới)
DEVICE_ID = "jetson-nano-iot" 

# 2. Cấu hình USB GPS (Ưu tiên 1)
GPS_PORT = '/dev/ttyACM0' 
GPS_BAUDRATE = 9600 
GPS_TIMEOUT = 2     
GPS_MAX_READ_LINES = 30 

# 3. Cấu hình IP Geolocation (Ưu tiên 2 - Fallback)
IP_GEO_URL = "http://ip-api.com/json/"


# Biến toàn cục bộ đếm thời gian
led_timer = None

# ==========================================
# CÁC HÀM HỖ TRỢ (GPIO, Timer)
# ==========================================
def setup():
    """Cấu hình GPIO"""
    GPIO.setmode(GPIO.BOARD)
    GPIO.setup(LED_PIN, GPIO.OUT, initial=GPIO.LOW)
    # LƯU Ý: Vẫn cần điện trở kéo lên 10kΩ ngoài cho chân 29.
    GPIO.setup(BUTTON_PIN, GPIO.IN)

def turn_off_led_task():
    """Hàm tự động tắt đèn sau 30s"""
    print("⏳ [Timer] Đã hết 30s, tắt đèn LED.")
    GPIO.output(LED_PIN, GPIO.LOW)

# ==========================================
# CÁC HÀM LẤY TỌA ĐỘ (GPS -> IP)
# ==========================================
def get_gps_coordinates():
    """ƯU TIÊN 1: Đọc dữ liệu từ USB GPS."""
    print(f"🛰️ [GPS] Đang kết nối tới {GPS_PORT}...")
    ser = None
    try:
        ser = serial.Serial(GPS_PORT, GPS_BAUDRATE, timeout=GPS_TIMEOUT)
        print(f"   -> Kết nối OK. Đang chờ tín hiệu vệ tinh ({GPS_MAX_READ_LINES} dòng)...")
        for i in range(GPS_MAX_READ_LINES):
            try:
                line = ser.readline().decode('utf-8', errors='ignore').strip()
                if line.startswith(('$GNGGA', '$GPGGA')):
                    msg = pynmea2.parse(line)
                    if msg.gps_qual > 0:
                        print(f"   -> ✅ [GPS] Fix thành công tại dòng {i+1}!")
                        return msg.latitude, msg.longitude, 'USB_GPS'
            except pynmea2.ParseError: continue
        print(f"❌ [GPS] Không bắt được tọa độ (ví dụ: ở trong nhà).")
    except Exception as e: print(f"❌ [GPS] Lỗi: {e}")
    finally:
        if ser and ser.is_open: ser.close()
    return None, None, None

def get_ip_coordinates():
    """ƯU TIÊN 2 (Fallback): Lấy tọa độ qua IP mạng."""
    print("🌐 [IP Fallback] Đang thử lấy tọa độ qua IP...")
    try:
        response = requests.get(IP_GEO_URL, timeout=4)
        if response.status_code == 200 and response.json().get('status') == 'success':
            data = response.json()
            print(f"   -> ✅ [IP Fallback] Thành công! Khu vực: {data.get('city')}")
            return data.get('lat'), data.get('lon'), 'IP_Geo'
    except Exception as e: print(f"   -> ❌ [IP Fallback] Lỗi: {e}")
    return None, None, None

# ==========================================
# XỬ LÝ CHÍNH (Thay đổi lớn ở đây)
# ==========================================
def handle_button_press():
    global led_timer
    print("\n" + "="*50)
    print("🟢 PHÁT HIỆN NHẤN NÚT! Bắt đầu quy trình...")
    
    # --- BƯỚC 1: Lấy tọa độ thực tế (Có Fallback) ---
    lat, lon, source = get_gps_coordinates()
    if lat is None:
        print("\n⚠️ Chuyển sang phương án dự phòng...")
        lat, lon, source = get_ip_coordinates()

    # Xác định giá trị cuối cùng để gửi. 
    # Nếu cả 2 cách đều thất bại, ta gửi 0.0 để đảm bảo đúng định dạng JSON API yêu cầu.
    final_lat = lat if lat is not None else 0.0
    final_lon = lon if lon is not None else 0.0
    final_source = source if source is not None else "Unknown"

    if lat is not None:
        print(f"\n✅ TỌA ĐỘ THỰC TẾ (Nguồn: {source}): Lat: {final_lat:.6f}, Lon: {final_lon:.6f}")
    else:
        print(f"\n❌ CẢNH BÁO: Không lấy được tọa độ. Sẽ gửi giá trị mặc định {final_lat},{final_lon}")


    # --- BƯỚC 2: Chuẩn bị Payload JSON đúng cấu trúc Server yêu cầu ---
    # Cấu trúc này khớp với lệnh curl bạn cung cấp
    api_payload = {
      "deviceId": DEVICE_ID,
      "location": {
        "latitude": final_lat,
        "longitude": final_lon
      },
      # (Tùy chọn) Gửi thêm nguồn gốc dữ liệu để server biết độ tin cậy
      "metadata": {
          "source": final_source
      }
    }

    # --- BƯỚC 3: Gọi API THẬT bằng phương thức POST ---
    print(f"\n📡 Đang gửi POST Request tới: {MAIN_API_URL} ...")
    # In ra payload để debug (dùng json.dumps cho dễ nhìn)
    print(f"   Payload gửi đi: {json.dumps(api_payload, indent=2)}")
        
    try:
        # QUAN TRỌNG: Sử dụng requests.post và tham số json=
        # Tham số json= sẽ tự động:
        # 1. Chuyển đổi dictionary 'api_payload' thành chuỗi JSON.
        # 2. Thêm header 'Content-Type: application/json' vào request.
        response = requests.post(MAIN_API_URL, json=api_payload, timeout=10)
        
        print(f"👉 Server phản hồi Mã: {response.status_code}")
        
        # Kiểm tra các mã thành công phổ biến (200 OK, 201 Created)
        if response.status_code in [200, 201]:
            print("✅ Gửi cảnh báo THÀNH CÔNG!")
            try:
                 print(f"   Server trả về: {response.json()}")
            except: pass # Phòng trường hợp server không trả về JSON
            
            # --- Xử lý đèn LED ---
            print("💡 Bật đèn LED báo hiệu.")
            GPIO.output(LED_PIN, GPIO.HIGH)
            if led_timer is not None: led_timer.cancel()
            led_timer = threading.Timer(30.0, turn_off_led_task)
            led_timer.start()
            print("⏳ Đã đặt lịch tắt đèn sau 30s.")
            
        else:
            # In ra nội dung lỗi từ server nếu có
            print(f"⚠️ Thất bại. Nội dung phản hồi: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Lỗi kết nối mạng: {e}")
    print("="*50 + "\n")

# ==========================================
# VÒNG LẶP CHÍNH
# ==========================================
def main():
    setup()
    print("\n---------------------------------------------------")
    print(f"🚀 HỆ THỐNG IoT SẴN SÀNG - Device ID: {DEVICE_ID}")
    print(f"ℹ️  API Mục tiêu: {MAIN_API_URL} (POST)")
    print("⚠️  LƯU Ý PHẦN CỨNG: Đảm bảo đã lắp điện trở kéo lên 10kΩ.")
    print("👉 HÃY NHẤN NÚT ĐỂ GỬI CẢNH BÁO THỰC TẾ.")
    print("---------------------------------------------------\n")
    try:
        while True:
            GPIO.wait_for_edge(BUTTON_PIN, GPIO.FALLING)
            time.sleep(0.2)
            if GPIO.input(BUTTON_PIN) == GPIO.LOW: 
                handle_button_press()
    except KeyboardInterrupt:
        print("\nĐang thoát...")
    finally:
        if led_timer is not None: led_timer.cancel()
        GPIO.cleanup()

if __name__ == "__main__":
    main()