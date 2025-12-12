# MQTT-based Intrusion Detection System for IoT Networks
**Hệ thống phát hiện xâm nhập cho mạng IoT sử dụng giao thức MQTT**

---

## 📖 Giới thiệu

Trong các hệ thống **IoT công nghiệp (Industrial IoT – IIoT)**, giao thức **MQTT (Message Queuing Telemetry Transport)** được sử dụng rộng rãi nhờ đặc tính nhẹ, tiết kiệm băng thông và phù hợp với các thiết bị có tài nguyên hạn chế. Tuy nhiên, MQTT **không được thiết kế với trọng tâm là bảo mật**, dẫn đến nhiều lỗ hổng nghiêm trọng trong môi trường triển khai thực tế như nhà máy thông minh.

Đồ án này xây dựng một **Hệ thống phát hiện xâm nhập (Intrusion Detection System – IDS)** cho mạng IoT sử dụng giao thức MQTT, hướng tới **môi trường Smart Factory**.

Hệ thống áp dụng mô hình **Hybrid IDS**, kết hợp:

- **Rule-based Detection**  
  Phát hiện các tấn công có dấu hiệu rõ ràng, tức thời (Flooding DoS, Malformed Data, Reconnect Storm…).

- **Machine Learning (Random Forest)**  
  Phát hiện các tấn công chậm, tinh vi và bất thường (Slow Brute-force, SlowITe…).

---

## 🏭 Ngữ cảnh Smart Factory

Hệ thống giả lập môi trường nhà máy thông minh gồm các phân khu:

- **🏭 Production Floor**: Cảm biến rung, bảo trì dự đoán, hệ thống thủy lực.  
- **⚡ Energy Management**: HVAC, quạt thông gió, cảm biến năng lượng.  
- **🏢 Office & IT**: Thiết bị và hệ thống văn phòng.  
- **🛡️ Security & Safety**: Báo cháy, cửa từ, camera an ninh.  
- **📦 Smart Storage**: Kho bãi thông minh, cảm biến môi trường.

Việc phân chia theo phân khu giúp mô phỏng lưu lượng IoT thực tế và đánh giá IDS trong nhiều ngữ cảnh khác nhau.

---

## 🏗 Kiến trúc hệ thống

```
IoT Simulators  ──MQTT TLS──▶  MQTT Broker (EMQX)
Attack Scripts  ──MQTT TLS──▶
                           │
                           ▼
                     Suricata IDS
                           │
                           ▼
                    Flow Forwarder
                           │
                           ▼
                      InfluxDB
                           │
                           ▼
                    Detection Engine
                           │
                           ▼
                   Dashboard / Email
```

### Thành phần chính

- **IoT Simulation**: Script replayer phát lại dữ liệu CSV lên Broker qua TLS.  
- **Attack Scripts**: 11 kịch bản tấn công MQTT.  
- **Suricata IDS**: Bắt lưu lượng mạng MQTT.  
- **Flow Forwarder**: Trích xuất Flow metadata.  
- **Detection Engine**: Rule-based + Machine Learning (Random Forest).  
- **Alerting**: Dashboard và Email.

---

## ⚙️ Cài đặt môi trường

### 1. Yêu cầu hệ thống

- OS: Ubuntu 20.04+ hoặc Windows (WSL2)  
- Python: 3.9+  
- Docker & Docker Compose  

### 2. Cài đặt thư viện Python

```bash
pip install -r requirements.txt
```

### 3. Cấu hình TLS

Đặt chứng chỉ CA tại:

```
certs/ca-cert.pem
```

### 4. Khởi chạy hạ tầng

```bash
docker-compose up -d
```

---

## 🚀 Chạy Giả lập (Simulation)

### Production Zone

```bash
python replayer_production.py --indir datasets --broker 10.12.112.191 --port 8883
```

### Energy Zone

```bash
python replayer_energy.py --indir datasets --broker 10.12.112.191 --port 8883
```

---

## ⚔️ Attack Simulation

### 🛡️ Rule-based Detectable Attacks

```bash
python Topic_Enumeration.py --broker 10.12.112.191 --port 8883 --username attacker --password 123
python Brute_Force.py --broker 10.12.112.191 --port 8883 --target-username admin --tls
python Duplicate_id.py --broker 10.12.112.191 --port 8883 --client-id target_device --username attacker --password 123
python Flooding_DoS.py --broker 10.12.112.191 --port 8883 --workers 10 --messages 2000
python Malformed_Data.py --broker 10.12.112.191 --port 8883 --username attacker --password 123
python Reconnect_Storm.py --broker 10.12.112.191 --port 8883 --type storm --workers 10 --reconnects 100
python Retain_Qos_Abuse.py --broker 10.12.112.191 --port 8883 --type mixed --username giamdoc --password 123
python Wildcard_Abuse.py --broker 10.12.112.191 --port 8883 --workers 5 --username attacker --password 123
```

### 🤖 Machine Learning Detectable Attacks

```bash
python Rotating_Brute_Force.py --broker 10.12.112.191 --port 8883 --target-username admin --tls
python Slow_Brute_Force.py --broker 10.12.112.191 --port 8883 --target-username admin --tls
python Slwit.py --host 10.12.112.191 --port 8883 --clients 50 --zombie --tls --username attacker --password 123
```

---

## 📂 Cấu trúc thư mục

```
mqtt-ids-project/
├── attack_scripts/
├── certs/
├── datasets/
├── ids_engine/
├── forwarder/
├── replayer_energy.py
├── replayer_production.py
├── docker-compose.yml
├── requirements.txt
└── README.md
```

---

## 📊 Kết quả đánh giá

- **Rule-based Detection**: Phát hiện 100% Flood, Malformed Data, Reconnect Storm (<1s).  
- **Machine Learning**: Random Forest phát hiện Slow Brute-force & SlowITe với độ chính xác >95%.  
- **Dashboard**: Hiển thị cảnh báo thời gian thực.

---

## 📌 Kết luận

Hệ thống IDS được xây dựng thành công cho mạng IoT sử dụng MQTT, kết hợp hiệu quả **Rule-based Detection** và **Machine Learning**, phù hợp triển khai trong môi trường **Smart Factory**.

