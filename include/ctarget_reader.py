#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Target reader : the only process which touches the GPIO of the target matrix.

A dart closes its contact for 1.1 to 3.7 ms only. Scanning the matrix in the loop of
the game read each segment every 3 ms at best (95 rpi-lgpio calls per pass under
Trixie) : short contacts were missed. Here :

    rest     the 7 columns are high, the 10 lines are inputs : the process sleeps
             until the kernel signals a rising edge on a line (no CPU used)
    wake up  the edge tells which line (0.3 ms after the impact on a Pi 3). The
             column is searched by halves of the columns, then confirmed alone, and
             searched again while the contact stays closed : contacts bounce
    release  the dart is sent once its contact is open for RELEASE seconds, then
             the columns are high again

Lines are always inputs and columns always outputs : two outputs are never linked
through a closed contact. Edges are waited with gpiod (the event gives the line),
columns are driven with lgpio, in one call for all of them : gpiod takes 1 ms to
change the direction of lines on a Pi 3, lgpio 6 us to write them.

Each dart is written on stdout, one line : "<segment> <code>", for example "T20 2610",
or "? <code>" when the code is not declared in [SectionKeys] (wiring assistant).

Usage :
    python3 include/ctarget_reader.py           for the game
    python3 include/ctarget_reader.py --test    shows each dart with its timings
"""

import argparse
import configparser
import os
import signal
import sys
import time

import gpiod
import lgpio
from gpiod.line import Bias, Direction, Edge, Value

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)
from include import cpaths  # noqa: E402

CHIP = '/dev/gpiochip0'
CHIP_NUMBER = 0
# The contact is open since this time : the dart is over (bounces included)
RELEASE = 0.020
# A contact closed longer than this is a dart stuck on the target : sent anyway
HOLD_MAX = 0.400


def read_wiring(config_path):
    '''
    Lines, columns and segments from the configuration of the game (read only)
    '''
    config = configparser.ConfigParser(inline_comment_prefixes='#')
    config.optionxform = str
    config.read(config_path)

    def pins(section):
        if not config.has_section(section):
            return []
        return [int(value) for value in config[section].values() if value.strip().isdigit()]

    lines = pins('Raspberry_BoardPinsIns')
    columns = pins('Raspberry_BoardPinsOuts')
    segments = {}
    if config.has_section('SectionKeys'):
        for segment, code in config['SectionKeys'].items():
            if code.strip():
                segments[code.strip()] = segment
    return lines, columns, segments


class TargetReader:
    '''
    Matrix read on edges : see the description of the module
    '''
    def __init__(self, lines, columns, segments):
        self.lines = lines
        self.columns = columns
        self.segments = segments
        self.all_high = (1 << len(columns)) - 1

        self.request = gpiod.request_lines(CHIP, consumer='raspydarts-target', config={
            tuple(lines): gpiod.LineSettings(direction=Direction.INPUT, bias=Bias.PULL_DOWN,
                                             edge_detection=Edge.RISING)})
        self.handle = lgpio.gpiochip_open(CHIP_NUMBER)
        lgpio.group_claim_output(self.handle, columns, [1] * len(columns))

    def close(self):
        lgpio.group_write(self.handle, self.columns[0], 0, self.all_high)
        lgpio.group_free(self.handle, self.columns[0])
        lgpio.gpiochip_close(self.handle)
        self.request.release()

    def lit_by(self, line, bits):
        '''
        Is the line high when only the columns of bits are high ?
        '''
        lgpio.group_write(self.handle, self.columns[0], bits, self.all_high)
        return self.request.get_value(line) == Value.ACTIVE

    def column_of(self, line):
        '''
        Column whose contact with the line is closed, None if it is open or bounced
        meanwhile. Found by halves (3 steps for 7 columns instead of 7 : each step costs
        about 75 us on a Pi 3), then confirmed alone : a bounce during the search gives
        a wrong half, the confirmation rejects it.
        '''
        candidates = list(range(len(self.columns)))
        while len(candidates) > 1:
            half = candidates[:len(candidates) // 2]
            if self.lit_by(line, sum(1 << index for index in half)):
                candidates = half
            else:
                candidates = candidates[len(half):]
        found = self.columns[candidates[0]] if self.lit_by(line, 1 << candidates[0]) else None
        lgpio.group_write(self.handle, self.columns[0], self.all_high, self.all_high)
        return found

    def line_closed(self, line):
        return self.request.get_value(line) == Value.ACTIVE

    def flush_edges(self):
        while self.request.wait_edge_events(0):
            self.request.read_edge_events()

    def next_dart(self, timeout=None):
        '''
        Wait for a dart. Returns (code, segment, timings) or None after timeout.
        timings : wake up after the edge, column search, contact, edges seen, searches
        (us, us, ms, n, n)
        '''
        while True:
            if not self.request.wait_edge_events(timeout):
                return None
            events = self.request.read_edge_events()
            woken = time.monotonic_ns()
            edge = events[0]
            line = edge.line_offset
            wake_us = (woken - edge.timestamp_ns) / 1000

            start = time.monotonic_ns()
            column = self.column_of(line)
            searches = 1
            found = time.monotonic_ns()

            # Until the contact is open for RELEASE seconds. While the column is not found,
            # it is searched again each time the line is seen closed : contacts bounce,
            # a search made during a bounce finds nothing
            edges = len(events)
            opened = None
            while (time.monotonic_ns() - edge.timestamp_ns) / 1e9 < HOLD_MAX:
                if self.line_closed(line):
                    opened = None
                    if column is None:
                        column = self.column_of(line)
                        searches += 1
                        found = time.monotonic_ns()
                        continue
                elif opened is None:
                    opened = time.monotonic_ns()
                elif (time.monotonic_ns() - opened) / 1e9 >= RELEASE:
                    break
                time.sleep(0.0005)
            search_us = (found - start) / 1000
            if self.request.wait_edge_events(0):
                edges += len(self.request.read_edge_events())
            self.flush_edges()
            contact_ms = ((opened or time.monotonic_ns()) - edge.timestamp_ns) / 1e6

            if column is None:
                # Contact already open : the dart is lost. Told in test mode only
                return (None, None, (wake_us, search_us, contact_ms, edges, searches))
            code = f'{line}{column}'
            return (code, self.segments.get(code), (wake_us, search_us, contact_ms, edges, searches))


def main():
    parser = argparse.ArgumentParser(description='RaspyDarts target reader')
    parser.add_argument('--test', action='store_true', help='show each dart with its timings')
    parser.add_argument('--duration', type=int, default=0, help='test : stop after N seconds')
    parser.add_argument('--config', default=None)
    args = parser.parse_args()

    config_path = args.config
    if config_path is None:
        config_path = os.path.join(cpaths.user_dir(), cpaths.CONFIG_NAME)
        if not os.path.isfile(config_path):
            config_path = os.path.join(cpaths.user_dir(), cpaths.OLD_CONFIG_NAME)
    lines, columns, segments = read_wiring(config_path)
    if not lines or not columns:
        print(f"No target matrix in {config_path}", file=sys.stderr)
        return 1

    reader = TargetReader(lines, columns, segments)
    stop = []
    signal.signal(signal.SIGTERM, lambda *_: stop.append(True))
    signal.signal(signal.SIGINT, lambda *_: stop.append(True))
    end = time.monotonic() + args.duration if args.duration else None

    if args.test:
        print(f"{len(lines)} lignes x {len(columns)} colonnes, {len(segments)} codes declares")
        print("En attente de flechettes...\n", flush=True)
    darts = []
    lost = 0
    try:
        number = 0
        previous = None
        while not stop and (end is None or time.monotonic() < end):
            dart = reader.next_dart(timeout=0.5)
            if dart is None:
                continue
            code, segment, (wake_us, search_us, contact_ms, edges, searches) = dart
            if args.test:
                number += 1
                now = time.monotonic()
                since = f"{now - previous:5.1f}s" if previous is not None else "     -"
                previous = now
                timings = f"+{since}  reveil {wake_us:3.0f}us  recherche {search_us:4.0f}us x{searches}  contact {contact_ms:4.1f}ms"
                if code is None:
                    # Contact open again before its column was found : a dart lost, or
                    # a parasite (a dart which vibrates, a segment brushed). Not sent
                    lost += 1
                    print(f"{number:3}  sans colonne {timings}", flush=True)
                else:
                    darts.append((wake_us, search_us, contact_ms))
                    print(f"{number:3}  {segment or '?':<4} {code:<7} {timings}", flush=True)
            elif code is not None:
                print(f"{segment or '?'} {code}", flush=True)
    finally:
        reader.close()

    if args.test:
        print(f"\n{len(darts)} flechette(s) lue(s), {lost} contact(s) sans colonne")
        if darts:
            wakes = sorted(d[0] for d in darts)
            searches = sorted(d[1] for d in darts)
            contacts = sorted(d[2] for d in darts)
            print(f"  reveil    mediane {wakes[len(wakes) // 2]:6.0f} us   max {wakes[-1]:6.0f} us")
            print(f"  recherche mediane {searches[len(searches) // 2]:6.0f} us   max {searches[-1]:6.0f} us")
            print(f"  contact   min {contacts[0]:5.1f} ms   mediane {contacts[len(contacts) // 2]:5.1f} ms   max {contacts[-1]:5.1f} ms")
    return 0


if __name__ == '__main__':
    sys.exit(main())
