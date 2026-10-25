"""
MicroCorp AI - Public Cloudflare Tunnel & Mobile Gateway Manager
Exposes local MicroCorp storefront and checkout portal to the global internet
via Cloudflare Quick Tunnel, generates mobile QR codes, and ensures 24/7 public access.
"""

import os
import re
import sys
import time
import json
import logging
import threading
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import (
    SERVER_PORT, CLOUDFLARED_BIN, PUBLIC_GATEWAY_FILE, 
    PUBLIC_QR_FILE, DATA_DIR, PAYOUT_UPI_ID, PAYEE_NAME
)

logger = logging.getLogger("MicroCorp.TunnelGateway")

class PublicTunnelGateway:
    def __init__(self):
        self.port = SERVER_PORT
        self.cloudflared_path = Path(CLOUDFLARED_BIN)
        self.process: Optional[subprocess.Popen] = None
        self.public_url: Optional[str] = None
        self.is_running = False
        self._thread: Optional[threading.Thread] = None
        self.last_sync_time = 0
        self._load_cached_state()

    def _load_cached_state(self):
        """Loads cached public URL if available."""
        if PUBLIC_GATEWAY_FILE.exists():
            try:
                with open(PUBLIC_GATEWAY_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.public_url = data.get("public_url")
            except Exception as e:
                logger.debug(f"Could not load cached tunnel state: {e}")

    def start_tunnel(self):
        """Starts the public Cloudflare tunnel in a background supervisor thread."""
        if self.is_running and self.process and self.process.poll() is None:
            return

        self.is_running = True
        self._thread = threading.Thread(target=self._run_supervisor, daemon=True, name="Cloudflare-Tunnel-Supervisor")
        self._thread.start()
        logger.info("🌐 Initiated Public Cloudflare Tunnel supervisor...")

    def stop_tunnel(self):
        """Stops the public tunnel."""
        self.is_running = False
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=3)
            except Exception:
                try:
                    self.process.kill()
                except Exception:
                    pass
            self.process = None
        logger.info("🛑 Public Cloudflare Tunnel stopped.")

    def _run_supervisor(self):
        """Continuously supervises the tunnel and auto-reconnects if disconnected."""
        while self.is_running:
            if not self.cloudflared_path.exists() or not os.access(str(self.cloudflared_path), os.X_OK):
                logger.warning(f"cloudflared binary not found at {self.cloudflared_path}. Public tunnel disabled.")
                time.sleep(30)
                continue

            # Clean any orphan cloudflared process listening on our port
            subprocess.run(["pkill", "-f", f"cloudflared.*{self.port}"], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(1)

            cmd = [
                str(self.cloudflared_path),
                "tunnel",
                "--protocol", "http2",
                "--edge-ip-version", "4",
                "--url", f"http://127.0.0.1:{self.port}"
            ]

            logger.info(f"🚀 Spawning Cloudflare Quick Tunnel on port {self.port}...")
            try:
                self.process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1
                )

                tunnel_url_pattern = re.compile(r"https://[a-zA-Z0-9\-]+\.trycloudflare\.com")
                
                # Stream logs to capture the public URL
                for line in iter(self.process.stdout.readline, ''):
                    if not self.is_running:
                        break
                    
                    match = tunnel_url_pattern.search(line)
                    if match:
                        url = match.group(0).strip()
                        if url != self.public_url:
                            self.public_url = url
                            self._on_tunnel_connected(url)

                if self.process:
                    self.process.wait()

            except Exception as e:
                logger.error(f"Error in Cloudflare tunnel process: {e}")

            if self.is_running:
                logger.warning("Cloudflare tunnel disconnected. Auto-reconnecting in 5 seconds...")
                time.sleep(5)

    def _on_tunnel_connected(self, url: str):
        """Fires when a new live public URL is assigned by Cloudflare."""
        self.public_url = url
        store_url = f"{url}/store"
        logger.info(f"✨ PUBLIC CLOUDFLARE STORE ONLINE: {store_url}")
        
        # 1. Save state file
        data = {
            "public_url": url,
            "store_url": store_url,
            "payout_upi_id": PAYOUT_UPI_ID,
            "payee_name": PAYEE_NAME,
            "port": self.port,
            "status": "ONLINE",
            "connected_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        with open(PUBLIC_GATEWAY_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        # 2. Generate SVG QR Code for instant phone access
        try:
            import qrcode
            import qrcode.image.svg
            factory = qrcode.image.svg.SvgPathImage
            img = qrcode.make(store_url, image_factory=factory, box_size=12)
            with open(PUBLIC_QR_FILE, "wb") as f:
                img.save(f)
            logger.info(f"📱 Generated Mobile QR Code for Public Store at {PUBLIC_QR_FILE}")
        except Exception as e:
            logger.warning(f"Could not generate public QR code: {e}")

        # 3. Log public link silently without intrusive desktop notifications
        logger.info(f"🌐 MicroCorp AI Public Store Live: {store_url} (Payouts: {PAYOUT_UPI_ID})")

    def get_public_url(self) -> Optional[str]:
        """Returns the active public URL if online."""
        if not self.public_url:
            self._load_cached_state()
        return self.public_url

    def get_gateway_status(self) -> Dict[str, Any]:
        """Returns full gateway telemetry."""
        is_active = bool(self.process and self.process.poll() is None and self.public_url)
        return {
            "is_active": is_active,
            "public_url": self.public_url,
            "store_url": f"{self.public_url}/store" if self.public_url else None,
            "payout_upi_id": PAYOUT_UPI_ID,
            "payee_name": PAYEE_NAME,
            "port": self.port,
            "qr_svg_available": PUBLIC_QR_FILE.exists()
        }

# Global singleton
public_gateway = PublicTunnelGateway()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    public_gateway.start_tunnel()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        public_gateway.stop_tunnel()
