import paho.mqtt.client as mqtt
import json
import time
import threading
import ssl
from datetime import datetime, timezone

class PayloadAnomalyAttackTLS:
    def __init__(self, broker_host="localhost", broker_port=8883, ca_cert_path="certs/ca-cert.pem"):
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.ca_cert_path = ca_cert_path
        self.attack_stats = {
            "messages_sent": 0,
            "messages_failed": 0,
            "connections_failed": 0,
            "start_time": None,
            "end_time": None
        }

    def create_client(self, client_id):
        """Create a Paho MQTT client configured to use TLS with CA certificate only."""
        try:
            client = mqtt.Client(client_id=client_id, protocol=mqtt.MQTTv311)

            # 🔒 TLS config (CA certificate only)
            client.tls_set(
                ca_certs=self.ca_cert_path,
                cert_reqs=ssl.CERT_REQUIRED,
                tls_version=ssl.PROTOCOL_TLS_CLIENT,
                ciphers=None
            )

            # 🔐 Use consistent credentials for Suricata visibility
            username = "giamdoc"
            password = "123"
            client.username_pw_set(username, password)

            return client
        except Exception as e:
            print(f"Error creating client {client_id}: {e}")
            return None

    def generate_payload(self, topic):
        """Generate a payload similar to normal IoT devices but with extra anomaly markers."""
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "value": 9999.99,
            "client_id": "attack_fast-sensor2",
            "zone": "attack",
            "attack_signature": "R5_PAYLOAD_ANOMALY",
            "anomaly_type": "oversized_payload",
            "data": "X" * 5000  # 5 KB valid JSON string
        }
        return json.dumps(payload)

    def anomaly_worker(self, worker_id, num_messages=50, delay_ms=200):
        client_id = f"attack_fast_worker{worker_id}"
        client = self.create_client(client_id)

        if not client:
            self.attack_stats["connections_failed"] += 1
            return

        try:
            client.connect(self.broker_host, self.broker_port, 60)
            client.loop_start()
            print(f"Worker {worker_id}: Connected to {self.broker_host}:{self.broker_port} using TLS")

            topic = "factory/energy/attack-fast/telemetry"

            for i in range(num_messages):
                try:
                    payload = self.generate_payload(topic)
                    info = client.publish(topic, payload, qos=0, retain=False)
                    if getattr(info, "rc", 1) == 0:
                        self.attack_stats["messages_sent"] += 1
                        print(f"Worker {worker_id}: Sent message {i+1}")
                    else:
                        self.attack_stats["messages_failed"] += 1
                        print(f"Worker {worker_id}: Failed to send message {i+1}")
                    time.sleep(delay_ms / 1000.0)
                except Exception as e:
                    self.attack_stats["messages_failed"] += 1
                    print(f"Worker {worker_id}: Error sending message {i}: {e}")

        except Exception as e:
            print(f"Worker {worker_id}: Connection failed: {e}")
            self.attack_stats["connections_failed"] += 1
        finally:
            client.loop_stop()
            client.disconnect()

    def launch_attack(self, num_workers=2, messages_per_worker=50, delay_ms=200):
        print(f"Launching Payload Anomaly Attack (TLS)")
        print(f"Broker: {self.broker_host}:{self.broker_port}")
        print(f"CA Certificate: {self.ca_cert_path}")
        print(f"Workers: {num_workers}, Messages per worker: {messages_per_worker}")

        self.attack_stats["start_time"] = time.time()
        threads = []
        for i in range(num_workers):
            t = threading.Thread(target=self.anomaly_worker, args=(i, messages_per_worker, delay_ms))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        self.attack_stats["end_time"] = time.time()
        self.print_stats()

    def print_stats(self):
        duration = self.attack_stats["end_time"] - self.attack_stats["start_time"]
        print("\nAttack Stats:")
        print(f"Messages Sent: {self.attack_stats['messages_sent']}")
        print(f"Messages Failed: {self.attack_stats['messages_failed']}")
        print(f"Connections Failed: {self.attack_stats['connections_failed']}")
        print(f"Duration: {duration:.2f}s")

if __name__ == "__main__":
    attack = PayloadAnomalyAttackTLS(
        broker_host="10.12.112.191",
        broker_port=8883,
        ca_cert_path="certs/ca-cert.pem"
    )
    attack.launch_attack(num_workers=4, messages_per_worker=20, delay_ms=300)
