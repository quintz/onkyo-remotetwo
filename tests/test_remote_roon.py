"""
Roon on the Remote + keep awake while Roon plays.

1. power.py against a mock Core REST API (API key via PIN, battery, inhibitors)
2. The real driver process like on the Remote (no container env):
   setup page "Roon & Standby", Roon registration incl. transport zones,
   playback -> standby inhibitor, stop -> released, Remote standby/wake.

Run:  python tests/test_remote_roon.py
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

import power  # noqa: E402
from mock_core_api import MockCoreApi  # noqa: E402
from mock_receiver import MockReceiver  # noqa: E402
from mock_roon_core import MockRoonCore  # noqa: E402
from test_e2e import Remote, settings_of  # noqa: E402

WS_PORT = 9396
PASSED: list[str] = []
KEY = "onkyo_127_0_0_1"


def check(cond, label):
    if not cond:
        raise AssertionError(label)
    PASSED.append(label)
    print("  ok -", label)


async def until(pred, timeout=8.0, label="condition"):
    end = asyncio.get_running_loop().time() + timeout
    while True:
        try:
            if pred():
                return True
        except (KeyError, IndexError, AttributeError):
            pass
        if asyncio.get_running_loop().time() > end:
            raise AssertionError(f"timeout: {label}")
        await asyncio.sleep(0.05)


def zone(state: str) -> dict:
    return {
        "zone_id": "z1",
        "display_name": "Wohnzimmer",
        "state": state,
        "outputs": [{"output_id": "o1", "display_name": "Wohnzimmer",
                     "source_controls": [{"control_key": KEY, "display_name": "Onkyo AVR", "status": "selected"}]}],
    }


async def test_power_unit():
    print("power.py (Core API, keep awake)")
    api_mock = MockCoreApi(pin="4711")
    await api_mock.start()
    url = f"http://127.0.0.1:{api_mock.port}"
    api = power.CoreApi(url)
    try:
        await api.create_api_key("0000")
        check(False, "wrong PIN rejected")
    except power.CoreApiError as e:
        check(e.status == 401, "wrong PIN rejected")
    key = await api.create_api_key("4711")
    check(key and len(api_mock.keys) == 1, "API key created with PIN")
    key2 = await power.CoreApi(url).create_api_key("4711")
    check(key2 != key and len(api_mock.keys) == 1, "re-entering the PIN replaces the old key")
    api = power.CoreApi(url, key2)
    check((await api.battery())["capacity"] == 80, "battery via API key")
    check(await power.CoreApi(url, "bogus").request("GET", "/system/power/battery") != (200, None)
          and (await power.CoreApi(url, "bogus").request("GET", "/system/power/battery"))[0] == 401, "invalid key -> 401")

    old = power.RENEW_INTERVAL
    power.RENEW_INTERVAL = 0.2
    try:
        keeper = power.AwakeKeeper(api, min_battery=30)
        await keeper.set_playing(True)
        await until(lambda: power.INHIBITOR_ID in api_mock.inhibitors, label="inhibitor")
        inh = api_mock.inhibitors[power.INHIBITOR_ID]
        check(inh["delay"] == power.INHIBITOR_DELAY and inh["who"], "temporary inhibitor set while playing")
        n = api_mock.log.count(("POST", "/api/system/power/standby_inhibitors"))
        await asyncio.sleep(0.5)
        check(api_mock.log.count(("POST", "/api/system/power/standby_inhibitors")) > n, "inhibitor renewed periodically")
        api_mock.battery = {"capacity": 20, "status": "DISCHARGING", "power_supply": False}
        await until(lambda: power.INHIBITOR_ID not in api_mock.inhibitors, label="low battery release")
        check(not keeper.active, "battery below limit -> Remote may sleep")
        api_mock.battery = {"capacity": 20, "status": "CHARGING", "power_supply": True}
        await until(lambda: power.INHIBITOR_ID in api_mock.inhibitors, label="docked")
        check(True, "docked -> kept awake regardless of battery")
        await keeper.set_playing(False)
        check(power.INHIBITOR_ID not in api_mock.inhibitors and not keeper.active, "playback stopped -> inhibitor removed")
    finally:
        power.RENEW_INTERVAL = old
        await api_mock.stop()


def start_driver(cfg_dir):
    env = dict(os.environ, UC_CONFIG_HOME=cfg_dir, UC_INTEGRATION_HTTP_PORT=str(WS_PORT),
               UC_LOG_LEVEL="DEBUG", UC_DISABLE_MDNS_PUBLISH="true")
    env.pop("ROON_ENABLED", None)
    log = open(os.path.join(cfg_dir, "driver.log"), "w")
    return subprocess.Popen([sys.executable, "intg-onkyoavr/driver.py"], cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)


async def connect_ws():
    for _ in range(80):
        try:
            return await websockets.connect(f"ws://127.0.0.1:{WS_PORT}/ws")
        except OSError:
            await asyncio.sleep(0.2)
    raise AssertionError("driver did not start")


async def test_driver_on_remote(rx: MockReceiver, tmp: str):
    print("driver on the Remote with Roon + keep awake")
    core = MockRoonCore()
    await core.start()
    api_mock = MockCoreApi(pin="4711")
    await api_mock.start()
    cfg = os.path.join(tmp, "remote")
    os.makedirs(cfg)
    with open(os.path.join(cfg, "config.json"), "w") as f:
        json.dump({"devices": [{"id": "127_0_0_1", "name": "Onkyo AVR", "address": "127.0.0.1",
                                "inputs": [["10", "Apple TV"], ["11", "Roon"]], "modern": True}]}, f)
    proc = start_driver(cfg)
    try:
        ws = await connect_ws()
        async with ws:
            r = Remote(ws)
            ev = await r.setup_step("setup_driver", {"reconfigure": True, "setup_data": {}})
            items = [i["id"] for i in settings_of(ev)["action"]["field"]["dropdown"]["items"]]
            check("roon" in items, "reconfigure offers 'Roon & Standby'")
            ev = await r.setup_step("set_driver_user_data", {"input_values": {"action": "roon"}})
            s = settings_of(ev)
            src_items = [i["id"] for i in s["roon_source"]["field"]["dropdown"]["items"]]
            check(src_items == ["", "10", "11"], "Roon input dropdown uses the receiver's own names")
            form = {"roon_enabled": "true", "roon_source": "11", "roon_volume_max": "60", "keep_awake": "true",
                    "min_battery": "30", "roon_zone": "", "roon_core": f"127.0.0.1:{core.port}",
                    "core_api_url": f"http://127.0.0.1:{api_mock.port}"}
            ev = await r.setup_step("set_driver_user_data", {"input_values": dict(form, pin="")})
            check("error" in settings_of(ev), "keep awake without PIN -> asks for PIN")
            ev = await r.setup_step("set_driver_user_data", {"input_values": dict(form, pin="9999")})
            check("PIN" in settings_of(ev)["error"]["field"]["label"]["value"]["en"], "wrong PIN -> error")
            ev = await r.setup_step("set_driver_user_data", {"input_values": dict(form, pin="4711")})
            check(ev["state"] == "OK", "Roon settings saved")
            saved = json.load(open(os.path.join(cfg, "settings.json")))
            check(saved["core_api_key"].startswith("secret-") and "4711" not in json.dumps(saved), "API key stored, PIN not stored")

            await asyncio.wait_for(core.subscribed.wait(), 15)
            await asyncio.wait_for(core.zone_subscribed.wait(), 10)
            check("com.roonlabs.transport:2" in core.register_requests[-1]["optional_services"], "registers for transport (zones)")
            await until(lambda: core.controls["volume"][KEY]["volume_max"] == 60, label="controls")
            check(True, "Roon controls from the driver on the Remote")
            await until(lambda: core.controls["volume"][KEY]["volume_value"] == 40, label="volume")

            # Roon starts playing -> keep awake
            await core.set_zone(zone("playing"))
            await until(lambda: power.INHIBITOR_ID in api_mock.inhibitors, label="inhibitor on play")
            check(api_mock.inhibitors[power.INHIBITOR_ID]["delay"] == power.INHIBITOR_DELAY, "Roon plays -> Remote kept awake (temporary inhibitor)")
            await core.set_zone(zone("paused"))
            await until(lambda: power.INHIBITOR_ID not in api_mock.inhibitors, label="released")
            check(True, "Roon paused -> Remote may sleep again")
            await core.set_zone(dict(zone("playing"), zone_id="z2", display_name="Küche",
                                     outputs=[{"output_id": "o2", "display_name": "Küche", "source_controls": []}]))
            await asyncio.sleep(0.5)
            check(power.INHIBITOR_ID not in api_mock.inhibitors, "other zone playing -> not kept awake")

            # remote removes entities / disconnects -> receiver stays (Roon needs it)
            await r.req("unsubscribe_events", {"entity_ids": ["EntityTypes.MEDIA_PLAYER.onkyo_127_0_0_1"]})
            await asyncio.sleep(0.5)
            check(len(rx.clients) == 1, "unsubscribe doesn't disconnect the receiver while Roon is on")

            # Remote standby / wake
            regs = len(core.register_requests)
            await r.event("enter_standby")
            await until(lambda: len(rx.clients) == 0, label="receiver disconnected on standby")
            check(True, "Remote standby -> receiver connection closed (as before)")
            await r.event("exit_standby")
            await until(lambda: len(core.register_requests) > regs, timeout=15, label="roon re-register")
            check(core.register_requests[-1].get("token") == core.token, "wake up -> Roon reconnects with token")
            await until(lambda: len(rx.clients) == 1, label="receiver reconnected")
            check(True, "wake up -> receiver reconnected")
            r2 = await core.request("com.roonlabs.volumecontrol:1/set_volume", {"control_key": KEY, "mode": "absolute", "value": 22})
            check(r2.name == "Success" and await rx_is(rx, "MVL", "16"), "Roon volume works after wake up")

            # disable Roon again
            ev = await r.setup_step("setup_driver", {"reconfigure": True, "setup_data": {}})
            ev = await r.setup_step("set_driver_user_data", {"input_values": {"action": "roon"}})
            check(settings_of(ev)["roon_enabled"]["field"]["checkbox"]["value"] is True, "form shows saved settings")
            ev = await r.setup_step("set_driver_user_data", {"input_values": dict(form, roon_enabled="false", pin="")})
            check(ev["state"] == "OK", "Roon disabled")
            await until(lambda: not core.connected.is_set(), label="roon disconnected")
            check(True, "disabling Roon closes the Roon connection")
    except Exception:
        print(open(os.path.join(cfg, "driver.log")).read()[-5000:])
        raise
    finally:
        proc.terminate()
        for _ in range(50):
            if proc.poll() is not None:
                break
            await asyncio.sleep(0.1)
        if proc.poll() is None:
            proc.kill()
        await core.stop()
        await api_mock.stop()


async def rx_is(rx, key, value, timeout=3.0):
    end = asyncio.get_running_loop().time() + timeout
    while rx.state.get(key) != value:
        if asyncio.get_running_loop().time() > end:
            return False
        await asyncio.sleep(0.02)
    return True


async def main():
    tmp = tempfile.mkdtemp()
    await test_power_unit()
    rx = MockReceiver()
    await rx.start("127.0.0.1", 60128)
    try:
        await test_driver_on_remote(rx, tmp)
    finally:
        await rx.stop()
        shutil.rmtree(tmp, ignore_errors=True)
    print(f"\nALL {len(PASSED)} CHECKS PASSED")


if __name__ == "__main__":
    asyncio.run(main())
