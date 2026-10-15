#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gallery of the memories (photos and clips of the webcam), served on the local network.

Runs as its own service (see ensure_running) : available even when the game is not.
Each game is a folder of the pictures and of the videos (see ccamera.folder_tree) :
    <date>/<game>  or  <game>/<date>   (directory_order of [Camera])
Pages : all the games, one game ; each memory can be seen, downloaded, printed, deleted,
a game can be downloaded (ZIP) or deleted.

Password : gallery_password of [Camera]. Without one, all is allowed and every page says
so. The QR codes shown by the borne carry a key (see token) : being in front of it is
enough ; typing the address asks for the password.

Usage :
    python3 include/cgallery.py          the server (port PORT)
"""

import configparser
import hashlib
import html
import io
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.parse
import zipfile
from http import cookies
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)
from include import cpaths  # noqa: E402

PORT = 8080
PHOTOS = ('.jpg', '.jpeg', '.png')
VIDEOS = ('.mp4',)
THUMB_SIZE = 360
CACHE_DIR = os.path.join(cpaths.user_dir(), 'gallery_cache')
COOKIE = 'raspydarts_gallery'


# ------------------------------------------------------------------ shared with the game
def secret():
    '''
    Salt of the keys : different on each borne
    '''
    try:
        with open('/etc/machine-id') as file:
            return file.read().strip()
    except OSError:
        return socket.gethostname()


def token(password):
    '''
    Key given by the QR codes of the borne, and kept by the browser once logged in
    '''
    return hashlib.sha256(f"{secret()}:{password}".encode()).hexdigest()[:24]


def partie_id(date, game):
    '''
    Identifier of a game in the addresses (date first, whatever the folder order)
    '''
    return urllib.parse.quote(f"{date}/{game}", safe='')


def address(ip, partie=None, password=''):
    '''
    Address of the gallery (or of one game) for a QR code of the borne
    '''
    path = f"/p/{partie}" if partie else "/"
    key = f"?k={token(password)}" if password else ""
    return f"http://{ip}:{PORT}{path}{key}"


def local_ip():
    '''
    Address of the borne on the local network (no packet is sent)
    '''
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
            probe.connect(('192.0.2.1', 9))
            return probe.getsockname()[0]
    except OSError:
        return f"{socket.gethostname()}.local"


def running():
    try:
        with socket.create_connection(('127.0.0.1', PORT), timeout=0.3):
            return True
    except OSError:
        return False


def ensure_running(logs=None):
    '''
    Started by the game if it does not run. As its own systemd unit : started from the
    service of the game, it would be stopped with it
    '''
    if running():
        return
    script = os.path.abspath(__file__)
    try:
        result = subprocess.run(['systemd-run', '--user', '--unit=raspydarts-gallery', '--collect',
                                 '--quiet', sys.executable, '-u', script], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            return
        if logs is not None:
            logs.warning(f"Gallery : systemd-run refused ({result.stderr.strip()}), started with the game")
    except (OSError, subprocess.TimeoutExpired):
        pass
    try:
        log = open(os.path.join(ROOT_DIR, 'logs', 'gallery.log'), 'a')
        subprocess.Popen([sys.executable, '-u', script], stdout=log, stderr=log, stdin=subprocess.DEVNULL,
                         start_new_session=True)
    except OSError as error:
        if logs is not None:
            logs.error(f"Gallery not started : {error}")


# ------------------------------------------------------------------ the memories
def settings():
    '''
    [Camera] of the configuration, read at each request : changes apply at once
    '''
    config = configparser.ConfigParser(inline_comment_prefixes='#', interpolation=None)
    config.optionxform = str
    path = os.path.join(cpaths.user_dir(), cpaths.CONFIG_NAME)
    if not os.path.isfile(path):
        path = os.path.join(cpaths.user_dir(), cpaths.OLD_CONFIG_NAME)
    config.read(path, encoding='utf-8')
    camera = dict(config['Camera']) if config.has_section('Camera') else {}
    home = cpaths.user_home()
    return {
        'pictures': cpaths.usable_dir(camera.get('picture_path', ''), os.path.join(home, 'Pictures')),
        'videos': cpaths.usable_dir(camera.get('video_path', ''), os.path.join(home, 'Videos')),
        'order': camera.get('directory_order', '0').strip(),
        'password': camera.get('gallery_password', '').strip().strip("'"),
    }


def folders(conf, date, game):
    '''
    Folders of a game : pictures and videos
    '''
    relative = os.path.join(date, game) if conf['order'] != '1' else os.path.join(game, date)
    return [os.path.join(conf['pictures'], relative), os.path.join(conf['videos'], relative)]


def parties(conf):
    '''
    All the games with memories : [(last change, date, game, files)], newest first
    '''
    found = {}
    for root in (conf['pictures'], conf['videos']):
        if not os.path.isdir(root):
            continue
        for first in os.listdir(root):
            path = os.path.join(root, first)
            if not os.path.isdir(path):
                continue
            for second in os.listdir(path):
                if not os.path.isdir(os.path.join(path, second)):
                    continue
                date, game = (first, second) if conf['order'] != '1' else (second, first)
                found.setdefault((date, game), None)
    result = []
    for date, game in found:
        files = memories(conf, date, game)
        if files:
            result.append((max(os.path.getmtime(path) for _name, path in files), date, game, files))
    return sorted(result, reverse=True)


def memories(conf, date, game):
    '''
    Files of a game : [(name, path)], in the order they were taken
    '''
    files = []
    for folder in folders(conf, date, game):
        if os.path.isdir(folder):
            for name in os.listdir(folder):
                if name.lower().endswith(PHOTOS + VIDEOS):
                    files.append((name, os.path.join(folder, name)))
    return sorted(files, key=lambda item: os.path.getmtime(item[1]))


def find(conf, partie, name=None):
    '''
    (date, game, path of name) from an address, None if it is not a memory
    '''
    date, _, game = urllib.parse.unquote(partie).partition('/')
    if not date or not game or '/' in game or '..' in (date, game):
        return None
    if name is None:
        return date, game, None
    for file_name, path in memories(conf, date, game):
        if file_name == name:
            return date, game, path
    return None


def thumbnail(path):
    '''
    Small JPEG of a photo or of the first second of a clip, kept in CACHE_DIR
    '''
    os.makedirs(CACHE_DIR, exist_ok=True)
    key = hashlib.md5(f"{path}:{os.path.getmtime(path)}".encode()).hexdigest()
    cached = os.path.join(CACHE_DIR, f"{key}.jpg")
    if not os.path.exists(cached):
        if path.lower().endswith(VIDEOS):
            subprocess.run(['ffmpeg', '-nostdin', '-loglevel', 'error', '-y', '-ss', '1', '-i', path,
                            '-frames:v', '1', '-vf', f'scale={THUMB_SIZE}:-2', cached], timeout=30)
        else:
            from PIL import Image
            with Image.open(path) as picture:
                picture.thumbnail((THUMB_SIZE, THUMB_SIZE))
                picture.convert('RGB').save(cached, 'JPEG', quality=80)
    return cached


# ------------------------------------------------------------------ pages
STYLE = """
body{margin:0;font-family:sans-serif;background:#141414;color:#eee}
header{padding:12px 16px;background:#202020;display:flex;gap:12px;align-items:center;flex-wrap:wrap}
header a{color:#eee;text-decoration:none;font-weight:bold}
h1{font-size:1.2em;margin:0}
.warning{background:#7a2b1e;padding:8px 16px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(170px,1fr));gap:10px;padding:16px}
.card{background:#202020;border-radius:6px;overflow:hidden}
.card img{width:100%;aspect-ratio:4/3;object-fit:cover;display:block}
.card .name{padding:6px 8px;font-size:.85em;word-break:break-word}
.actions{display:flex;flex-wrap:wrap;gap:6px;padding:0 8px 8px}
.actions a,.actions button,.big a,.big button{background:#333;color:#eee;border:0;border-radius:4px;
 padding:6px 10px;font-size:.85em;text-decoration:none;cursor:pointer}
.actions .delete,.big .delete{background:#7a2b1e}
.big{display:flex;flex-wrap:wrap;gap:8px;padding:0 16px}
.video{position:relative}
.video:after{content:"\\25B6";position:absolute;top:8px;left:10px;font-size:1.4em;text-shadow:0 0 4px #000}
form.login{padding:24px 16px}
input{font-size:1em;padding:8px}
@media print{header,.actions,.warning,.big{display:none}}
"""


def page(title, body, conf, back=True):
    warning = '' if conf['password'] else (
        '<div class="warning">Aucun mot de passe : n\'importe qui sur ce réseau peut supprimer les souvenirs '
        '(réglage dans les paramètres de la webcam de la borne).</div>')
    home = '<a href="/">&larr; Toutes les parties</a>' if back else ''
    return (f'<!doctype html><html lang="fr"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{html.escape(title)}</title><style>{STYLE}</style></head><body>'
            f'<header>{home}<h1>{html.escape(title)}</h1></header>{warning}{body}</body></html>')


def describe(date, game):
    '''
    "High Score - 15/10/2026 10:50" from the folders
    '''
    name, _, stamp = game.rpartition('_')
    if len(stamp) >= 12 and stamp.isdigit():
        return f"{name} - {stamp[6:8]}/{stamp[4:6]}/{stamp[0:4]} {stamp[8:10]}:{stamp[10:12]}"
    return f"{game} - {date.replace('_', '/')}"


class Handler(BaseHTTPRequestHandler):
    server_version = 'RaspyDarts'

    def log_message(self, format, *args):
        pass

    # -- answers
    def send(self, code, content, kind='text/html; charset=utf-8', headers=None):
        data = content.encode('utf-8') if isinstance(content, str) else content
        self.send_response(code)
        self.send_header('Content-Type', kind)
        self.send_header('Content-Length', str(len(data)))
        for header, value in (headers or {}).items():
            self.send_header(header, value)
        self.end_headers()
        if self.command != 'HEAD':
            self.wfile.write(data)

    def redirect(self, location, headers=None):
        self.send_response(303)
        self.send_header('Location', location)
        for header, value in (headers or {}).items():
            self.send_header(header, value)
        self.send_header('Content-Length', '0')
        self.end_headers()

    def send_file(self, path, kind, download_name=None):
        '''
        With byte ranges : video players (Safari above all) ask for parts
        '''
        size = os.path.getsize(path)
        start, end = 0, size - 1
        ranged = self.headers.get('Range', '')
        if ranged.startswith('bytes='):
            first, _, last = ranged[6:].split(',')[0].partition('-')
            if first:
                start = int(first)
                end = int(last) if last else size - 1
            elif last:
                start = max(0, size - int(last))
            end = min(end, size - 1)
            self.send_response(206)
            self.send_header('Content-Range', f'bytes {start}-{end}/{size}')
        else:
            self.send_response(200)
        self.send_header('Content-Type', kind)
        self.send_header('Accept-Ranges', 'bytes')
        self.send_header('Content-Length', str(end - start + 1))
        if download_name:
            quoted = urllib.parse.quote(download_name)
            self.send_header('Content-Disposition', f"attachment; filename*=UTF-8''{quoted}")
        self.end_headers()
        if self.command == 'HEAD':
            return
        with open(path, 'rb') as file:
            file.seek(start)
            remaining = end - start + 1
            while remaining > 0:
                chunk = file.read(min(65536, remaining))
                if not chunk:
                    break
                try:
                    self.wfile.write(chunk)
                except (BrokenPipeError, ConnectionResetError):
                    return
                remaining -= len(chunk)

    # -- access
    def allowed(self, conf, query):
        '''
        True if no password, or the right key (QR code, cookie). A key in the address is
        kept as a cookie, then removed from the address
        '''
        if not conf['password']:
            return True
        good = token(conf['password'])
        if query.get('k', [''])[0] == good:
            self.redirect(self.path.split('?')[0], {'Set-Cookie': f'{COOKIE}={good}; Path=/; Max-Age=31536000'})
            return None
        jar = cookies.SimpleCookie(self.headers.get('Cookie', ''))
        return COOKIE in jar and jar[COOKIE].value == good

    def login_page(self, conf, wrong=False):
        message = '<p>Mot de passe incorrect.</p>' if wrong else ''
        body = (f'<form class="login" method="post" action="/login?next={urllib.parse.quote(self.path)}">'
                f'{message}<p>Mot de passe de la galerie :</p>'
                f'<input type="password" name="password" autofocus> <button>Entrer</button></form>')
        self.send(200, page('Galerie RaspyDarts', body, conf, back=False))

    # -- routes
    def do_HEAD(self):
        self.do_GET()

    def do_GET(self):
        conf = settings()
        url = urllib.parse.urlsplit(self.path)
        query = urllib.parse.parse_qs(url.query)
        access = self.allowed(conf, query)
        if access is None:
            return
        if not access:
            return self.login_page(conf)
        parts = [urllib.parse.unquote(part) for part in url.path.strip('/').split('/') if part]
        try:
            if not parts:
                return self.home(conf)
            if parts[0] == 'p' and len(parts) == 2:
                return self.partie(conf, parts[1])
            if parts[0] in ('f', 't', 'd', 'print') and len(parts) == 3:
                found = find(conf, urllib.parse.quote(parts[1], safe=''), parts[2])
                if found is None:
                    return self.send(404, page('Introuvable', '<p class="big">Ce souvenir n\'existe plus.</p>', conf))
                path = found[2]
                kind = 'video/mp4' if path.lower().endswith(VIDEOS) else (
                    'image/png' if path.lower().endswith('.png') else 'image/jpeg')
                if parts[0] == 'f':
                    return self.send_file(path, kind)
                if parts[0] == 'd':
                    return self.send_file(path, kind, download_name=parts[2])
                if parts[0] == 't':
                    return self.send_file(thumbnail(path), 'image/jpeg')
                source = f"/f/{urllib.parse.quote(parts[1], safe='')}/{urllib.parse.quote(parts[2])}"
                return self.send(200, f'<!doctype html><html><body style="margin:0" onload="window.print()">'
                                      f'<img src="{source}" style="width:100%"></body></html>')
            if parts[0] == 'zip' and len(parts) == 2:
                return self.zip(conf, parts[1])
        except (OSError, ValueError, subprocess.SubprocessError) as error:
            return self.send(500, page('Erreur', f'<p class="big">{html.escape(str(error))}</p>', conf))
        self.send(404, page('Introuvable', '', conf))

    def do_POST(self):
        conf = settings()
        url = urllib.parse.urlsplit(self.path)
        query = urllib.parse.parse_qs(url.query)
        length = int(self.headers.get('Content-Length', '0') or 0)
        form = urllib.parse.parse_qs(self.rfile.read(length).decode('utf-8', 'replace')) if length else {}
        if url.path == '/login':
            target = query.get('next', ['/'])[0]
            if not target.startswith('/'):
                target = '/'
            if conf['password'] and form.get('password', [''])[0] == conf['password']:
                return self.redirect(target, {'Set-Cookie': f'{COOKIE}={token(conf["password"])}; Path=/; Max-Age=31536000'})
            return self.login_page(conf, wrong=True)
        if not self.allowed(conf, {}):
            return self.login_page(conf)
        parts = [urllib.parse.unquote(part) for part in url.path.strip('/').split('/') if part]
        if parts and parts[0] == 'delete' and len(parts) in (2, 3):
            partie = urllib.parse.quote(parts[1], safe='')
            if len(parts) == 3:
                found = find(conf, partie, parts[2])
                if found is not None:
                    os.remove(found[2])
                return self.redirect(f"/p/{partie}")
            found = find(conf, partie)
            if found is not None:
                for folder in folders(conf, found[0], found[1]):
                    shutil.rmtree(folder, ignore_errors=True)
                    # The date folder (or game folder) left empty goes too
                    parent = os.path.dirname(folder)
                    if os.path.isdir(parent) and not os.listdir(parent):
                        os.rmdir(parent)
            return self.redirect('/')
        self.send(404, page('Introuvable', '', conf))

    def home(self, conf):
        cards = []
        for _changed, date, game, files in parties(conf):
            ident = partie_id(date, game)
            first = files[0][0]
            photos = sum(1 for name, _p in files if name.lower().endswith(PHOTOS))
            count = f"{photos} photo(s), {len(files) - photos} vidéo(s)"
            cards.append(f'<div class="card"><a href="/p/{ident}"><img loading="lazy" src="/t/{ident}/{urllib.parse.quote(first)}"></a>'
                         f'<div class="name"><b>{html.escape(describe(date, game))}</b><br>{count}</div></div>')
        body = f'<div class="grid">{"".join(cards)}</div>' if cards else '<p class="big">Aucun souvenir pour le moment.</p>'
        self.send(200, page('Galerie RaspyDarts', body, conf, back=False))

    def partie(self, conf, raw):
        ident = urllib.parse.quote(raw, safe='')
        found = find(conf, ident)
        if found is None:
            return self.send(404, page('Introuvable', '', conf))
        date, game, _ = found
        files = memories(conf, date, game)
        cards = []
        for name, path in files:
            quoted = urllib.parse.quote(name)
            video = name.lower().endswith(VIDEOS)
            if video:
                view = f'<video controls preload="none" poster="/t/{ident}/{quoted}" src="/f/{ident}/{quoted}" style="width:100%"></video>'
                printing = ''
            else:
                view = f'<a href="/f/{ident}/{quoted}"><img loading="lazy" src="/t/{ident}/{quoted}"></a>'
                printing = f'<a href="/print/{ident}/{quoted}" target="_blank">Imprimer</a>'
            cards.append(f'<div class="card{" video" if video else ""}">{view}'
                         f'<div class="name">{html.escape(os.path.splitext(name)[0])}</div><div class="actions">'
                         f'<a href="/d/{ident}/{quoted}">Télécharger</a>{printing}'
                         f'<form method="post" action="/delete/{ident}/{quoted}" onsubmit="return confirm(\'Supprimer ce souvenir ?\')">'
                         f'<button class="delete">Supprimer</button></form></div></div>')
        actions = (f'<div class="big"><a href="/zip/{ident}">Tout télécharger (ZIP)</a>'
                   f'<form method="post" action="/delete/{ident}" onsubmit="return confirm(\'Supprimer tous les souvenirs de cette partie ?\')">'
                   f'<button class="delete">Supprimer la partie</button></form></div>')
        body = actions + (f'<div class="grid">{"".join(cards)}</div>' if cards else '<p class="big">Aucun souvenir.</p>')
        self.send(200, page(describe(date, game), body, conf))

    def zip(self, conf, raw):
        found = find(conf, urllib.parse.quote(raw, safe=''))
        if found is None:
            return self.send(404, page('Introuvable', '', conf))
        date, game, _ = found
        with tempfile.TemporaryFile(dir='/tmp' if os.path.isdir('/tmp') else None) as archive:
            # Stored, not compressed : photos and videos are already
            with zipfile.ZipFile(archive, 'w', zipfile.ZIP_STORED) as content:
                for name, path in memories(conf, date, game):
                    content.write(path, name)
            size = archive.tell()
            archive.seek(0)
            self.send_response(200)
            self.send_header('Content-Type', 'application/zip')
            self.send_header('Content-Length', str(size))
            name = urllib.parse.quote(f"{game}.zip")
            self.send_header('Content-Disposition', f"attachment; filename*=UTF-8''{name}")
            self.end_headers()
            shutil.copyfileobj(archive, self.wfile)


def main():
    server = ThreadingHTTPServer(('0.0.0.0', PORT), Handler)
    server.daemon_threads = True
    print(f"Gallery on port {PORT}", flush=True)
    server.serve_forever()


if __name__ == '__main__':
    main()
