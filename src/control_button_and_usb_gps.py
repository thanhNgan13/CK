import Jetson.GPIO as GPIO
import requests
import threading
import time
import serial
import pynmea2

# --- CẤU HÌNH CHÍNH ---
BUTTON_PIN = 29   # Board Pin 29 (Nút nhấn)
LED_PIN = 31      # Board Pin 31 (Đèn LED)
# URL API nhận dữ liệu (Server của bạn)
MAIN_API_URL = "https://httpbin.org/get"

# --- CẤU HÌNH GPS ---
# Đây là cổng bạn vừa tìm được
GPS_PORT = '/dev/ttyACM0' 
GPS_BAUDRATE = 9600 # Tốc độ mặc định phổ biến của U-Blox GPS
GPS_TIMEOUT = 2     # Thời gian chờ đọc tối đa (giây)

# Biến toàn cục bộ đếm thời gian
led_timer = None

def setup():
    """Cấu hình GPIO"""
    GPIO.setmode(GPIO.BOARD)
    GPIO.setup(LED_PIN, GPIO.OUT, initial=GPIO.LOW)
    
    # --- NHẮC LẠI QUAN TRỌNG VỀ PHẦN CỨNG ---
    # Jetson Nano không hỗ trợ tốt điện trở kéo lên nội bộ.
    # Để nút nhấn hoạt động ổn định, không bị nhiễu (tự nhấn),
    # bạn BẮT BUỘC phải lắp thêm điện trở kéo lên (pull-up resistor)
    # khoảng 10kΩ nối giữa chân 3.3V (Pin 1) và chân tín hiệu (Pin 29).
    GPIO.setup(BUTTON_PIN, GPIO.IN)

def turn_off_led_task():
    """Hàm tự động tắt đèn sau 30s"""
    print("⏳ [Timer] Đã hết 30s, tắt đèn LED.")
    GPIO.output(LED_PIN, GPIO.LOW)

# --- HÀM ĐỌC DỮ LIỆU TỪ USB GPS ---
def get_gps_coordinates():
    """Mở cổng serial, đọc dữ liệu NMEA và trích xuất tọa độ."""
    print(f"🛰️ Đang kết nối tới GPS tại {GPS_PORT}...")
    ser = None
    try:
        # Mở kết nối tới cổng USB GPS
        ser = serial.Serial(GPS_PORT, GPS_BAUDRATE, timeout=GPS_TIMEOUT)
        print("   -> Kết nối thành công. Đang chờ dữ liệu vệ tinh (Fix)...")
        
        # Đọc thử 30 dòng dữ liệu để tìm dòng chứa tọa độ hợp lệ
        # Nếu ở trong nhà, việc này có thể mất thời gian hoặc không bắt được.
        for i in range(30):
            try:
                # Đọc một dòng và giải mã (decode) thành text
                line = ser.readline().decode('utf-8', errors='ignore').strip()
                
                # Chỉ xử lý các dòng bắt đầu bằng $GNGGA (GPS+GLONASS) hoặc $GPGGA (chỉ GPS)
                # Đây là các dòng chứa thông tin vị trí và chất lượng tín hiệu.
                if line.startswith(('$GNGGA', '$GPGGA')):
                    # Dùng thư viện pynmea2 để phân tích dòng text
                    msg = pynmea2.parse(line)
                    
                    # Kiểm tra 'gps_qual' (Chất lượng tín hiệu). 
                    # > 0 nghĩa là đã bắt được vệ tinh và tọa độ hợp lệ.
                    if msg.gps_qual > 0:
                        lat = msg.latitude
                        lon = msg.longitude
                        print(f"   -> ✅ Đã bắt được tín hiệu (Fix) tại dòng thứ {i+1}!")
                        return lat, lon
                    else:
                        # Nếu gps_qual = 0, nghĩa là đang tìm vệ tinh (thường thấy khi ở trong nhà)
                        if i % 5 == 0: # In bớt log cho đỡ rối
                            print(f"   -> ⚠️ Đang dò tìm vệ tinh... (Chất lượng: {msg.gps_qual})")
                            
            except pynmea2.ParseError:
                continue # Bỏ qua nếu dòng dữ liệu bị lỗi

        print("❌ Không bắt được tọa độ hợp lệ sau khi đọc 30 dòng. (Có thể do ở trong nhà kín).")

    except serial.SerialException as e:
        print(f"❌ Lỗi kết nối thiết bị GPS: {e}")
        print("👉 Kiểm tra: Đã cắm chặt USB chưa? Đã chạy bằng 'sudo' chưa?")
    except Exception as e:
        print(f"❌ Lỗi không xác định: {e}")
    finally:
        # Luôn nhớ đóng cổng serial sau khi dùng xong
        if ser and ser.is_open:
            ser.close()
            
    # Trả về None nếu thất bại
    return None, None

def handle_button_press():
    """Hàm xử lý chính khi nút được nhấn"""
    global led_timer
    
    print("\n" + "="*40)
    print("🟢 PHÁT HIỆN NHẤN NÚT! Bắt đầu quy trình...")
    
    # --- BƯỚC 1: Lấy tọa độ từ GPS ---
    lat, lon = get_gps_coordinates()
    
    payload = {} # Biến chứa dữ liệu sẽ gửi đi
    if lat is not None and lon is not None:
        print(f"📍 TỌA ĐỘ THU ĐƯỢC: Vĩ độ (Lat): {lat:.6f}, Kinh độ (Lon): {lon:.6f}")
        # Đóng gói tọa độ vào dictionary để gửi kèm request
        payload = {'latitude': lat, 'longitude': lon}
    else:
        print("⚠️ Cảnh báo: Không lấy được tọa độ GPS. Vẫn tiếp tục gọi API nhưng không có vị trí.")

    # --- BƯỚC 2: Gọi API chính tới Server ---
    print(f"📡 Đang gửi dữ liệu tới Server: {MAIN_API_URL} ...")
    if payload:
        print(f"   (Kèm dữ liệu: {payload})")
        
    try:
        # Gửi GET request, truyền tọa độ vào tham số 'params'
        # Nếu dùng POST, hãy đổi thành: requests.post(MAIN_API_URL, data=payload, timeout=10)
        response = requests.get(MAIN_API_URL, params=payload, timeout=10)
        
        if response.status_code == 200:
            print("✅ Server phản hồi THÀNH CÔNG (200 OK).")
            
            # --- BƯỚC 3: Xử lý đèn LED và Hẹn giờ ---
            print("💡 Bật đèn LED báo hiệu.")
            GPIO.output(LED_PIN, GPIO.HIGH)
            
            # Nếu có bộ đếm cũ đang chạy thì hủy nó
            if led_timer is not None:
                print("   -> Hủy bộ đếm thời gian cũ.")
                led_timer.cancel()
            
            # Tạo bộ đếm mới: 30 giây sau sẽ tắt đèn
            led_timer = threading.Timer(30.0, turn_off_led_task)
            led_timer.start()
            print("⏳ Đã đặt lịch tắt đèn sau 30 giây tính từ bây giờ.")
            
        elif response.status_code == 503:
             print("⚠️ Server đang bận (503 Service Unavailable). Hãy thử lại sau.")
        else:
            print(f"⚠️ Server trả về lỗi: Mã {response.status_code}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Không thể kết nối tới Server: {e}")
    print("="*40 + "\n")

def main():
    setup()
    print("\n---------------------------------------------------")
    print("🚀 HỆ THỐNG IoT SẴN SÀNG HOẠT ĐỘNG!")
    print(f"ℹ️  Cổng GPS mục tiêu: {GPS_PORT}")
    print("⚠️  LƯU Ý: Đảm bảo đã lắp điện trở kéo lên (Pull-up resistor) 10kΩ cho nút nhấn.")
    print("👉 HÃY NHẤN NÚT để lấy tọa độ GPS và gửi về server.")
    print("---------------------------------------------------\n")
    
    try:
        while True:
            # Chờ sự kiện nhấn nút (cạnh xuống)
            GPIO.wait_for_edge(BUTTON_PIN, GPIO.FALLING)
            
            # Chống rung (Debounce) đơn giản
            time.sleep(0.2)
            
            # Kiểm tra lại xem nút có thực sự đang được giữ không
            if GPIO.input(BUTTON_PIN) == GPIO.LOW: 
                handle_button_press()

    except KeyboardInterrupt:
        print("\nĐang thoát chương trình...")
    finally:
        # Dọn dẹp khi thoát
        if led_timer is not None:
            led_timer.cancel()
        GPIO.cleanup()
        print("Đã dọn dẹp GPIO.")

if __name__ == "__main__":
    main()