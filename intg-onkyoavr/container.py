#!/usr/bin/env python3
"""
Entry point for the Docker container (e.g. on Proxmox).

MODE=roon (default)
    Roon only: connects to the receiver ONKYO_HOST and offers volume/source
    control to Roon. The Remote keeps using the integration installed on the
    Remote itself -> the Remote works even when the container is down.

MODE=full
    Runs the complete Remote Two integration driver (discovered by the Remote
    via mDNS) plus Roon (ROON_ENABLED=1 by default). Receivers are configured
    in the Remote's setup and stay connected permanently.

Environment:
    ONKYO_HOST          receiver IP (MODE=roon, required)
    ONKYO_NAME          name shown in Roon (default "Onkyo")
    ROON_SOURCE         input Roon switches to, code or name (e.g. 11, "STRM BOX", "NET")
    ROON_VOLUME_MAX     upper limit of the Roon volume slider (default 80)
    ROON_VOLUME_STEP    step for volume +/- in Roon (default 1)
    ROON_CORE           Roon Core host[:port], empty = auto discovery
    DATA_DIR            persistent data (Roon token, UC config), default /data
    LOG_LEVEL           DEBUG / INFO (default INFO)

:copyright: (c) 2026 by Quirin.
:license: Mozilla Public License Version 2.0, see LICENSE for more details.
"""

import asyncio
import logging
import os
import signal
import sys

DATA_DIR = os.getenv("DATA_DIR", "/data")
MODE = os.getenv("MODE", "roon").strip().lower()
LOG_LEVEL = os.getenv("LOG_LEVEL", os.getenv("UC_LOG_LEVEL", "INFO")).upper()


def run_full() -> None:
    """Complete UC integration driver + Roon."""
    os.environ.setdefault("UC_CONFIG_HOME", DATA_DIR)
    os.environ.setdefault("UC_LOG_LEVEL", LOG_LEVEL)
    os.environ.setdefault("ROON_ENABLED", "1")
    import driver  # noqa: PLC0415  (env must be set before import)

    loop = driver._LOOP
    # PID 1 in Docker: without a handler SIGTERM would be ignored and
    # "docker stop" would wait 10 s before killing the container.
    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(sig, loop.stop)
        except NotImplementedError:
            pass
    loop.run_until_complete(driver.main())
    loop.run_forever()

    async def _shutdown():
        if driver._ROON is not None:
            await driver._ROON.stop()
        for receiver in list(driver._configured_avrs.values()):
            await receiver.disconnect()

    loop.run_until_complete(_shutdown())


async def run_roon_only() -> None:
    """Receiver <-> Roon bridge without the Remote integration."""
    import avr  # noqa: PLC0415
    from config import AvrDevice  # noqa: PLC0415
    from const import __version__  # noqa: PLC0415
    from roon_bridge import RoonManager, RoonSettings  # noqa: PLC0415

    log = logging.getLogger("container")
    host = os.getenv("ONKYO_HOST", "").strip()
    if not host:
        log.error("ONKYO_HOST is not set (IP address of the receiver)")
        sys.exit(2)
    name = os.getenv("ONKYO_NAME", "Onkyo").strip() or "Onkyo"

    settings = RoonSettings.from_env()
    settings.enabled = True
    log.info("Onkyo Roon bridge v%s - receiver %s", __version__, host)

    device = AvrDevice(id=host.replace(".", "_"), name=name, address=host)
    receiver = avr.OnkyoDevice(device, loop=asyncio.get_running_loop())
    manager = RoonManager(settings, os.path.join(DATA_DIR, "roon.json"))
    await receiver.connect()
    await manager.add_receiver(receiver, name)
    manager.start()

    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(sig, stop.set)
        except NotImplementedError:
            pass

    async def poll():
        # same as the driver's poller: keeps state fresh and detects dead links
        while not stop.is_set():
            await asyncio.sleep(30)
            if receiver.connected:
                await receiver.update()

    poller = loop.create_task(poll())
    await stop.wait()
    poller.cancel()
    await manager.stop()
    await receiver.disconnect()


def main() -> None:
    logging.basicConfig(
        level=LOG_LEVEL,
        format="%(asctime)s.%(msecs)03d %(levelname)-8s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    logging.getLogger("websockets").setLevel(logging.WARNING)
    os.makedirs(DATA_DIR, exist_ok=True)
    if MODE == "full":
        run_full()
    elif MODE == "roon":
        asyncio.run(run_roon_only())
    else:
        logging.error("Unknown MODE=%s (use 'roon' or 'full')", MODE)
        sys.exit(2)


if __name__ == "__main__":
    main()
