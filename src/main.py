import gc
import json
import math
import network
import os
import struct
import time
import uasyncio as asyncio
from machine import I2S, PWM, Pin

import config
import secrets


STATE_PATH = "/state.json"
UI_PATH = "/index.html"


class DeviceState:
    def __init__(self):
        self.level = 0
        self.track = config.DEFAULT_TRACK
        self.ip = "0.0.0.0"
        self.running = False
        self.stop_audio = False
        self.audio_generation = 0
        self.load()

    def load(self):
        try:
            with open(STATE_PATH) as f:
                data = json.load(f)
            self.track = data.get("track", self.track)
        except Exception:
            self.save()

    def save(self):
        with open(STATE_PATH, "w") as f:
            json.dump({"track": self.track}, f)

    def reset(self):
        self.level = 0
        self.running = False
        self.stop_audio = True
        self.audio_generation += 1


state = DeviceState()


def clamp(value, lo, hi):
    return max(lo, min(hi, value))


class Servo:
    def __init__(self):
        self.pwm = PWM(Pin(config.SERVO_PIN), freq=config.SERVO_HZ)
        self.angle = config.SERVO_NEUTRAL_ANGLE
        self.write_angle(self.angle)

    def write_angle(self, angle):
        angle = clamp(angle, 0, 180)
        span = config.SERVO_MAX_US - config.SERVO_MIN_US
        pulse_us = config.SERVO_MIN_US + (span * angle // 180)
        duty = int(pulse_us * 65535 // 20000)
        self.pwm.duty_u16(duty)
        self.angle = angle

    def off(self):
        self.write_angle(config.SERVO_NEUTRAL_ANGLE)


class RgbLed:
    def __init__(self):
        self.r = PWM(Pin(config.RGB_R_PIN), freq=config.RGB_PWM_HZ)
        self.g = PWM(Pin(config.RGB_G_PIN), freq=config.RGB_PWM_HZ)
        self.b = PWM(Pin(config.RGB_B_PIN), freq=config.RGB_PWM_HZ)
        self.off()

    def _write(self, pwm, value):
        duty = clamp(value, 0, 65535)
        if not config.RGB_COMMON_CATHODE:
            duty = 65535 - duty
        pwm.duty_u16(duty)

    def set(self, r, g, b):
        self._write(self.r, r)
        self._write(self.g, g)
        self._write(self.b, b)

    def off(self):
        self.set(0, 0, 0)


class Button:
    def __init__(self):
        pull = Pin.PULL_UP if config.BUTTON_PULL_UP else Pin.PULL_DOWN
        self.pin = Pin(config.BUTTON_PIN, Pin.IN, pull)
        self.last_press = 0

    def pressed(self):
        value = self.pin.value()
        return value == 0 if config.BUTTON_ACTIVE_LOW else value == 1

    def poll_press(self):
        now = time.ticks_ms()
        if self.pressed() and time.ticks_diff(now, self.last_press) > 300:
            self.last_press = now
            return True
        return False


class AudioPlayer:
    def __init__(self):
        self.i2s = None
        self.enabled = False
        self.amp = None
        if config.AMP_ENABLE_PIN is not None:
            self.amp = Pin(config.AMP_ENABLE_PIN, Pin.OUT)
            self.set_amp(False)

    def set_amp(self, on):
        if self.amp is None:
            return
        value = 1 if (on == config.AMP_ENABLE_ACTIVE_HIGH) else 0
        self.amp.value(value)

    def close(self):
        if self.i2s:
            try:
                self.i2s.deinit()
            except Exception:
                pass
        self.i2s = None
        self.set_amp(False)

    def _read_wav_header(self, f):
        if f.read(4) != b"RIFF":
            raise ValueError("not a RIFF file")
        f.seek(22)
        channels = struct.unpack("<H", f.read(2))[0]
        rate = struct.unpack("<I", f.read(4))[0]
        f.seek(34)
        bits = struct.unpack("<H", f.read(2))[0]
        data_size = 0
        while True:
            chunk = f.read(4)
            if not chunk:
                break
            size = struct.unpack("<I", f.read(4))[0]
            if chunk == b"data":
                data_size = size
                break
            f.seek(f.tell() + size)
        if bits != 16 or channels not in (1, 2) or data_size <= 0:
            raise ValueError("WAV must be 16-bit PCM mono/stereo")
        return channels, rate, bits, data_size

    def _scale_samples(self, buf, volume):
        if volume >= 1.0:
            return buf
        out = bytearray(len(buf))
        for i in range(0, len(buf) - 1, 2):
            sample = struct.unpack_from("<h", buf, i)[0]
            struct.pack_into("<h", out, i, int(sample * volume))
        return out

    async def play(self, filename, generation):
        path = config.AUDIO_DIR + "/" + filename
        state.stop_audio = False
        try:
            with open(path, "rb") as f:
                channels, rate, bits, _ = self._read_wav_header(f)
                self.close()
                self.i2s = I2S(
                    config.I2S_ID,
                    sck=Pin(config.I2S_SCK_PIN),
                    ws=Pin(config.I2S_WS_PIN),
                    sd=Pin(config.I2S_SD_PIN),
                    mode=I2S.TX,
                    bits=bits,
                    format=I2S.STEREO if channels == 2 else I2S.MONO,
                    rate=rate,
                    ibuf=8192,
                )
                self.set_amp(True)
                volume = clamp(state.level, 1, config.MAX_LEVEL) / config.MAX_LEVEL
                while state.running and generation == state.audio_generation and not state.stop_audio:
                    data = f.read(2048)
                    if not data:
                        f.seek(0)
                        self._read_wav_header(f)
                        continue
                    self.i2s.write(self._scale_samples(data, volume))
                    await asyncio.sleep_ms(0)
        except Exception as exc:
            print("audio error:", exc)
        finally:
            self.close()


servo = Servo()
led = RgbLed()
button = Button()
audio = AudioPlayer()


def list_tracks():
    try:
        return sorted(name for name in os.listdir(config.AUDIO_DIR) if name.lower().endswith(".wav"))
    except OSError:
        return []


def json_response(writer, data, status="200 OK"):
    body = json.dumps(data)
    return http_response(writer, body, status, "application/json")


async def http_response(writer, body, status="200 OK", content_type="text/plain"):
    if isinstance(body, str):
        body = body.encode()
    writer.write(("HTTP/1.1 %s\r\n" % status).encode())
    writer.write(("Content-Type: %s\r\n" % content_type).encode())
    writer.write(("Content-Length: %d\r\n" % len(body)).encode())
    writer.write(b"Connection: close\r\n\r\n")
    writer.write(body)
    await writer.drain()


def percent_decode(value):
    value = value.replace("+", " ")
    out = ""
    i = 0
    while i < len(value):
        if value[i] == "%" and i + 2 < len(value):
            try:
                out += chr(int(value[i + 1:i + 3], 16))
                i += 3
                continue
            except ValueError:
                pass
        out += value[i]
        i += 1
    return out


def parse_form(body):
    result = {}
    for part in body.split("&"):
        if "=" in part:
            key, value = part.split("=", 1)
            result[percent_decode(key)] = percent_decode(value)
    return result


def status_payload():
    return {
        "device": config.DEVICE_NAME,
        "ip": state.ip,
        "level": state.level,
        "running": state.running,
        "track": state.track,
        "tracks": list_tracks(),
        "max_level": config.MAX_LEVEL,
    }


def render_ui():
    with open(UI_PATH) as f:
        return f.read()


async def read_request(reader):
    line = await reader.readline()
    if not line:
        return None, None, {}, ""
    method, path, _ = line.decode().strip().split(" ", 2)
    headers = {}
    while True:
        line = await reader.readline()
        if line in (b"\r\n", b"\n", b""):
            break
        key, value = line.decode().split(":", 1)
        headers[key.lower()] = value.strip()
    length = int(headers.get("content-length", "0"))
    body = (await reader.read(length)).decode() if length else ""
    return method, path, headers, body


def start_effects():
    state.running = state.level > 0
    state.stop_audio = True
    state.audio_generation += 1
    asyncio.create_task(audio.play(state.track, state.audio_generation))


async def handle_client(reader, writer):
    try:
        method, path, _, body = await read_request(reader)
        if method is None:
            return
        clean_path = path.split("?", 1)[0]
        if method == "GET" and clean_path in ("/", "/index.html"):
            await http_response(writer, render_ui(), content_type="text/html")
        elif method == "GET" and clean_path == "/status":
            await json_response(writer, status_payload())
        elif method == "GET" and clean_path == "/tracks":
            await json_response(writer, {"tracks": list_tracks(), "selected": state.track})
        elif method == "POST" and clean_path == "/trigger":
            state.level = clamp(state.level + 1, 0, config.MAX_LEVEL)
            start_effects()
            await json_response(writer, status_payload())
        elif method == "POST" and clean_path == "/stop":
            state.level = clamp(state.level - 1, 0, config.MAX_LEVEL)
            if state.level == 0:
                state.reset()
            else:
                start_effects()
            await json_response(writer, status_payload())
        elif method == "POST" and clean_path == "/reset":
            state.reset()
            await json_response(writer, status_payload())
        elif method == "POST" and clean_path == "/config/track":
            data = parse_form(body)
            track = data.get("track", "")
            if track in list_tracks():
                state.track = track
                state.save()
            await json_response(writer, status_payload())
        else:
            await json_response(writer, {"error": "not found"}, "404 Not Found")
    except Exception as exc:
        print("http error:", exc)
    finally:
        writer.close()
        try:
            await writer.wait_closed()
        except AttributeError:
            pass


async def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        wlan.connect(secrets.WIFI_SSID, secrets.WIFI_PASSWORD)
        for _ in range(40):
            if wlan.isconnected():
                break
            await asyncio.sleep_ms(500)
    if not wlan.isconnected():
        raise RuntimeError("wifi connection failed")
    state.ip = wlan.ifconfig()[0]
    print("wifi connected:", wlan.ifconfig())


async def servo_task():
    direction = 1
    while True:
        if state.running and state.level > 0:
            servo.write_angle(config.SERVO_MAX_ANGLE if direction > 0 else config.SERVO_MIN_ANGLE)
            direction *= -1
            await asyncio.sleep_ms(max(80, 700 - state.level * 45))
        else:
            servo.write_angle(config.SERVO_NEUTRAL_ANGLE)
            await asyncio.sleep_ms(200)


async def led_task():
    phase = 0
    while True:
        if state.running and state.level > 0:
            base = int(65535 * state.level / config.MAX_LEVEL)
            pulse = int((math.sin(phase / 5) + 1) * 0.5 * base)
            led.set(pulse, base // 6, base - pulse // 2)
            phase += 1
            await asyncio.sleep_ms(max(40, 180 - state.level * 12))
        else:
            led.off()
            await asyncio.sleep_ms(120)


async def button_task():
    while True:
        if button.poll_press():
            state.reset()
            audio.close()
            led.off()
            servo.off()
            print("button reset")
        await asyncio.sleep_ms(40)


async def main():
    await connect_wifi()
    try:
        os.mkdir(config.AUDIO_DIR)
    except OSError:
        pass
    asyncio.create_task(servo_task())
    asyncio.create_task(led_task())
    asyncio.create_task(button_task())
    server = await asyncio.start_server(handle_client, "0.0.0.0", config.HTTP_PORT)
    print("http://%s:%d" % (state.ip, config.HTTP_PORT))
    while True:
        gc.collect()
        await asyncio.sleep(30)


try:
    asyncio.run(main())
finally:
    asyncio.new_event_loop()
