import sys, time, math, random
sensor = (sys.argv[1] if len(sys.argv) > 1 else "ECG").upper()
t0 = time.time(); i = 0
def log(m): print(m, flush=True)
log(f"[DEMO] {sensor} started")
try:
    while True:
        t = time.time() - t0; i += 1
        if sensor == "ECG":
            hr = 72 + 6*math.sin(t*0.4)
            log(f"ECG: t={t:.1f}s  HR={hr:.1f} bpm  R-peak? {i%30==0}")
        elif sensor == "EMG":
            amp = abs(math.sin(t*2.3)) + random.random()*0.2
            log(f"EMG: t={t:.1f}s  rms={amp:.2f}")
        elif sensor in ("PULSE OX","PULSEOX","PULSE_OX"):
            spo2 = 98 - abs(math.sin(t*0.2))*1.5; pr = 70 + 5*math.sin(t*0.5)
            log(f"PulseOx: t={t:.1f}s  SpO2={spo2:.1f}%  PR={pr:.1f}")
        elif sensor == "REACTION":
            log("Reaction: ready" if i%20 else f"Reaction: stimulus -> response {random.randint(180,320)} ms")
        time.sleep(0.1)
except KeyboardInterrupt:
    log(f"[DEMO] {sensor} stopped")
import math
import random
import sys
import time
from itertools import count
from typing import Any, Callable, Dict


def _normalize_sensor_key(raw_name: str) -> str:
    return "".join(raw_name.split()).lower()


def _generate_ecg(step: int) -> float:
    baseline = 72
    rhythmic = 6 * math.sin(step / 4.0)
    noise = random.uniform(-2.0, 2.0)
    return baseline + rhythmic + noise


def _generate_pulse_ox(step: int) -> float:
    drift = math.sin(step / 12.0) * 0.5
    noise = random.uniform(-0.4, 0.4)
    return 97.5 + drift + noise


def _generate_emg(step: int) -> float:
    envelope = abs(math.sin(step / 3.0)) * 20
    noise = random.uniform(-2.5, 2.5)
    return envelope + noise


def _generate_reaction(step: int) -> float:
    base_time_ms = 240 + 40 * math.sin(step / 5.0)
    variance = random.uniform(-30, 30)
    return max(120.0, base_time_ms + variance)


SENSOR_PROFILES: Dict[str, Dict[str, Any]] = {
    "ECG": {"unit": "bpm", "interval": 0.5, "generator": _generate_ecg},
    "Pulse Ox": {"unit": "%", "interval": 0.8, "generator": _generate_pulse_ox},
    "EMG": {"unit": "mV", "interval": 0.4, "generator": _generate_emg},
    "Reaction": {"unit": "ms", "interval": 1.2, "generator": _generate_reaction},
}

DEFAULT_SENSOR = "ECG"

SENSOR_ALIASES = {
    "ecg": "ECG",
    "pulseox": "Pulse Ox",
    "emg": "EMG",
    "reaction": "Reaction",
}


def _resolve_sensor_name(raw: str) -> str:
    if not raw:
        return DEFAULT_SENSOR

    normalized = _normalize_sensor_key(raw)
    return SENSOR_ALIASES.get(normalized, raw)


def main() -> None:
    raw_sensor_name = " ".join(sys.argv[1:]).strip()
    sensor_name = _resolve_sensor_name(raw_sensor_name)
    profile = SENSOR_PROFILES.get(sensor_name, SENSOR_PROFILES[DEFAULT_SENSOR])

    print(f"[demo] Starting {sensor_name} sensor stream", flush=True)

    try:
        for tick in count():
            value = profile["generator"](tick)
            unit = profile["unit"]
            if unit == "ms":
                display_value = f"{value:.0f}"
            else:
                display_value = f"{value:.2f}"
            print(f"{sensor_name}: {display_value} {unit}", flush=True)
            time.sleep(profile["interval"])
    except KeyboardInterrupt:
        print("[demo] Sensor stream interrupted", flush=True)


if __name__ == "__main__":
    random.seed()
    main()
