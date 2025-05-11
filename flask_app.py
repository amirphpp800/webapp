from flask import Flask, render_template, jsonify
import threading
import time
import requests
import subprocess
import random
import platform
import queue
import os
import re

app = Flask(__name__)

# Global scanning state
scanning = False
scan_thread = None
total_scans = 0
successful_scans = 0
scan_log = []
scan_results = []
log_lock = threading.Lock()
results_lock = threading.Lock()
scan_queue = queue.Queue()
MAX_LOG_ENTRIES = 100

# Pre-compile regular expressions for performance
ttl_regex = re.compile(r'ttl=|time=', re.IGNORECASE)

def generate_random_ip(min_octet1=0, max_octet1=255, exclude_private=False):
    """Generate a random IP with filtering options"""
    while True:
        # Generate first octet within range
        first = random.randint(min_octet1, max_octet1)

        # Generate remaining octets
        ip = f"{first}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}"

        # Check if we should skip private IPs
        if exclude_private and is_private_ip(ip):
            continue

        return ip

def is_private_ip(ip):
    """Check if an IP address is in a private range"""
    octets = [int(o) for o in ip.split('.')]

    # Check private IP ranges
    if octets[0] == 10:
        return True
    if octets[0] == 172 and 16 <= octets[1] <= 31:
        return True
    if octets[0] == 192 and octets[1] == 168:
        return True
    if octets[0] == 127:  # Loopback
        return True
    if octets[0] == 169 and octets[1] == 254:  # Link-local
        return True

    return False

def ping_test(ip_address, timeout=3):
    """Test if an IP address responds to ping with optimized performance."""
    try:
        start_time = time.time()
        param = '-n' if platform.system().lower() == 'windows' else '-c'

        # Optimize command for faster execution
        if platform.system().lower() == 'windows':
            cmd = ['ping', '-w', str(int(timeout * 1000)), '-n', '1', ip_address]
        else:
            # Using -c 1 for one ping request, -I to use default interface
            cmd = ['ping', '-W', str(int(timeout)), '-c', '1', ip_address]

        output = subprocess.check_output(
            cmd, 
            universal_newlines=True, 
            stderr=subprocess.STDOUT,
            timeout=timeout + 1  # Add buffer to timeout
        )

        end_time = time.time()
        response_time = round((end_time - start_time) * 1000)

        # Look for actual ping time in the output if available
        time_match = re.search(r'time=(\d+\.?\d*)', output)
        if time_match:
            return True, f"{time_match.group(1)}ms"

        # Use regex for faster pattern matching
        if ttl_regex.search(output):
            return True, f"{response_time}ms"
        return False, "Failed"
    except subprocess.CalledProcessError:
        return False, "Failed"
    except subprocess.TimeoutExpired:
        return False, "Timeout"
    except Exception as e:
        error_msg = str(e)
        if "No such file" in error_msg:  # Fix for network error
            return False, "Network error"
        return False, f"Error: {error_msg[:20]}"

def get_country_from_ip(ip_address):
    """Get country information for an IP address using API with caching."""
    try:
        # Use session for connection pooling
        response = requests.get(
            f"https://api.iplocation.net/?ip={ip_address}", 
            timeout=3
        )

        if response.status_code == 200:
            data = response.json()
            country = data.get("country_name", "Unknown")
            # Limit length for display purposes
            if len(country) > 15:
                return country[:15]
            return country
        return "Unknown"
    except Exception:
        return "Unknown"

def scan_ips():
    global scanning, total_scans, successful_scans, scan_log

    try:
        # Reset counters
        total_scans = 0
        successful_scans = 0

        add_to_log("Scanning started...")

        while scanning:
            # Generate random IP
            ip = generate_random_ip(exclude_private=True)

            # Test IP
            success, ping_result = ping_test(ip, timeout=3)

            # Update total scans
            total_scans += 1

            if success:
                # Get country
                country = get_country_from_ip(ip)

                # Update successful scans
                successful_scans += 1

                # Add to log and results
                log_message = f"Success: {ip} - Ping: {ping_result} - Country: {country}"
                add_to_log(log_message)
                add_to_results(ip, ping_result, country)
            else:
                if random.random() < 0.2:  # Only log about 20% of failures
                    log_message = f"Failed: {ip} - {ping_result}"
                    add_to_log(log_message)

            # Small delay to prevent flooding
            time.sleep(0.1)
    except Exception as e:
        add_to_log(f"Scan error: {str(e)}")
    finally:
        add_to_log("Scanning stopped.")
        scanning = False

def add_to_log(message):
    with log_lock:
        # Add timestamp
        timestamp = time.strftime("%H:%M:%S", time.localtime())
        log_entry = f"[{timestamp}] {message}"

        # Add to log with limit
        scan_log.append(log_entry)

        # Keep log size reasonable
        if len(scan_log) > MAX_LOG_ENTRIES:
            scan_log = scan_log[-MAX_LOG_ENTRIES:]

def add_to_results(ip, ping, country):
    with results_lock:
        # Check if IP already exists in results
        for result in scan_results:
            if result["ip"] == ip:
                return

        # Add new result
        scan_results.append({
            "ip": ip,
            "ping": ping,
            "country": country
        })

def check_internet():
    try:
        # Faster connectivity check - only basic TCP connection
        import socket
        socket.create_connection(("8.8.8.8", 53), timeout=3)
        return True
    except:
        try:
            # Fallback to HTTP request
            requests.head("https://www.google.com", timeout=3)
            return True
        except:
            return False

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/check_internet')
def check_internet_route():
    return jsonify({"connected": check_internet()})

@app.route('/start_scan')
def start_scan():
    global scanning, scan_thread

    if not scanning:
        scanning = True
        scan_thread = threading.Thread(target=scan_ips)
        scan_thread.daemon = True
        scan_thread.start()
        return jsonify({"success": True})

    return jsonify({"success": False, "message": "Scanning already in progress"})

@app.route('/stop_scan')
def stop_scan():
    global scanning

    if scanning:
        scanning = False
        return jsonify({"success": True})

    return jsonify({"success": False, "message": "No scan in progress"})

@app.route('/clear_results')
def clear_results():
    global scan_results

    with results_lock:
        scan_results = []

    return jsonify({"success": True})

@app.route('/scan_status')
def scan_status():
    with log_lock, results_lock:
        progress = 0
        if total_scans > 0:
            progress = min(100, int((successful_scans / total_scans) * 100))

        return jsonify({
            "scanning": scanning,
            "total_scans": total_scans,
            "successful_scans": successful_scans,
            "progress": progress,
            "log": "\n".join(scan_log),
            "results": scan_results
        })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000, debug=True)
