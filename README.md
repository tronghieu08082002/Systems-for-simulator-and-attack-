MQTT-based Intrusion Detection System for IoT Networks
Hệ thống phát hiện xâm nhập cho mạng IoT sử dụng giao thức MQTT

📖 Giới thiệu
Đồ án này xây dựng một hệ thống phát hiện xâm nhập (IDS) lai (Hybrid IDS) dành cho môi trường nhà máy thông minh (Smart Factory) sử dụng giao thức MQTT. Hệ thống kết hợp giữa Rule-based Detection (phát hiện dựa trên luật) cho các tấn công đã biết và Machine Learning (Random Forest) để phát hiện các tấn công tinh vi, chậm hoặc chưa biết.

Các phân hệ trong Smart Factory giả lập:

Office & IT

Production Floor (Dây chuyền sản xuất, cảm biến rung, nhiệt độ...)

Energy Management (Quản lý năng lượng, HVAC...)

Security & Safety (Báo cháy, cửa từ...)

Smart Storage (Kho bãi thông minh)

🏗 Kiến trúc hệ thống

Luồng dữ liệu hoạt động như sau:

IoT Simulation: Các script replayer phát lại dữ liệu thực tế từ các file CSV (datasets) lên MQTT Broker qua kết nối TLS an toàn.

Attacker: Các script tấn công giả lập 11 loại tấn công khác nhau nhắm vào Broker.

Traffic Capture: Suricata bắt gói tin và chuyển tiếp qua Flow Forwarder.

Storage: Dữ liệu Flow metadata được lưu trữ vào InfluxDB.

Detection Engine:

Rule Engine: Kiểm tra các ngưỡng (Threshold) và mẫu (Signature).

ML Engine: Mô hình Random Forest phân tích hành vi bất thường.

Alerting: Gửi cảnh báo qua Dashboard/Email.

⚙️ Cài đặt môi trường
1. Yêu cầu hệ thống

OS: Ubuntu 20.04+ (Khuyến nghị) hoặc Windows.

Python: 3.9 trở lên.

MQTT Broker: EMQX hoặc Mosquitto (đã cấu hình TLS port 8883).

2. Cài đặt thư viện

pip install -r requirements.txt

(Yêu cầu các thư viện chính: pandas, paho-mqtt, scikit-learn, influxdb-client, v.v.)

3. Chuẩn bị Chứng chỉ (TLS)

Đảm bảo thư mục certs/ nằm trong thư mục gốc của dự án và chứa file ca-cert.pem hợp lệ để kết nối tới Broker.

🚀 Hướng dẫn chạy Giả lập (Simulation)

Hệ thống sử dụng các bộ dữ liệu CSV thực tế để giả lập hoạt động của hàng trăm thiết bị IoT trong nhà máy.

1. Chạy Zone Production

Giả lập các cảm biến rung, bảo trì dự đoán, hệ thống thủy lực...

python replayer_production.py --indir datasets --broker 10.12.112.191 --port 8883

2. Chạy Zone Energy

Giả lập hệ thống làm mát (Cooler), quạt (Fan), cảm biến chuyển động...

python replayer_energy.py --indir datasets --broker 10.12.112.191 --port 8883

⚔️ Hướng dẫn chạy Tấn công (Attacks)
Bộ công cụ bao gồm 11 loại tấn công được chia thành 2 nhóm chính. Lưu ý: Các script này đã được cấu hình mặc định sử dụng TLS với CA certificate tại certs/ca-cert.pem.

Nhóm 1: Rule-based Detectable Attacks (Tấn công nhanh/rõ ràng)

1. Topic Enumeration (Dò quét Topic) Attacker cố gắng đăng ký nhiều topic để dò tìm cấu trúc mạng.

python Topic_Enumeration.py --broker 10.12.112.191 --port 8883 --username attacker --password 123

2. Brute Force (Dò mật khẩu nhanh) Tấn công đăng nhập liên tục với tốc độ cao.

python Brute_Force.py --broker 10.12.112.191 --port 8883 --target-username "admin" --tls
3. Duplicate Client ID (Trùng lặp ID) Ngắt kết nối thiết bị hợp lệ bằng cách sử dụng Client ID của nạn nhân.

Bash

python Duplicate_id.py --broker 10.12.112.191 --port 8883 --client-id "target_device" --username attacker --password 123

4. Flooding DoS (Tấn công tràn ngập) Spam hàng nghìn tin nhắn rác làm quá tải Broker.

python Flooding_DoS.py --broker 10.12.112.191 --port 8883 --workers 10 --messages 2000 --topics "factory/sensor/temp" --username attacker --password 123

5. Malformed Data (Dữ liệu sai lệch) Gửi payload sai định dạng hoặc quá khổ (Oversized payload).

python Malformed_Data.py --broker 10.12.112.191 --port 8883 --username attacker --password 123

6. Reconnect Storm (Bão kết nối) Có 3 chế độ tấn công:

Storm: Kết nối/ngắt ngẫu nhiên gây nhiễu loạn.

python Reconnect_Storm.py --broker 10.12.112.191 --port 8883 --type storm --workers 10 --reconnects 100 --username attacker --password 123

Rapid: Kết nối/ngắt tốc độ cao để spam CPU (TLS Handshake).

python Reconnect_Storm.py --broker 10.12.112.191 --port 8883 --type rapid --workers 20 --duration 60 --username attacker --password 123

Burst: Dồn dập kết nối đồng thời (Thundering Herd).


python Reconnect_Storm.py --broker 10.12.112.191 --port 8883 --type burst --workers 5 --burst-size 50 --num-bursts 20 --username attacker --password 123

7. Retain & QoS Abuse Lạm dụng tin nhắn Retained hoặc QoS cấp cao để gây quá tải bộ nhớ/CPU.

python Retain_Qos_Abuse.py --broker 10.12.112.191 --port 8883 --type mixed --username giamdoc --password 123

8. Wildcard Subscription Abuse Đăng ký các topic wildcard (#) để nghe lén toàn bộ hệ thống.


python Wildcard_Abuse.py --broker 10.12.112.191 --port 8883 --workers 5 --username attacker --password 123

Nhóm 2: ML-based Detectable Attacks (Tấn công chậm/tinh vi)

9. Rotating Brute Force Thay đổi Client ID liên tục để tránh bị block IP/ID khi dò mật khẩu.

python Rotating_Brute_Force.py --broker 10.12.112.191 --port 8883 --target-username "admin" --tls

10. Slow Brute Force Dò mật khẩu với tốc độ rất chậm (Low-rate) để lẩn tránh các luật dựa trên ngưỡng thời gian.

python Slow_Brute_Force.py --broker 10.12.112.191 --port 8883 --target-username "admin" --tls

11. SlowITe (Slow DoS) Chiếm dụng kết nối bằng cách gửi Keep-Alive cực lớn và giữ kết nối mở (Zombie mode) để làm cạn kiệt slot kết nối của Broker.

python Slwit.py --host 10.12.112.191 --port 8883 --clients 50 --zombie --tls --username attacker --password 123

🛡️ Hướng dẫn vận hành IDS

1. Khởi động Log & Forwarder
Đảm bảo Suricata đang chạy và log đang được đẩy vào InfluxDB thông qua script forwarder.

2. Khởi động Detection Engine
Chạy engine chính để bắt đầu phân tích lưu lượng:


# Ví dụ (cần trỏ đúng file main của IDS)
python ids_main.py --mode hybrid
Hệ thống sẽ tải Rule-set và Model Random Forest đã huấn luyện để bắt đầu giám sát.

3. Giám sát
Truy cập Dashboard (Grafana/Web Interface) để xem các cảnh báo theo thời gian thực.

📂 Cấu trúc thư mục
mqtt-ids-project/
├── attack_scripts/          # Chứa 11 scripts tấn công (Slwit, Flood, etc.)
├── certs/                   # Chứa CA certificate (ca-cert.pem)
├── datasets/                # Chứa file CSV dữ liệu sensor (Gửi kèm)
├── replayer_energy.py       # Script giả lập phân khu năng lượng
├── replayer_production.py   # Script giả lập phân khu sản xuất
├── ids_engine/              # Source code Rule Engine & ML Engine
├── requirements.txt         # Các thư viện cần thiết
└── README.md                # Tài liệu hướng dẫn này
