MQTT-based Intrusion Detection System for IoT Networks

Hệ thống phát hiện xâm nhập cho mạng IoT sử dụng giao thức MQTT

📖 1. Giới thiệu tổng quan

Trong bối cảnh Cách mạng Công nghiệp 4.0, các hệ thống IoT công nghiệp (Industrial IoT – IIoT) ngày càng được triển khai rộng rãi trong nhà máy thông minh (Smart Factory). Một trong những giao thức truyền thông phổ biến nhất trong môi trường này là MQTT (Message Queuing Telemetry Transport) nhờ đặc tính nhẹ, tiết kiệm băng thông và phù hợp với thiết bị tài nguyên hạn chế.

Tuy nhiên, MQTT được thiết kế với trọng tâm là hiệu năng, không phải bảo mật, dẫn đến nhiều lỗ hổng nghiêm trọng như:

Thiếu cơ chế kiểm soát truy cập chi tiết

Dễ bị tấn công từ chối dịch vụ (DoS)

Dễ bị dò quét topic, nghe lén hoặc giả mạo thiết bị

Khó phát hiện các tấn công chậm, tinh vi (low-rate attacks)

Xuất phát từ các vấn đề trên, đồ án này xây dựng một Hệ thống phát hiện xâm nhập (Intrusion Detection System – IDS) dành riêng cho mạng IoT sử dụng MQTT, với cách tiếp cận Hybrid IDS, kết hợp:

Rule-based Detection: Phát hiện nhanh, chính xác các tấn công đã biết

Machine Learning (Random Forest): Phát hiện các hành vi bất thường, tấn công chậm hoặc chưa có chữ ký rõ ràng

Hệ thống được thiết kế và đánh giá trong bối cảnh nhà máy thông minh giả lập, với hàng trăm thiết bị IoT hoạt động đồng thời.

🏭 2. Môi trường Smart Factory giả lập

Để đảm bảo tính thực tế, đồ án xây dựng một mô hình nhà máy thông minh gồm nhiều phân khu chức năng, mỗi phân khu đại diện cho một loại nghiệp vụ IoT khác nhau:

2.1 Các phân khu (Zones)

Office & IT

Máy tính văn phòng, máy in, cảm biến môi trường

Traffic có tính định kỳ, payload nhỏ

Production Floor

Dây chuyền sản xuất

Cảm biến rung, nhiệt độ, bảo trì dự đoán (Predictive Maintenance)

Traffic cường độ cao, liên tục

Energy Management

Hệ thống HVAC, quạt, làm mát, cảm biến năng lượng

Traffic ổn định, theo chu kỳ

Security & Safety

Báo cháy, cửa từ, camera

Traffic sự kiện (event-based), yêu cầu độ tin cậy cao

Smart Storage

Kho bãi thông minh

Cảm biến nhiệt độ, độ ẩm, mức nước, camera

👉 Việc phân chia theo Zone giúp:

Mô phỏng traffic IoT thực tế

Tạo điều kiện cho attacker dò quét, lạm dụng wildcard

Đánh giá IDS trong nhiều ngữ cảnh khác nhau

🏗 3. Kiến trúc hệ thống IDS
3.1 Tổng quan kiến trúc

Hệ thống được thiết kế theo kiến trúc Flow-based IDS, không xử lý payload thô ở mức gói tin nhằm giảm tải tài nguyên.

Luồng dữ liệu tổng thể:

IoT Simulation / Attacker
          ↓
   MQTT Broker (TLS)
          ↓
      Suricata
          ↓
   MQTT Flow Forwarder
          ↓
      InfluxDB
          ↓
 Rule Engine  |  ML Engine
          ↓
 Dashboard / Email Alert

3.2 Mô tả chi tiết từng thành phần
🔹 IoT Simulation (Replayer)

Các script replayer_*.py phát lại dữ liệu từ file CSV

Mô phỏng hàng trăm thiết bị IoT hoạt động đồng thời

Kết nối MQTT qua TLS (port 8883)

🔹 Attacker

Tập hợp 11 script tấn công MQTT

Bao phủ cả tấn công nhanh và tấn công chậm

Được thiết kế để giống hành vi thiết bị thật, không quá “ồn ào”

🔹 MQTT Broker

EMQX hoặc Mosquitto

Cấu hình TLS, xác thực username/password

Là mục tiêu chính của các cuộc tấn công

🔹 Suricata

Network IDS

Bắt lưu lượng MQTT TLS

Xuất log ở dạng EVE JSON

🔹 Flow Forwarder

Chuyển đổi packet-level log → Flow metadata

Loại bỏ payload thô

Giảm kích thước dữ liệu đáng kể

🔹 InfluxDB

Lưu trữ time-series data

Phù hợp với sliding window detection

🔹 Detection Engine

Rule Engine: Phát hiện dựa trên ngưỡng và mẫu

ML Engine: Random Forest phân loại hành vi

🔹 Alerting

Dashboard (Grafana / Web UI)

Email cảnh báo khi phát hiện tấn công nghiêm trọng

📊 4. Pipeline xử lý dữ liệu (Data Pipeline)
4.1 Flow-based Detection

Thay vì xử lý toàn bộ payload MQTT, hệ thống chỉ giữ các trường metadata quan trọng:

client_id

username

mqtt_type (connect, publish, subscribe, disconnect)

topic

qos, retain

payload_length

return_code

timestamp

➡️ Cách tiếp cận này:

Giảm >60% dung lượng lưu trữ

Giảm tải CPU/RAM

Phù hợp triển khai lâu dài 24/7

⚙️ 5. Cài đặt môi trường
5.1 Yêu cầu hệ thống

OS: Ubuntu 20.04+ (khuyến nghị) hoặc Windows

Python: 3.9+

MQTT Broker: EMQX hoặc Mosquitto

TLS: Bật port 8883

5.2 Cài đặt thư viện
pip install -r requirements.txt


Các thư viện chính:

paho-mqtt

pandas

scikit-learn

influxdb-client

numpy

matplotlib

5.3 Chuẩn bị chứng chỉ TLS

Đảm bảo thư mục certs/ tồn tại

Có file:

certs/ca-cert.pem


File này dùng để xác thực Broker trong tất cả script

🚀 6. Hướng dẫn chạy giả lập IoT
6.1 Zone Production
python replayer_production.py \
  --indir datasets \
  --broker 10.12.112.191 \
  --port 8883

6.2 Zone Energy
python replayer_energy.py \
  --indir datasets \
  --broker 10.12.112.191 \
  --port 8883


➡️ Có thể chạy song song nhiều zone để tạo traffic thực tế.

⚔️ 7. Hướng dẫn chạy Tấn công (11 Attacks)
7.1 Nhóm Rule-based Attacks (8 loại)
#	Tấn công	Mục tiêu
1	Topic Enumeration	Dò cấu trúc topic
2	Brute Force	Dò mật khẩu nhanh
3	Duplicate Client ID	Ngắt thiết bị hợp lệ
4	Flooding DoS	Làm quá tải Broker
5	Malformed Data	Payload lỗi/quá khổ
6	Reconnect Storm	Làm cạn tài nguyên TLS
7	Retain & QoS Abuse	Lạm dụng QoS/Retain
8	Wildcard Abuse	Nghe lén toàn hệ thống

(Các lệnh chạy giữ nguyên như bạn đã mô tả)

7.2 Nhóm ML-based Attacks (3 loại)
#	Tấn công	Đặc điểm
9	Rotating Brute Force	Đổi Client ID liên tục
10	Slow Brute Force	Tốc độ rất chậm
11	SlowITe	Chiếm dụng kết nối

➡️ Các tấn công này khó phát hiện bằng rule thuần, cần ML.

🛡️ 8. Vận hành IDS
8.1 Khởi động logging

Đảm bảo Suricata chạy

Forwarder đang đẩy dữ liệu vào InfluxDB

8.2 Khởi động Detection Engine
python ids_main.py --mode hybrid


Hệ thống sẽ:

Load rule-set

Load mô hình Random Forest đã huấn luyện

Bắt đầu giám sát real-time

8.3 Giám sát

Dashboard hiển thị:

Loại tấn công

Client bị nghi ngờ

Thời gian phát hiện

Email alert cho các sự kiện nghiêm trọng

📂 9. Cấu trúc thư mục
mqtt-ids-project/
├── attack_scripts/
├── certs/
├── datasets/
├── replayer_energy.py
├── replayer_production.py
├── ids_engine/
├── requirements.txt
└── README.md

📉 10. Hạn chế của hệ thống

Dataset vẫn mang tính mô phỏng

ML chưa hỗ trợ online learning

Chưa tích hợp phản ứng tự động (Auto-block)

🚀 11. Hướng phát triển

Online / Incremental Learning

Federated IDS cho nhiều nhà máy

Triển khai IDS tại Edge Gateway

Kết hợp IDS + IPS

✅ 12. Kết luận

Đồ án đã xây dựng thành công một hệ thống IDS cho MQTT IoT có khả năng:

Phát hiện đa dạng tấn công

Hoạt động ổn định với chi phí tài nguyên thấp

Phù hợp triển khai trong Smart Factory thực tế
