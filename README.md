# MQTT-based Intrusion Detection System for IoT Networks

## 📌 Thông tin đồ án

* **Tên đề tài**: Xây dựng hệ thống phát hiện xâm nhập (IDS) cho mạng IoT sử dụng giao thức MQTT
* **Loại đồ án**: Đồ án tốt nghiệp
* **Hướng tiếp cận**: Rule-based IDS kết hợp Machine Learning (Random Forest)
* **Ngữ cảnh ứng dụng**: Nhà máy thông minh (Smart Factory) với nhiều khu vực (Office, Production, Energy, Security, Storage)

---

## 📖 Mục lục

1. Giới thiệu chung
2. Kiến trúc hệ thống
3. Mô hình dữ liệu & Pipeline xử lý
4. Các loại tấn công được mô phỏng
5. Rule-based IDS
6. Machine Learning IDS
7. Hướng dẫn cài đặt & triển khai
8. Hướng dẫn chạy mô phỏng tấn công
9. Testing & Evaluation
10. Demo & Dashboard
11. Cấu trúc thư mục
12. Hạn chế & hướng phát triển

---

## 1. Giới thiệu chung

Trong bối cảnh IoT ngày càng phổ biến trong công nghiệp, giao thức MQTT được sử dụng rộng rãi do tính nhẹ và hiệu quả. Tuy nhiên, MQTT thiếu cơ chế bảo mật tích hợp mạnh, khiến hệ thống dễ bị tấn công.

Đồ án này đề xuất một **hệ thống IDS cho MQTT IoT**, kết hợp:

* **Rule-based detection**: Phát hiện tấn công rõ ràng, tức thời
* **Machine Learning (Random Forest)**: Phát hiện các tấn công chậm, tinh vi

---

## 2. Kiến trúc hệ thống

### 2.1 Tổng quan kiến trúc

Hệ thống gồm các thành phần chính:

* MQTT Broker (TLS)
* IoT Device Simulator (≈300 thiết bị)
* Attack Generator (11 loại tấn công)
* Suricata (Network IDS)
* MQTT Flow Forwarder
* InfluxDB
* Rule Engine
* ML Engine (Random Forest)
* Dashboard + Email Alert

### 2.2 Luồng dữ liệu

```
IoT Devices / Attacker
        ↓
   MQTT Broker (TLS)
        ↓
     Suricata
        ↓
  Flow Forwarder
        ↓
     InfluxDB
        ↓
 Rule Engine / ML Engine
        ↓
 Dashboard + Email Alert
```

---

## 3. Mô hình dữ liệu & Pipeline xử lý

### 3.1 MQTT Flow-based Schema

Thay vì lưu toàn bộ packet-level log, hệ thống chỉ giữ **flow metadata**, bao gồm:

* client_id
* username
* mqtt_type (connect, publish, subscribe, disconnect)
* topic
* qos, retain
* payload_len
* return_code
* timestamp

➡️ Giảm tải dữ liệu >60%, phù hợp triển khai thực tế.

---

## 4. Các loại tấn công được mô phỏng (11 attacks)

### 4.1 Rule-based Attacks (8 loại)

1. Publish Flood
2. Payload Anomaly (Oversized Payload)
3. Retain & QoS Abuse
4. Topic Enumeration
5. Wildcard Subscription Abuse
6. Reconnect Storm
7. Brute-force Login
8. Duplicate Client ID

### 4.2 ML-based Attacks (3 loại)

9. Slow Brute-force
10. Rotating Brute-force
11. SlowITE (Low-rate Intelligent Attack)

---

## 5. Rule-based IDS

### 5.1 Nguyên lý

Rule engine phân tích dữ liệu trong sliding window (time-based) và so sánh với các ngưỡng xác định trước.

### 5.2 Ví dụ Rule

* **Publish Flood**: Số lượng publish > ngưỡng trong 1 cửa sổ thời gian
* **Reconnect Storm**: connect/disconnect liên tục trong thời gian ngắn
* **Payload Anomaly**: payload_len vượt ngưỡng cho phép

### 5.3 Ưu điểm

* Phát hiện nhanh
* Dễ giải thích
* Phù hợp tấn công rõ ràng

---

## 6. Machine Learning IDS

### 6.1 Mô hình sử dụng

* **Random Forest Classifier**

### 6.2 Feature chính

* publish_rate
* avg_payload_len
* connect_fail_ratio
* session_duration
* topic_entropy

### 6.3 Vai trò

ML được dùng để phát hiện:

* Tấn công chậm
* Tấn công bắt chước hành vi thiết bị hợp lệ

---

## 7. Hướng dẫn cài đặt & triển khai

### 7.1 Yêu cầu hệ thống

* Ubuntu 20.04+
* Docker & Docker Compose
* Python 3.9+

### 7.2 Cài đặt

```bash
git clone <repo_url>
cd mqtt-ids
pip install -r requirements.txt
```

### 7.3 Chạy hệ thống

```bash
docker-compose up -d
```

---

## 8. Hướng dẫn chạy mô phỏng tấn công

### 8.1 Ví dụ: Publish Flood

```bash
python publish_flood.py --broker <IP> --port 8883
```

### 8.2 Ví dụ: Slow Brute-force

```bash
python slow_brute_force.py --target-username sensor_01
```

➡️ Mỗi script tấn công có thể chạy độc lập.

---

## 9. Testing & Evaluation

### 9.1 Testing Rule-based

* Test online
* Mỗi đợt test 1 loại tấn công
* Traffic thật + traffic tấn công

### 9.2 Chỉ số đánh giá

* Detection Rate
* False Positive Rate
* CPU / RAM usage
* Alert Latency

---

## 10. Demo & Dashboard

* Dashboard hiển thị:

  * Alert theo thời gian
  * Phân loại attack
  * Client bị nghi ngờ
* Email alert khi phát hiện tấn công nghiêm trọng

---

## 11. Cấu trúc thư mục

```
├── attack_scripts/
├── rule_engine/
├── ml_engine/
├── forwarder/
├── docker-compose.yml
├── requirements.txt
└── README.md
```

---

## 12. Hạn chế & hướng phát triển

### 12.1 Hạn chế

* Dataset chưa phản ánh 100% môi trường thực
* ML chưa được huấn luyện online

### 12.2 Hướng phát triển

* Online learning
* Federated IDS
* Triển khai edge-level IDS

---

## ✅ Kết luận

Đồ án đã xây dựng thành công một **IDS cho MQTT IoT** có khả năng phát hiện đa dạng tấn công với chi phí tài nguyên thấp, phù hợp triển khai thực tế trong nhà máy thông minh.

---

📎 *Tài liệu này dùng để nộp kèm source code đồ án.*
