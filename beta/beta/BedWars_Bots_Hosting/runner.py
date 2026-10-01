#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Master Hosting Runner for Render / Railway / VPS / Docker.
Launches both FunPay & Playerok BedWars bots in parallel processes
and runs a lightweight HTTP healthcheck server for Render Web Services.
"""

import os
import sys
import time
import subprocess
import threading
import http.server
import socketserver


def run_healthcheck_server():
    """Lightweight HTTP Server so Render Web Services detect an open port."""
    port = int(os.getenv("PORT", 10000))
    
    class HealthHandler(http.server.SimpleHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header('Content-type', 'text/plain; charset=utf-8')
            self.end_headers()
            self.wfile.write(b"OK - FunPay & Playerok BedWars Bots are running live!")
            
        def log_message(self, format, *args):
            pass  # Suppress HTTP access logs

    try:
        with socketserver.TCPServer(("", port), HealthHandler) as httpd:
            print(f"[🌐 WebServer] HTTP Healthcheck listening on port {port} ✅")
            httpd.serve_forever()
    except Exception as e:
        print(f"[⚠️ WebServer Error] {e}")


print("=" * 65)
print(" 🚀 Starting FunPay & Playerok BedWars Bots on Hosting...")
print("=" * 65)

# Start Web Server thread for Render HTTP Port scanner
web_thread = threading.Thread(target=run_healthcheck_server, daemon=True)
web_thread.start()

# Launch FunPay Bot
funpay_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "FunPay_BedWars_Bot")
p1 = subprocess.Popen(
    [sys.executable, "-u", "main.py"],
    cwd=funpay_dir,
    env=dict(os.environ, PYTHONUNBUFFERED="1")
)
print("[✅ Process] FunPay BedWars Bot started (PID: %d)" % p1.pid, flush=True)

# Launch Playerok Bot
playerok_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Playerok_BedWars_Bot")
p2 = subprocess.Popen(
    [sys.executable, "-u", "main.py"],
    cwd=playerok_dir,
    env=dict(os.environ, PYTHONUNBUFFERED="1")
)
print("[✅ Process] Playerok BedWars Bot started (PID: %d)" % p2.pid, flush=True)

try:
    p1.wait()
    p2.wait()
except KeyboardInterrupt:
    print("\n[ℹ️ Info] Stopping bots...", flush=True)
    p1.terminate()
    p2.terminate()
