"""
Output of the sound (Personnalisation du jeu > Général > Sortie du son) : HDMI, the jack of the
Raspberry, a USB sound card, or automatic (a USB card when one is plugged, else HDMI). A screen
VGA, plugged by an adapter HDMI-VGA, has no sound : a USB card gives it one.

The default output of PipeWire is set : the game (pygame), VLC and omxplayer (-o alsa) play on
it. The intro video, played before PipeWire starts, reads the same setting (scripts/Intro.sh).
The outputs are told apart by their card : « bcm2835 HDMI 1 », « bcm2835 Headphones », a card
on the USB bus (their names of PipeWire, mailbox.stereo-fallback..., do not say it).
"""

import json
import os
import subprocess
import threading
import time

OUTPUTS = ('auto', 'hdmi', 'jack', 'usb')
# The wanted output, then the others if it is missing (a USB card unplugged : HDMI)
ORDER = {'auto': ('usb', 'hdmi', 'jack'), 'hdmi': ('hdmi', 'usb', 'jack'),
         'jack': ('jack', 'hdmi', 'usb'), 'usb': ('usb', 'hdmi', 'jack')}
# USB cards already put at full volume once (one plugged is often very low) ; then the volume of
# the system is the user's (Volume général of the USB pads, desktop). HDMI and the jack keep
# theirs (HDMI : set once by raspydarts-audio of the installation)
SET_ONCE = os.path.expanduser('~/.config/raspydarts-audio-outputs')
# PipeWire is started with the session : it can come after the game
WAIT = 20


def kind(sink):
    """
    'hdmi', 'jack' or 'usb' : the output of this sink of PipeWire, None if unknown
    """
    properties = sink.get('properties') or {}
    card = str(properties.get('alsa.card_name') or properties.get('api.alsa.card.name') or '').lower()
    if str(properties.get('device.bus', '')).lower() == 'usb' or 'usb' in card:
        return 'usb'
    if 'hdmi' in card:
        return 'hdmi'
    if 'headphones' in card or 'analog' in card:
        return 'jack'
    return None


def sinks():
    """
    The outputs of PipeWire : [(kind, name)]
    """
    try:
        text = subprocess.run(['pactl', '-f', 'json', 'list', 'sinks'], capture_output=True, text=True,
                              timeout=10, check=True).stdout
        return [(kind(sink), sink.get('name')) for sink in json.loads(text) if kind(sink)]
    except (OSError, ValueError, subprocess.SubprocessError):
        return []


def choose(setting, found):
    """
    The sink to use for this setting, None if none
    """
    for wanted in ORDER.get(setting, ORDER['auto']):
        for found_kind, name in found:
            if found_kind == wanted:
                return found_kind, name
    return None


def apply(setting, logs):
    """
    The sound sent to the output of this setting (in a thread : PipeWire may not be ready)
    """
    threading.Thread(target=set_output, args=(setting, logs), daemon=True).start()


def set_output(setting, logs):
    """
    See apply
    """
    setting = setting if setting in OUTPUTS else 'auto'
    deadline = time.monotonic() + WAIT
    while True:
        chosen = choose(setting, sinks())
        if chosen is not None:
            break
        if time.monotonic() > deadline:
            logs.warning(f"Sound : no output found for '{setting}'")
            return
        time.sleep(1)
    found_kind, name = chosen
    run = lambda *command: subprocess.run(['pactl', *command], capture_output=True, timeout=10, check=False)
    run('set-default-sink', name)
    run('set-sink-mute', name, '0')
    try:
        with open(SET_ONCE, encoding='utf-8') as file:
            done = file.read().split()
    except OSError:
        done = []
    if found_kind == 'usb' and name not in done:
        run('set-sink-volume', name, '100%')
        try:
            os.makedirs(os.path.dirname(SET_ONCE), exist_ok=True)
            with open(SET_ONCE, 'a', encoding='utf-8') as file:
                file.write(f"{name}\n")
        except OSError:
            pass
    if setting not in ('auto', found_kind):
        logs.warning(f"Sound : no '{setting}' output, sent to {found_kind} ({name})")
    else:
        logs.info(f"Sound : {found_kind} ({name})")
