"""
Roon bridge tests: mock Roon Core + mock receiver.

1. In-process: RoonManager + OnkyoDevice (MODE=roon logic)
2. Container MODE=full as subprocess: UC driver + Roon, remote standby must
   not disconnect the receiver

Run:  python tests/test_roon.py
"""

import asyncio
import json
import os
import shutil
import subprocess
import sys
import tempfile

import websockets

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "intg-onkyoavr"))

import roon  # noqa: E402
from mock_receiver import MockReceiver  # noqa: E402
from mock_roon_core import MockRoonCore, SoodResponder  # noqa: E402

PASSED: list[str] = []


def check(cond, label):
    if not cond:
        raise AssertionError(label)
    PASSED.append(label)
    print("  ok -", label)


async def until(pred, timeout=5.0, label="condition"):
    end = asyncio.get_running_loop().time() + timeout
    while True:
        try:
            if pred():
                return True
        except (KeyError, IndexError):
            pass
        if asyncio.get_running_loop().time() > end:
            raise AssertionError(f"timeout: {label}")
        await asyncio.sleep(0.03)


def test_moo():
    print("MOO encoding")
    raw = roon.encode("REQUEST", "com.roonlabs.volumecontrol:1/set_volume", 7, {"control_key": "k", "mode": "absolute", "value": 3})
    msg = roon.parse(raw)
    check(msg.verb == "REQUEST" and msg.service == "com.roonlabs.volumecontrol:1" and msg.name == "set_volume", "request first line")
    check(msg.request_id == 7 and msg.body["value"] == 3, "headers + json body")
    msg = roon.parse(roon.encode("COMPLETE", "Success", 3))
    check(msg.verb == "COMPLETE" and msg.name == "Success" and msg.body is None, "message without body")
    check(roon.parse(b"garbage") is None, "garbage rejected")


async def test_discovery(core_port):
    print("SOOD discovery")
    loop = asyncio.get_running_loop()
    responder = SoodResponder(core_port)
    transport, _ = await loop.create_datagram_endpoint(lambda: responder, local_addr=("127.0.0.1", 0))
    port = transport.get_extra_info("sockname")[1]
    old = (roon.SOOD_MULTICAST, roon.SOOD_PORT)
    roon.SOOD_MULTICAST, roon.SOOD_PORT = "127.0.0.1", port
    try:
        found = await roon.discover_core(timeout=3)
    finally:
        roon.SOOD_MULTICAST, roon.SOOD_PORT = old
        transport.close()
    check(found == ("127.0.0.1", core_port) and responder.queries >= 1, f"core discovered via SOOD ({found})")


async def test_bridge(rx: MockReceiver, core: MockRoonCore, tmp: str):
    print("Roon bridge (MODE=roon)")
    import avr
    from config import AvrDevice
    from roon_bridge import RoonManager, RoonSettings

    settings = RoonSettings(enabled=True, core_host="127.0.0.1", core_port=core.port, source="STRM BOX", volume_max=60)
    state_file = os.path.join(tmp, "roon.json")
    manager = RoonManager(settings, state_file)
    device = AvrDevice(id="127_0_0_1", name="Onkyo Wohnzimmer", address="127.0.0.1")
    receiver = avr.OnkyoDevice(device, loop=asyncio.get_running_loop())
    await receiver.connect()
    await manager.add_receiver(receiver, device.name)
    manager.start()
    key = "onkyo_127_0_0_1"
    vol = lambda: core.controls["volume"][key]  # noqa: E731
    src = lambda: core.controls["source"][key]  # noqa: E731

    await asyncio.wait_for(core.subscribed.wait(), 10)
    check("token" not in core.register_requests[0], "first registration without token")
    check(json.load(open(state_file))["tokens"][roon_core_id()] == core.token, "token stored")
    await until(lambda: vol()["volume_value"] == 40, label="initial volume")
    check(vol()["display_name"] == "Onkyo Wohnzimmer" and vol()["volume_max"] == 60, "volume control registered (name, max)")
    check(src()["status"] == "deselected", "source control: on, other input -> deselected")
    await until(lambda: "connected" in core.status.get("message", "") and not core.status.get("is_error"), label="status")
    check(True, "status shows receiver connected")

    r = await core.request("com.roonlabs.volumecontrol:1/set_volume", {"control_key": key, "mode": "absolute", "value": 30})
    check(r.name == "Success" and await rx_is(rx, "MVL", "1E"), "Roon absolute volume 30 -> MVL1E")
    await core.request("com.roonlabs.volumecontrol:1/set_volume", {"control_key": key, "mode": "relative_step", "value": 1})
    check(await rx_is(rx, "MVL", "1F"), "relative step +1 -> 31")
    await core.request("com.roonlabs.volumecontrol:1/set_volume", {"control_key": key, "mode": "absolute", "value": 99})
    check(await rx_is(rx, "MVL", "3C"), "volume capped at ROON_VOLUME_MAX (60)")
    await rx.push("MVL2A")
    await until(lambda: vol()["volume_value"] == 42, label="volume from receiver")
    check(True, "volume change on receiver reaches Roon")
    await core.request("com.roonlabs.volumecontrol:1/set_mute", {"control_key": key, "mode": "on"})
    check(await rx_is(rx, "AMT", "01"), "mute on")
    await until(lambda: vol()["is_muted"] is True, label="muted state")
    await core.request("com.roonlabs.volumecontrol:1/set_mute", {"control_key": key, "mode": "toggle"})
    check(await rx_logged(rx, "AMTTG"), "mute toggle")

    r = await core.request("com.roonlabs.sourcecontrol:1/convenience_switch", {"control_key": key})
    check(r.name == "Success" and await rx_is(rx, "SLI", "11"), "convenience switch selects STRM BOX (11)")
    await until(lambda: src()["status"] == "selected", label="selected")
    check(True, "source status selected")
    await core.request("com.roonlabs.sourcecontrol:1/standby", {"control_key": key})
    check(await rx_is(rx, "PWR", "00"), "standby -> PWR00")
    await until(lambda: src()["status"] == "standby", label="standby status")
    check(True, "source status standby")
    rx.state["SLI"] = "10"
    rx.log.clear()
    await core.request("com.roonlabs.sourcecontrol:1/convenience_switch", {"control_key": key})
    check(await rx_is(rx, "PWR", "01") and await rx_is(rx, "SLI", "11"), "convenience switch from standby: power on + input")
    check(rx.log.index("PWR01") < rx.log.index("SLI11"), "power on before input switch")

    r = await core.request("com.roonlabs.volumecontrol:1/set_volume", {"control_key": "nope", "mode": "absolute", "value": 1})
    check(r.name == "InvalidRequest", "unknown control -> InvalidRequest")
    r = await core.request("com.roonlabs.ping:1/ping")
    check(r.name == "Success", "ping")

    # core restart -> re-register with stored token, controls come back
    await core.drop()
    await asyncio.wait_for(core.subscribed.wait(), 15)
    check(core.register_requests[-1].get("token") == core.token, "re-registration uses stored token")
    check(key in core.controls["volume"] and key in core.controls["source"], "controls available after core reconnect")

    # receiver lost -> Roon status shows error
    await rx.stop()
    await until(lambda: core.status.get("is_error") is True, timeout=10, label="error status")
    check("not reachable" in core.status["message"], "receiver offline shown in Roon status")
    check(src()["status"] == "standby", "source status standby while receiver offline")
    await rx.start("127.0.0.1", 60128)
    await until(lambda: core.status.get("is_error") is False, timeout=15, label="recovered")
    check(True, "receiver reconnect recovers Roon status")

    await manager.stop()
    await receiver.disconnect()


def roon_core_id():
    from mock_roon_core import CORE_ID
    return CORE_ID


async def rx_is(rx, key, value, timeout=3.0):
    end = asyncio.get_running_loop().time() + timeout
    while rx.state.get(key) != value:
        if asyncio.get_running_loop().time() > end:
            return False
        await asyncio.sleep(0.02)
    return True


async def rx_logged(rx, entry, timeout=3.0):
    end = asyncio.get_running_loop().time() + timeout
    while entry not in rx.log:
        if asyncio.get_running_loop().time() > end:
            return False
        await asyncio.sleep(0.02)
    return True


async def test_full_mode(rx: MockReceiver, tmp: str):
    print("container MODE=full (UC driver + Roon)")
    core = MockRoonCore()
    await core.start()
    data = os.path.join(tmp, "full")
    os.makedirs(data)
    with open(os.path.join(data, "config.json"), "w") as f:
        json.dump({"devices": [{"id": "127_0_0_1", "name": "Onkyo AVR", "address": "127.0.0.1"}]}, f)
    env = dict(os.environ, MODE="full", DATA_DIR=data, ROON_CORE=f"127.0.0.1:{core.port}", ROON_SOURCE="11",
               UC_INTEGRATION_HTTP_PORT="9398", UC_DISABLE_MDNS_PUBLISH="true", LOG_LEVEL="DEBUG")
    log = open(os.path.join(data, "container.log"), "w")
    proc = subprocess.Popen([sys.executable, "intg-onkyoavr/container.py"], cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
    try:
        await asyncio.wait_for(core.subscribed.wait(), 15)
        key = "onkyo_127_0_0_1"
        await until(lambda: key in core.controls["volume"], label="controls")
        check(True, "full mode: receiver from UC config exposed to Roon without a remote")
        await until(lambda: core.controls["volume"][key]["volume_value"] > 0, label="volume")
        # Remote connects and goes to standby -> receiver must stay connected
        for _ in range(50):
            try:
                ws = await websockets.connect("ws://127.0.0.1:9398/ws")
                break
            except OSError:
                await asyncio.sleep(0.2)
        async with ws:
            await ws.send(json.dumps({"kind": "event", "msg": "enter_standby"}))
            await asyncio.sleep(1.0)
        rx.log.clear()
        r = await core.request("com.roonlabs.volumecontrol:1/set_volume", {"control_key": key, "mode": "absolute", "value": 25})
        check(r.name == "Success" and await rx_is(rx, "MVL", "19"), "Roon still works while the remote sleeps")
        check(rx.log == ["MVL19"], "no reconnect/disconnect caused by remote standby")
    except Exception:
        print(open(os.path.join(data, "container.log")).read()[-4000:])
        raise
    finally:
        proc.terminate()
        for _ in range(100):
            if proc.poll() is not None:
                break
            await asyncio.sleep(0.1)
        if proc.poll() is None:
            proc.kill()
        await core.stop()


async def test_roon_mode_process(rx: MockReceiver, tmp: str):
    print("container MODE=roon as process")
    core = MockRoonCore()
    await core.start()
    data = os.path.join(tmp, "roononly")
    env = dict(os.environ, MODE="roon", DATA_DIR=data, ONKYO_HOST="127.0.0.1", ONKYO_NAME="NR686",
               ROON_CORE=f"127.0.0.1:{core.port}", ROON_SOURCE="STRM BOX")
    os.makedirs(data, exist_ok=True)
    log = open(os.path.join(data, "container.log"), "w")
    proc = subprocess.Popen([sys.executable, "intg-onkyoavr/container.py"], cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
    try:
        await asyncio.wait_for(core.subscribed.wait(), 15)
        await until(lambda: "onkyo_127_0_0_1" in core.controls["volume"], label="controls")
        check(core.controls["volume"]["onkyo_127_0_0_1"]["display_name"] == "NR686", "roon mode: receiver from env")
        check(os.path.exists(os.path.join(data, "roon.json")), "token persisted in DATA_DIR")
    finally:
        proc.send_signal(15)
        # wait asynchronously: the mock core runs in this event loop and must
        # answer the WebSocket close handshake
        for _ in range(100):
            if proc.poll() is not None:
                break
            await asyncio.sleep(0.1)
        if proc.poll() is None:
            proc.kill()
            print(open(os.path.join(data, "container.log")).read()[-3000:])
        check(proc.returncode == 0, "clean shutdown on SIGTERM")
        await core.stop()


async def main():
    test_moo()
    tmp = tempfile.mkdtemp()
    rx = MockReceiver()
    await rx.start("127.0.0.1", 60128)
    core = MockRoonCore()
    await core.start()
    try:
        await test_discovery(core.port)
        await test_bridge(rx, core, tmp)
        rx.state.update({"PWR": "01", "SLI": "10"})
        await test_full_mode(rx, tmp)
        await test_roon_mode_process(rx, tmp)
    finally:
        await core.stop()
        await rx.stop()
        shutil.rmtree(tmp, ignore_errors=True)
    print(f"\nALL {len(PASSED)} CHECKS PASSED")


if __name__ == "__main__":
    asyncio.run(main())
