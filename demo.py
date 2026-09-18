#!/usr/bin/env python3
"""Small demonstration script to try the library against a real dongle.

Read-only by default: it identifies the dongle and prints its channel table without
transmitting anything. Movement commands are opt-in and ask for confirmation first, since
they physically move a shutter.

Usage:
    uv run demo.py                          # identify and list channels
    uv run demo.py --port /dev/ttyACM0      # force the serial port
    uv run demo.py --channel 2 --close      # close, asks for confirmation
    uv run demo.py --channel 2 --stop --yes # stop, without confirmation

"""

from __future__ import annotations

import argparse
import sys

from pyneosol import Dongle, NeosolError, find_ports

ACTIONS = ("open", "close", "stop", "favourite")


def parse_args() -> argparse.Namespace:
    """Build the command line."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--port", help="serial port; auto-detected when omitted")
    parser.add_argument("--channel", type=int, help="channel to act on")
    for action in ACTIONS:
        parser.add_argument(f"--{action}", action="store_true", help=f"send {action}")
    parser.add_argument("--yes", action="store_true", help="skip the confirmation prompt")
    return parser.parse_args()


def show_ports() -> None:
    """List the serial ports whose USB identifiers match a dongle."""
    ports = find_ports()
    if not ports:
        print("No matching USB device found. Pass --port to try a specific one.")
        return
    for port in ports:
        print(f"  {port.device}  {port.manufacturer or '?'} / {port.product or '?'}")


def show_dongle(dongle: Dongle) -> None:
    """Print identification and channel table."""
    info = dongle.info()
    print("\nDongle")
    print(f"  hardware version : {info.hardware_version}")
    print(f"  software version : {info.software_version}")
    print(f"  frame repeat     : {info.frame_repeat}")
    print(f"  read protection  : {'yes' if info.read_protection else 'no'}")
    print(f"  transmit power   : {dongle.transmit_power()}")

    channels = dongle.channels()
    used = [channel for channel in channels if channel.is_used]
    print(f"\nChannels: {len(channels)} total, {len(used)} used")
    # Keys are deliberately not printed: they are the secret that commands the shutters.
    for channel in used:
        print(f"  channel {channel.index:>2}  serial {channel.serial}  sync {channel.sync}")
    if not used:
        print("  none paired yet")


def confirm(action: str, channel: int) -> bool:
    """Ask before moving a real shutter."""
    answer = input(f"\nSend {action.upper()} on channel {channel}? This moves a shutter. [y/N] ")
    return answer.strip().lower() in {"y", "yes", "o", "oui"}


def main() -> int:
    """Run the demonstration."""
    args = parse_args()
    requested = [action for action in ACTIONS if getattr(args, action)]

    if len(requested) > 1:
        print(f"Pick a single action, got: {', '.join(requested)}", file=sys.stderr)
        return 2
    if requested and args.channel is None:
        print("--channel is required to send an action", file=sys.stderr)
        return 2

    print("Looking for a dongle...")
    show_ports()

    try:
        with Dongle.open(args.port) as dongle:
            show_dongle(dongle)

            if not requested:
                print("\nRead-only run: nothing was transmitted.")
                return 0

            action = requested[0]
            if not args.yes and not confirm(action, args.channel):
                print("Cancelled.")
                return 0

            before = dongle.channel(args.channel).sync
            getattr(dongle, {"open": "open_shutter", "close": "close_shutter"}.get(action, action))(
                args.channel
            )
            after = dongle.channel(args.channel).sync
            # The counter proves a frame left the dongle. It says nothing about the motor:
            # the link is one-way, so there is no way to know whether the shutter moved.
            print(f"\n{action.upper()} sent on channel {args.channel}")
            print(f"  sync counter: {before} -> {after}")
            return 0

    except NeosolError as error:
        print(f"\nError: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
