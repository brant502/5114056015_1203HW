import requests
import sqlite3
import random
import urllib3  # 用來關閉警告訊息
from datetime import datetime

# ==========================================
# 設定區
# ==========================================
# 這裡填入你的 API Key，如果沒有填，程式會自動切換到模擬模式
API_KEY = "CWA-1FFDDAEC-161F-46A3-BE71-93C32C52829F" 
DATA_ID = "O-A0001-001" 
API_URL = f"https://opendata.cwa.gov.tw/api/v1/rest/datastore/{DATA_ID}?Authorization={API_KEY}"
DB_NAME = "weather.db"

# 關閉「不安全連線」的警告訊息，讓畫面乾淨一點
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS temp_data (
            station_id TEXT PRIMARY KEY,
            name TEXT,
            city TEXT,
            town TEXT,
            obs_time TEXT,
            temperature REAL,
            lat REAL,
            lon REAL
        )
    ''')
    conn.commit()
    return conn

def generate_mock_data():
    """產生測試用的模擬資料 (當 API 失敗時使用)"""
    print("⚠️ 進入「模擬資料模式」(可能是 API Key 錯誤或連線被擋)...")
    
    mock_stations = [
        ("466920", "臺北", "臺北市", "中正區", 25.037, 121.514),
        ("466880", "板橋", "新北市", "板橋區", 24.997, 121.442),
        ("467571", "新竹", "新竹縣", "竹北市", 24.827, 121.014),
        ("467490", "臺中", "臺中市", "北區", 24.145, 120.683),
        ("467530", "阿里山", "嘉義縣", "阿里山鄉", 23.508, 120.813),
        ("467410", "臺南", "臺南市", "中西區", 22.993, 120.204),
        ("467440", "高雄", "高雄市", "前鎮區", 22.565, 120.313),
        ("466990", "花蓮", "花蓮縣", "花蓮市", 23.975, 121.613),
        ("467660", "臺東", "臺東縣", "臺東市", 22.752, 121.154),
        ("467080", "宜蘭", "宜蘭縣", "宜蘭市", 24.763, 121.756),
        ("466940", "基隆", "基隆市", "仁愛區", 25.133, 121.740),
        ("467350", "澎湖", "澎湖縣", "馬公市", 23.565, 119.563),
        ("467999", "墾丁", "屏東縣", "恆春鎮", 21.946, 120.797)
    ]
    
    data = []
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    for s_id, name, city, town, lat, lon in mock_stations:
        temp = round(random.uniform(18.0, 30.0), 1)
        if name == "阿里山":
            temp = round(random.uniform(8.0, 15.0), 1)
            
        data.append({
            "StationId": s_id,
            "StationName": name,
            "GeoInfo": {
                "CountyName": city,
                "TownName": town,
                "Coordinates": [{}, {"StationLatitude": lat, "StationLongitude": lon}]
            },
            "WeatherElement": {"AirTemperature": temp},
            "ObsTime": {"DateTime": current_time}
        })
    return {"records": {"Station": data}}

def fetch_data():
    """嘗試從 API 抓取"""
    print(f"嘗試連線 API: {API_URL}")
    try:
        # 關鍵修改：加入 verify=False 來略過 SSL 驗證
        response = requests.get(API_URL, timeout=5, verify=False)
        response.raise_for_status()
        data = response.json()
        
        if "records" not in data or "Station" not in data["records"]:
            raise ValueError("API 回傳格式不符")
            
        print("✅ API 連線成功！(已略過 SSL 驗證)")
        return data
        
    except Exception as e:
        # 如果還是失敗，或是 API Key 沒填，就會印出錯誤並切換到假資料
        print(f"❌ 連線失敗或 API Key 無效，改用模擬資料。錯誤訊息: {e}")
        return generate_mock_data()

def save_to_db(conn, data):
    if not data: return
    
    c = conn.cursor()
    stations = data['records']['Station']
    count = 0
    
    for s in stations:
        try:
            s_id = s['StationId']
            s_name = s['StationName']
            city = s['GeoInfo']['CountyName']
            town = s['GeoInfo']['TownName']
            
            coords = s['GeoInfo']['Coordinates']
            if isinstance(coords, list):
                lat = float(coords[1]['StationLatitude'])
                lon = float(coords[1]['StationLongitude'])
            else:
                continue

            temp = float(s['WeatherElement']['AirTemperature'])
            obs_time = s['ObsTime']['DateTime']
            
            c.execute('''
                REPLACE INTO temp_data (station_id, name, city, town, obs_time, temperature, lat, lon)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (s_id, s_name, city, town, obs_time, temp, lat, lon))
            count += 1
        except Exception:
            continue
            
    conn.commit()
    print(f"資料庫已更新 {count} 筆資料")

if __name__ == "__main__":
    conn = init_db()
    data = fetch_data()
    save_to_db(conn, data)
    conn.close()