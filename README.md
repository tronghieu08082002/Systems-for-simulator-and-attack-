MQTT-based Intrusion Detection System for IoT Networks

Hệ thống phát hiện xâm nhập cho mạng IoT sử dụng giao thức MQTT

📌 Thông tin chung

Tên đề tài: MQTT-based Intrusion Detection System for IoT Networks

Loại hệ thống: Hybrid IDS (Rule-based + Machine Learning)

Giao thức giám sát: MQTT over TLS

Môi trường triển khai: Smart Factory (Industrial IoT)

Mục tiêu chính:

Phát hiện các tấn công MQTT phổ biến

Phát hiện các tấn công chậm, tinh vi

Tối ưu tài nguyên (CPU, RAM, Storage)

📖 1. Giới thiệu

MQTT là giao thức truyền thông nhẹ, được sử dụng rộng rãi trong các hệ thống IoT công nghiệp. Tuy nhiên, MQTT không được thiết kế với trọng tâm là bảo mật, khiến các hệ thống Smart Factory dễ bị:

Dò quét topic

Giả mạo thiết bị

Flooding DoS

Brute-force đăng nhập

Tấn công chậm (low-rate attack) rất khó phát hiện

Đồ án này xây dựng một hệ thống IDS chuyên biệt cho MQTT, sử dụng cách tiếp cận Flow-based IDS, kết hợp:

Rule-based Detection → phát hiện nhanh, rõ ràng

Machine Learning (Random Forest) → phát hiện hành vi bất thường

🏭 2. Mô hình Smart Factory giả lập

Hệ thống mô phỏng ≈300 thiết bị IoT thuộc nhiều phân khu:

Zone	Mô tả
Office & IT	Máy tính, máy in, cảm biến văn phòng
Production	Dây chuyền sản xuất, rung, nhiệt độ
Energy	HVAC, quạt, làm mát
Security	Báo cháy, cửa từ, camera
Storage	Kho thông minh, môi trường

➡️ Mỗi zone có đặc tính traffic khác nhau, giúp IDS được đánh giá thực tế.

🏗 3. Kiến trúc hệ thống
IoT Replayer / Attacker
          ↓
   MQTT Broker (TLS : 8883)
          ↓
      Suricata IDS
          ↓
   MQTT Flow Forwarder
          ↓
      InfluxDB
          ↓
  Rule Engine  +  ML Engine
          ↓
 Dashboard (Grafana) + Email Alert

🧠 4. Triết lý thiết kế (RẤT QUAN TRỌNG)
4.1 Vì sao không phân tích payload?

Payload MQTT có thể:

Mã hóa

Rất lớn

Không đồng nhất

Phân tích payload gây:

Tốn CPU

Tăng False Positive

➡️ Hệ thống chỉ phân tích Flow Metadata, gồm:

client_id, username, mqtt_type,
topic, qos, retain,
payload_length, return_code, timestamp


➡️ Giảm >60% dung lượng, phù hợp chạy 24/7.

⚙️ 5. Cài đặt môi trường
5.1 Yêu cầu hệ thống

OS: Ubuntu 20.04+ (khuyến nghị)

Python: 3.9+

MQTT Broker: EMQX hoặc Mosquitto

TLS: Port 8883

5.2 Cài thư viện
pip install -r requirements.txt

5.3 Chuẩn bị TLS
certs/
└── ca-cert.pem


👉 Tất cả script đều mặc định dùng TLS.

🚀 6. Chạy giả lập IoT (REPLAYER)
6.1 Production Zone
python replayer_production.py \
  --indir datasets \
  --broker 10.12.112.191 \
  --port 8883

6.2 Energy Zone
python replayer_energy.py \
  --indir datasets \
  --broker 10.12.112.191 \
  --port 8883

6.3 Office Zone
python replayer_office.py \
  --indir datasets \
  --broker 10.12.112.191 \
  --port 8883


➡️ Có thể chạy song song nhiều zone.

⚔️ 7. Chạy tấn công (11 ATTACKS)

⚠️ Chỉ chạy trong môi trường lab

🔴 Nhóm 1 – Rule-based Detectable Attacks (8 loại)
1️⃣ Topic Enumeration
python topic_enumeration.py \
  --broker 10.12.112.191 \
  --port 8883 \
  --username attacker \
  --password 123

2️⃣ Brute Force (Fast)
python Brute_Force.py \
  --broker 10.12.112.191 \
  --port 8883 \
  --target-username admin \
  --tls

3️⃣ Duplicate Client ID
python duplicate_id.py \
  --broker 10.12.112.191 \
  --port 8883 \
  --client-id target_device \
  --username attacker \
  --password 123

4️⃣ Publish Flood (DoS)
python publish_flood.py \
  --broker 10.12.112.191 \
  --port 8883 \
  --workers 10 \
  --messages 2000

5️⃣ Payload Anomaly (Oversized)
python payload_anomaly.py \
  --broker 10.12.112.191 \
  --port 8883

6️⃣ Reconnect Storm

Storm

python reconnect_storm.py --type storm --workers 10 --reconnects 100


Rapid

python reconnect_storm.py --type rapid --workers 20 --duration 60


Burst

python reconnect_storm.py --type burst --burst-size 50 --num-bursts 20

7️⃣ Retain & QoS Abuse
python retain_qos_abuse.py \
  --broker 10.12.112.191 \
  --port 8883

8️⃣ Wildcard Abuse
python wildcard_abuse.py \
  --broker 10.12.112.191 \
  --port 8883 \
  --workers 5

🟠 Nhóm 2 – ML-based Attacks (3 loại)
9️⃣ Rotating Brute Force
python slow_brute_force.py \
  --broker 10.12.112.191 \
  --port 8883 \
  --target-username admin \
  --tls

🔟 Slow Brute Force
python slow_brute_force.py \
  --broker 10.12.112.191 \
  --port 8883 \
  --target-username admin \
  --packets-per-minute 4 \
  --tls

1️⃣1️⃣ SlowITe (Slow DoS)
python slowite.py \
  --host 10.12.112.191 \
  --port 8883 \
  --clients 50 \
  --zombie \
  --tls

🛡️ 8. Chạy IDS
8.1 Khởi động logging

Suricata đang chạy

Forwarder đang ghi vào InfluxDB

8.2 Chạy IDS Engine
python ids_main.py --mode hybrid

📊 9. Dashboard & Alert

Dashboard (Grafana):

Attack type

Client ID

Timestamp

Email alert cho:

Flood

Brute force

Reconnect storm

📂 10. Cấu trúc thư mục
mqtt-ids-project/
├── attack_scripts/
├── certs/
├── datasets/
├── replayer_*.py
├── ids_engine/
├── requirements.txt
└── README.md

📉 11. Hạn chế

Dataset mô phỏng

ML offline

Chưa có IPS tự động block

🚀 12. Hướng phát triển

Online learning

Edge IDS

Federated IDS

IDS + IPS

✅ 13. Kết luận

Hệ thống chứng minh rằng Hybrid IDS cho MQTT IoT có thể:

Phát hiện đa dạng tấn công

Giảm tài nguyên đáng kể

Phù hợp triển khai Smart Factory thực tế

⚠️ Lưu ý pháp lý

Các script tấn công chỉ phục vụ nghiên cứu và giáo dục.
Không sử dụng vào mục đích trái phép.
