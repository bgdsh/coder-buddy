import math
import os
import wave
from array import array


OUT_DIR = "audio"
RATE = 22050


def write_tone(path, notes):
    frames = array("h")
    for freq, duration, gain in notes:
        count = int(RATE * duration)
        for i in range(count):
            env = min(1.0, i / 300) * min(1.0, (count - i) / 600)
            value = int(math.sin(2 * math.pi * freq * i / RATE) * gain * env * 32767)
            frames.append(value)
    with wave.open(path, "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(RATE)
        f.writeframes(frames.tobytes())


os.makedirs(OUT_DIR, exist_ok=True)
write_tone(os.path.join(OUT_DIR, "approve_soft.wav"), [(523.25, 0.18, 0.4), (659.25, 0.22, 0.4)])
write_tone(os.path.join(OUT_DIR, "approve_ping.wav"), [(880.00, 0.12, 0.5), (1174.66, 0.18, 0.45)])
write_tone(os.path.join(OUT_DIR, "approve_alert.wav"), [(392.00, 0.16, 0.5), (392.00, 0.16, 0.5), (783.99, 0.22, 0.45)])
