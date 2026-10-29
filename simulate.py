"""Simulator untuk DEBUGGING saja (bukan edge fisik).

Mengirim telemetry palsu supaya kamu bisa mengecek detector + dashboard tanpa HP.
Pemakaian:  python scripts/simulate.py [tegak|bungkuk|pergi]
"""
import json
import os
import sys
import time
from pathlib import Path

import paho.mqtt.client as mqtt

root = Path(__file__).resolve().parent.parent
env = root / ".env"
if env.exists():
    for line in env.read_text(encoding="utf-8").splitlines():
        if line.strip() and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

pid = os.getenv("PROJECT_ID", "sitsmart_demo")
host = os.getenv("MQTT_HOST", "broker.hivemq.com")
port = int(os.getenv("MQTT_PORT", "1883"))
scenario = sys.argv[1] if len(sys.argv) > 1 else "tegak"

SCENARIOS = {
    "tegak":   (dict(rms=0.05, gravity=[0.0, 9.8, 0.0]), dict(rms=0.03, gravity=[0.0, 0.0, 9.8])),
    "bungkuk": (dict(rms=0.05, gravity=[0.0, 8.0, 5.6]), dict(rms=0.03, gravity=[0.0, 0.0, 9.8])),
    "pergi":   (dict(rms=2.0,  gravity=[2.0, 8.5, 3.0]), dict(rms=0.02, gravity=[0.0, 0.0, 9.8])),
}
body, seat = SCENARIOS[scenario]

c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="sitsmart-simulator")
c.connect(host, port, 30)
c.loop_start()
print(f"[simulator] skenario '{scenario}' ke sitsmart/{pid}  (Ctrl+C untuk berhenti)")
try:
    while True:
        for edge, d in ((1, body), (2, seat)):
            c.publish(f"sitsmart/{pid}/edge/{edge}/telemetry",
                      json.dumps({"edge": edge, "ts": int(time.time() * 1000), "rot": 0.01, **d}))
        time.sleep(1)
except KeyboardInterrupt:
    pass
