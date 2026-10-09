"""
End-to-end test: starts the real driver process, a mock TX-NR686 and talks to
the driver over WebSocket like the Remote does.

Run:  python tests/test_e2e.py      (needs: pip install -r requirements.txt websockets)
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
from mock_receiver import MockReceiver  # noqa: E402

WS_PORT = 9399
PASSED: list[str] = []


def check(cond, label):
    if not cond:
        raise AssertionError(label)
    PASSED.append(label)
    print("  ok -", label)


class Remote:
    """Minimal fake of the Remote's side of the integration WebSocket."""

    def __init__(self, ws):
        self.ws = ws
        self.events: list[dict] = []
        self._rid = 0
        self.mark = 0  # events index before the last request
        self._waiters: dict[int, asyncio.Future] = {}
        self._task = asyncio.get_running_loop().create_task(self._read())

    async def _read(self):
        async for raw in self.ws:
            msg = json.loads(raw)
            if msg.get("kind") == "event":
                self.events.append(msg)
            elif msg.get("kind") == "resp" and msg.get("req_id") in self._waiters:
                self._waiters.pop(msg["req_id"]).set_result(msg)
            elif msg.get("kind") == "req":  # driver asks us (e.g. supported entity types)
                reply = {"kind": "resp", "req_id": msg["id"], "code": 200, "msg": "supported_entity_types",
                         "msg_data": ["media_player", "remote", "select", "light", "button", "switch", "sensor"]}
                if msg.get("msg") == "get_version":
                    reply.update(msg="version", msg_data={"core": "0.99", "api": "0.20.0"})
                await self.ws.send(json.dumps(reply))

    async def req(self, msg, data=None):
        self._rid += 1
        fut = asyncio.get_running_loop().create_future()
        self._waiters[self._rid] = fut
        payload = {"kind": "req", "id": self._rid, "msg": msg}
        self.mark = len(self.events)
        if data is not None:
            payload["msg_data"] = data
        await self.ws.send(json.dumps(payload))
        return await asyncio.wait_for(fut, 15)

    async def event(self, msg):
        await self.ws.send(json.dumps({"kind": "event", "msg": msg}))

    async def wait_event(self, pred, timeout=8.0, label="event", since=None):
        end = asyncio.get_running_loop().time() + timeout
        # Events can arrive before the response of the request that caused them,
        # so by default look at everything since the last request was sent.
        start = self.mark if since is None else since
        while True:
            for e in self.events[start:]:
                if pred(e):
                    return e
            if asyncio.get_running_loop().time() > end:
                raise AssertionError(f"timeout waiting for {label}")
            await asyncio.sleep(0.05)

    def last_setup(self):
        return [e for e in self.events if e["msg"] == "driver_setup_change"][-1]["msg_data"]

    async def setup_step(self, msg, data):
        n = len([e for e in self.events if e["msg"] == "driver_setup_change"])
        await self.req(msg, data)
        end = asyncio.get_running_loop().time() + 10
        while True:
            changes = [e for e in self.events if e["msg"] == "driver_setup_change"]
            if len(changes) > n and changes[-1]["msg_data"].get("state") in ("WAIT_USER_ACTION", "OK", "ERROR"):
                return changes[-1]["msg_data"]
            if asyncio.get_running_loop().time() > end:
                raise AssertionError("setup step timeout")
            await asyncio.sleep(0.05)

    async def states(self):
        r = await self.req("get_entity_states")
        return {s["entity_id"]: s["attributes"] for s in r["msg_data"]}

    async def command(self, entity_id, cmd_id, params=None):
        etype = entity_id.split(".")[1].lower() if entity_id.startswith("EntityTypes.") else entity_id.split(".")[0]
        data = {"entity_type": etype, "entity_id": entity_id, "cmd_id": cmd_id}
        if params:
            data["params"] = params
        return (await self.req("entity_command", data))["code"]


async def rx_is(rx, key, value, timeout=2.0):
    """Wait until the mock receiver has processed a command (it runs concurrently)."""
    end = asyncio.get_running_loop().time() + timeout
    while rx.state.get(key) != value:
        if asyncio.get_running_loop().time() > end:
            return False
        await asyncio.sleep(0.02)
    return True


async def rx_logged(rx, entry, timeout=2.0):
    end = asyncio.get_running_loop().time() + timeout
    while entry not in rx.log:
        if asyncio.get_running_loop().time() > end:
            return False
        await asyncio.sleep(0.02)
    return True


def settings_of(setup_event):
    return {s["id"]: s for s in setup_event["require_user_action"]["input"]["settings"]}


def start_driver(cfg_dir):
    env = dict(os.environ, UC_CONFIG_HOME=cfg_dir, UC_INTEGRATION_HTTP_PORT=str(WS_PORT),
               UC_LOG_LEVEL="DEBUG", UC_DISABLE_MDNS_PUBLISH="true")
    os.makedirs(cfg_dir, exist_ok=True)
    log = open(os.path.join(cfg_dir, "driver.log"), "w")
    return subprocess.Popen([sys.executable, "intg-onkyoavr/driver.py"], cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)


async def wait_port():
    for _ in range(60):
        try:
            async with websockets.connect(f"ws://127.0.0.1:{WS_PORT}/ws"):
                return
        except OSError:
            await asyncio.sleep(0.2)
    raise AssertionError("driver did not start")


MP = "EntityTypes.MEDIA_PLAYER.onkyo_127_0_0_1"
RM = "EntityTypes.REMOTE.onkyo_127_0_0_1_remote"
SEL_IN = "EntityTypes.SELECT.onkyo_127_0_0_1_input"
SEL_LM = "EntityTypes.SELECT.onkyo_127_0_0_1_soundmode"


async def scenario_fresh_setup(rx: MockReceiver, cfg_dir: str):
    print("fresh setup, dropdowns, reconfigure")
    proc = start_driver(cfg_dir)
    try:
        await wait_port()
        async with websockets.connect(f"ws://127.0.0.1:{WS_PORT}/ws") as ws:
            r = Remote(ws)
            ver = (await r.req("get_driver_version"))["msg_data"]["version"]["driver"]
            check(ver == "0.5.0", f"driver version {ver}")

            ev = await r.setup_step("setup_driver", {"reconfigure": False, "setup_data": {"series": "TX-NR6xx", "address": "http://127.0.0.1/", "name": "Wohnzimmer"}})
            s = settings_of(ev)
            inputs_text = s["inputs"]["field"]["textarea"]["value"]
            check("10 = Apple TV" in inputs_text and "02 = PS5" in inputs_text, "names form prefilled with receiver names (NRI)")
            check("05 =" not in inputs_text and "2D =" not in inputs_text, "inputs hidden on receiver / other zone not listed")
            check("TX-NR686" in s["status"]["field"]["label"]["value"]["de"], "model detected")
            check("80 = Dolby Atmos/Surround" in s["modes"]["field"]["textarea"]["value"], "modern listening mode names")

            ev = await r.setup_step("set_driver_user_data", {"input_values": {"inputs": "10 = Apple TV\nfoo = bar", "modes": "00", "naming": "modern"}})
            check("error" in settings_of(ev), "invalid line -> form again with error")

            new_inputs = inputs_text.replace("02 = PS5", "02 = PlayStation").replace("25 = AM\n", "")
            new_modes = "80 = Kino\n82 = DTS Neural:X\n00 = Stereo\nPURE DIRECT\n03\n05"
            ev = await r.setup_step("set_driver_user_data", {"input_values": {"inputs": new_inputs, "modes": new_modes, "naming": "modern"}})
            check(ev["state"] == "OK", "setup completed")

            ids = [e["entity_id"] for e in (await r.req("get_available_entities"))["msg_data"]["available_entities"]]
            check(set(ids) == {MP, RM, SEL_IN, SEL_LM}, "4 entities with legacy ID format")
            await r.req("subscribe_events", {"entity_ids": ids})
            await r.wait_event(lambda e: e["msg"] == "entity_change" and e["msg_data"]["entity_id"] == SEL_IN
                               and e["msg_data"]["attributes"].get("current_option") == "Apple TV", label="input select state")
            await r.wait_event(lambda e: e["msg"] == "entity_change" and e["msg_data"]["entity_id"] == SEL_LM
                               and e["msg_data"]["attributes"].get("current_option") == "Kino", label="mode select state")
            st = await r.states()
            check(st[SEL_IN]["state"] == "ON" and "PlayStation" in st[SEL_IN]["options"] and "AM" not in st[SEL_IN]["options"], "input dropdown uses own names")
            check(st[SEL_LM]["current_option"] == "Kino" and st[SEL_LM]["options"][:2] == ["Kino", "DTS Neural:X"], "sound mode dropdown uses own names")
            check("Pure Direct" in st[SEL_LM]["options"] and "Game-RPG" in st[SEL_LM]["options"], "code-only / name-only lines get standard names")
            check(st[MP]["source_list"] == st[SEL_IN]["options"] and st[MP]["source"] == "Apple TV", "media player uses same names")

            check(await r.command(SEL_IN, "select_option", {"option": "PlayStation"}) == 200 and await rx_is(rx, "SLI", "02"), "select input -> SLI02")
            await r.wait_event(lambda e: e["msg"] == "entity_change" and e["msg_data"]["entity_id"] == SEL_IN
                               and e["msg_data"]["attributes"].get("current_option") == "PlayStation", label="current option PlayStation")
            check(True, "dropdown follows receiver")
            check(await r.command(SEL_IN, "select_option", {"option": "gibt es nicht"}) == 400, "unknown option -> 400")
            check(await r.command(MP, "select_source", {"source": "NETWORK"}) == 200 and await rx_is(rx, "SLI", "2B"), "old source name NETWORK still works")
            check(await r.command(MP, "select_source", {"source": "PHONO"}) == 200 and await rx_is(rx, "SLI", "22"), "PHONO -> 22 (was 20 before)")
            check(await r.command(RM, "send_cmd", {"command": "INPUT_BLUETOOTH"}) == 200 and await rx_is(rx, "SLI", "2E"), "INPUT_BLUETOOTH -> 2E (was AirPlay)")
            check(await r.command(MP, "select_sound_mode", {"mode": "Stereo"}) == 200 and await rx_is(rx, "LMD", "00"), "select sound mode by display name")
            await r.wait_event(lambda e: e["msg"] == "entity_change" and e["msg_data"]["entity_id"] == SEL_LM
                               and e["msg_data"]["attributes"].get("current_option") == "Stereo", label="mode Stereo")
            check(await r.command(MP, "select_sound_mode", {"mode": "PLII/PLIIx MOVIE"}) == 200 and await rx_is(rx, "LMD", "80"), "old mode name still works")
            await r.wait_event(lambda e: e["msg"] == "entity_change" and e["msg_data"]["entity_id"] == SEL_LM
                               and e["msg_data"]["attributes"].get("current_option") == "Kino", label="mode Kino")
            check(await r.command(SEL_LM, "select_next") == 200 and await rx_is(rx, "LMD", "82"), "sound mode select_next")
            check(await r.command(RM, "send_cmd", {"command": "LISTENING_MODE_GAME"}) == 200 and await rx_logged(rx, "LMDGAME"), "LISTENING_MODE_GAME cycles game modes")

            await rx.push("SLI2D")  # AirPlay started on the receiver, hidden in our list
            e = await r.wait_event(lambda e: e["msg"] == "entity_change" and e["msg_data"]["entity_id"] == SEL_IN
                                   and e["msg_data"]["attributes"].get("current_option") == "AIRPLAY", label="hidden input")
            check("AIRPLAY" in e["msg_data"]["attributes"]["options"], "active hidden input shown in dropdown")

            # reconfigure: edit names, applied without reconnect
            ev = await r.setup_step("setup_driver", {"reconfigure": True, "setup_data": {}})
            items = [i["id"] for i in settings_of(ev)["action"]["field"]["dropdown"]["items"]]
            check(items == ["edit:127_0_0_1", "add", "remove:127_0_0_1"], "reconfigure offers edit/add/remove")
            ev = await r.setup_step("set_driver_user_data", {"input_values": {"action": "edit:127_0_0_1"}})
            txt = settings_of(ev)["inputs"]["field"]["textarea"]["value"]
            check("02 = PlayStation" in txt and "25 = AM" not in txt, "edit shows saved lists")
            mark = len(r.events)
            ev = await r.setup_step("set_driver_user_data", {"input_values": {"inputs": txt + "\n2D = AirPlay", "modes": new_modes, "naming": "modern"}})
            check(ev["state"] == "OK", "reconfigure saved")
            e = await r.wait_event(lambda e: e["msg"] == "entity_change" and e["msg_data"]["entity_id"] == SEL_IN
                                   and "AirPlay" in e["msg_data"]["attributes"].get("options", []), label="options updated", since=mark)
            check(e["msg_data"]["attributes"]["current_option"] == "AirPlay", "new name applied live")
            check(await r.command(MP, "volume_up") == 200, "receiver still connected after reconfigure")

            # standby / wake
            rx.log.clear()
            await r.event("enter_standby")
            await asyncio.sleep(0.5)
            await r.event("exit_standby")
            await asyncio.sleep(1.5)
            check(await r.command(SEL_IN, "select_option", {"option": "TV"}) == 200 and await rx_is(rx, "SLI", "12"), "dropdown works after standby")
    finally:
        proc.terminate()
        proc.wait(5)
    cfg = json.load(open(os.path.join(cfg_dir, "config.json")))["devices"][0]
    check(cfg["modern"] is True and cfg["model"] == "TX-NR686" and ["02", "PlayStation"] in cfg["inputs"], "config.json stores names")


async def scenario_upgrade_from_04(rx: MockReceiver, cfg_dir: str):
    print("upgrade: config from v0.4.x without names")
    with open(os.path.join(cfg_dir, "config.json"), "w") as f:
        json.dump({"devices": [{"id": "127_0_0_1", "name": "Onkyo AVR", "address": "127.0.0.1", "series": "TX-NR6xx", "always_on": True}]}, f)
    rx.state["SLI"] = "02"
    proc = start_driver(cfg_dir)
    try:
        await wait_port()
        async with websockets.connect(f"ws://127.0.0.1:{WS_PORT}/ws") as ws:
            r = Remote(ws)
            await r.req("subscribe_events", {"entity_ids": [MP, RM]})
            await r.wait_event(lambda e: e["msg"] == "entity_change" and e["msg_data"]["entity_id"] == MP
                                   and "PS5" in e["msg_data"]["attributes"].get("source_list", []), label="NRI lists")
            check(True, "old config: input names read from receiver automatically")
            await asyncio.sleep(0.3)
            st = await r.states()
            check(st[MP]["source"] == "PS5" and "Dolby Atmos/Surround" in st[MP]["sound_mode_list"], "old media player entity keeps working with new names")
            ids = [e["entity_id"] for e in (await r.req("get_available_entities"))["msg_data"]["available_entities"]]
            check(SEL_IN in ids and SEL_LM in ids, "new dropdowns offered for existing receiver")
    finally:
        proc.terminate()
        proc.wait(5)


async def main():
    rx = MockReceiver()
    await rx.start("127.0.0.1", 60128)
    tmp = tempfile.mkdtemp()
    try:
        await scenario_fresh_setup(rx, os.path.join(tmp, "a"))
        rx2_dir = os.path.join(tmp, "b")
        os.makedirs(rx2_dir)
        await scenario_upgrade_from_04(rx, rx2_dir)
    except Exception:
        for d in ("a", "b"):
            p = os.path.join(tmp, d, "driver.log")
            if os.path.exists(p):
                print(f"--- {d}/driver.log (tail)")
                print("".join(open(p).readlines()[-int(os.environ.get("E2E_LOG_LINES", "40")):]))
        raise
    finally:
        await rx.stop()
        shutil.rmtree(tmp, ignore_errors=True)
    print(f"\nALL {len(PASSED)} CHECKS PASSED")


if __name__ == "__main__":
    os.makedirs(tempfile.gettempdir(), exist_ok=True)
    asyncio.run(main())
