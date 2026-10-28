"""Client du salon ChtiDarts (Python 3.7+, websocket-client)."""
import json
import os
import queue
import ssl
import threading
import time
from collections import deque
from pathlib import Path

URL = 'wss://video.chtiraspycard.fr/borne-lobby'
# CHTI BORNE COMPTES V1


class ChatClient:
    def __init__(self, name, token, visible=True):
        self.name, self.token = name, token
        self.visible = visible
        self.auth_failed = False
        self.match_live = None  # CHTI SPECTATEUR V1
        self.game_activity = {'playing': False}
        self.activity_version = 0
        self.commands = queue.Queue(maxsize=30)
        self.lock = threading.Lock()
        self.stopped = threading.Event()
        self.ws = None
        self.ident = None
        self.players = []
        self.events = deque(maxlen=150)
        self.status = 'CONNEXION...'
        self.thread = threading.Thread(target=self.run, daemon=True)

    def set_activity(self, data):
        with self.lock:
            if not data.get('playing'):
                self.match_live = None
            self.game_activity = dict(data)
            self.activity_version += 1

    def start(self):
        self.thread.start()

    def snapshot(self):
        with self.lock:
            return self.status, self.ident, list(self.players), list(self.events)

    def command(self, data):
        with self.lock:
            if self.status != 'CONNECTE':
                return False
        try:
            self.commands.put_nowait(data)
            return True
        except queue.Full:
            return False

    def stop(self):
        self.stopped.set()
        if self.ws:
            try:
                self.ws.close(timeout=1)
            except Exception:
                pass

    def run(self):
        import websocket
        while not self.stopped.is_set():
            connection = None
            try:
                connection = websocket.create_connection(
                    URL, timeout=4,
                    header=['Authorization: Bearer ' + self.token],
                    sslopt={'cert_reqs': ssl.CERT_REQUIRED})
                self.ws = connection
                if self.stopped.is_set():
                    break
                if self.visible:
                    connection.send(json.dumps({'type': 'hello', 'name': self.name}))
                activity_sent = -1
                next_activity = 0
                next_live = 0
                last_live = None
                last_live_at = 0
                connection.settimeout(0.2)
                while not self.stopped.is_set():
                    with self.lock:
                        version = self.activity_version
                        data = dict(self.game_activity)
                    if version != activity_sent or time.monotonic() >= next_activity:
                        data.update(type='activity', visible=self.visible)
                        connection.send(json.dumps(data))
                        activity_sent = version
                        next_activity = time.monotonic() + 15
                    with self.lock:
                        live = self.match_live if self.game_activity.get('playing') else None
                    now = time.monotonic()
                    if live is not None and now >= next_live and (live != last_live or now-last_live_at >= 5):
                        payload = json.dumps(live, ensure_ascii=False)
                        if len(payload.encode('utf-8')) <= 3900:
                            connection.send(payload)
                        next_live = now + 0.6
                        last_live_at = now
                        last_live = live
                    try:
                        command = self.commands.get_nowait()
                    except queue.Empty:
                        command = None
                    if command is not None:
                        connection.send(json.dumps(command))
                    try:
                        raw = connection.recv()
                    except websocket.WebSocketTimeoutException:
                        continue
                    if not raw:
                        raise ConnectionError('Deconnexion')
                    event = json.loads(raw)
                    if not isinstance(event, dict):
                        continue
                    with self.lock:
                        kind = event.get('type')
                        if kind == 'welcome':
                            self.ident = event.get('id')
                            account = event.get('account')
                            if isinstance(account, dict):
                                self.name = '{:03d} · {} (borne)'.format(account['id'], account['username'])
                        elif kind == 'presence':
                            incoming = event.get('players', [])
                            incoming = [p for p in incoming if isinstance(p, dict) and p.get('id')]
                            previous = {p['id'] for p in self.players}
                            # La premiere liste sert de reference ; pas de son pour soi-meme.
                            if self.status == 'CONNECTE':
                                for player in incoming:
                                    if player['id'] != self.ident and player['id'] not in previous:
                                        self.events.append({'type': 'joined', 'from': player['id'],
                                                            'name': player.get('name', '?'),
                                                            '_received': time.monotonic()})
                            self.players = incoming
                            self.status = 'CONNECTE'
                        else:
                            event['_received'] = time.monotonic()
                            self.events.append(event)
            except Exception as error:
                denied = getattr(error, 'status_code', None) in (401, 403)
                if denied:
                    self.auth_failed = True
                    self.stopped.set()
                    try:
                        from include.chti_chat_account import forget_session
                        forget_session()
                    except OSError:
                        pass
                with self.lock:
                    self.status = ('CONNEXION AU COMPTE REQUISE' if denied else 'HORS LIGNE - nouvelle tentative...')
                    self.players = []
                    self.ident = None
                    self.events.clear()
                while True:
                    try:
                        self.commands.get_nowait()
                    except queue.Empty:
                        break
            finally:
                if connection:
                    try:
                        connection.close(timeout=1)
                    except Exception:
                        pass
                self.ws = None
            self.stopped.wait(3)


# CHTI CHAT V2 : saisie et notifications
class MessageEditor:
    def __init__(self):
        self.text = ''
        self.cursor = 0

    def edit(self, key, left=(), right=()):
        if key in left:
            self.cursor = max(0, self.cursor - 1)
        elif key in right:
            self.cursor = min(len(self.text), self.cursor + 1)
        elif key == 'home':
            self.cursor = 0
        elif key == 'end':
            self.cursor = len(self.text)
        elif key == 'backspace' and self.cursor:
            self.text = self.text[:self.cursor-1] + self.text[self.cursor:]
            self.cursor -= 1
        elif key == 'delete':
            self.text = self.text[:self.cursor] + self.text[self.cursor+1:]
        else:
            value = ' ' if key == 'space' else key
            if isinstance(value, str) and len(value) == 1 and value.isprintable() and len(self.text) < 160:
                self.text = self.text[:self.cursor] + value + self.text[self.cursor:]
                self.cursor += 1


def _notify(display, invitation=False, connexion=False):
    name = ('chat_connexion' if connexion else
            'chat_invitation' if invitation else 'chat_message')
    try:
        # Meme lecture et meme volume que les autres sons de RaspyDarts.
        channel = display.play_sound('/pydarts/sounds/' + name + '.wav')
        if channel is None:
            print('[CHTI CHAT AUDIO] Lecture non confirmee : ' + name, flush=True)
    except Exception as error:
        print('[CHTI CHAT AUDIO] ' + name + ' : ' + str(error), flush=True)


def _new_events(display, client, seen):
    events = client.snapshot()[3]
    fresh = []
    for event in events:
        signature = (event.get('_received'), event.get('type'), event.get('invitation'),
                     event.get('from'), bool(event.get('outgoing')), event.get('text'))
        if signature in seen:
            continue
        seen.add(signature)
        fresh.append(event)
        if not event.get('outgoing'):
            if event.get('type') == 'joined':
                _notify(display, connexion=True)
            elif event.get('type') in ('chat', 'invite'):
                _notify(display, invitation=event.get('type') == 'invite')
    if len(seen) > 600:
        seen.intersection_update({(e.get('_received'), e.get('type'), e.get('invitation'),
                                  e.get('from'), bool(e.get('outgoing')), e.get('text')) for e in events})
    return fresh


def process_message_events(editor, events):
    import pygame
    for event in events:
        if event.type == pygame.QUIT:
            return 'cancel'
        if event.type != pygame.KEYDOWN:
            continue
        key = pygame.key.name(event.key).lower()
        if key == 'escape':
            return 'cancel'
        if key in ('return', 'enter', 'keypad enter', '[enter]'):
            if editor.text.strip():
                return 'send'
            continue
        if key in ('left', 'right', 'home', 'end', 'backspace', 'delete'):
            editor.edit(key, ('left',), ('right',))
        else:
            # Unicode garde les accents et la ponctuation du clavier AZERTY.
            value = getattr(event, 'unicode', '')
            for character in value:
                editor.edit(character)
    return None


def compose_message(display, keys, client, seen, recipient):
    import pygame
    _, _, left, right, enter, escape = keys
    editor = MessageEditor()
    backdrop = display.screen.copy()
    clock = pygame.time.Clock()
    while True:
        _new_events(display, client, seen)
        display.screen.blit(backdrop, (0, 0))
        w, h = display.screen.get_size()
        box = pygame.Rect(int(w*.035), int(h*.72), int(w*.93), int(h*.25))
        pygame.draw.rect(display.screen, (18, 31, 48), box, border_radius=8)
        pygame.draw.rect(display.screen, (245, 189, 55), box, 2, border_radius=8)
        font = pygame.font.Font(None, max(18, int(h*.034)))
        def line(value, y, color):
            display.screen.blit(font.render(value, True, color), (box.x+12, int(y)))
        line('MESSAGE POUR ' + str(recipient)[:24], box.y+h*.018, (245,189,55))
        before = editor.text[:editor.cursor]
        while before and font.size(before)[0] > box.width - 42:
            before = before[1:]
        after = editor.text[editor.cursor:]
        while after and font.size(before+after)[0] > box.width - 36:
            after = after[:-1]
        y = box.y+h*.08
        line(before+after, y, (238,240,245))
        if int(time.monotonic()*2) % 2 == 0:
            x = box.x+12+font.size(before)[0]
            pygame.draw.line(display.screen, (245,189,55), (x,int(y)), (x,int(y+h*.035)), 2)
        line('Espace : espace | Entree : envoyer | Echap : annuler | {}/160'.format(len(editor.text)),
             box.y+h*.17, (162,176,194))
        display.update_screen()
        # Chaque frappe du lot est traitee : aucune sortie apres la premiere lettre.
        action = process_message_events(editor, pygame.event.get())
        if action == 'cancel':
            return None
        if action == 'send' and editor.text.strip():
            return editor.text.strip()
        clock.tick(60)


def ensure_session(display, prompt=False):
    """Connexion uniquement avec un compte enregistré ; aucun accès invité."""
    if getattr(display, '_chti_auth_open', False):
        return None
    current = getattr(display, '_chti_chat_client', None)
    ready = bool(getattr(display, '_chti_ready_online', False))
    if current is not None and current.auth_failed:
        display._chti_account_session = None
        display._chti_chat_status = 'CONNEXION AU COMPTE REQUISE'
    if current is not None and not current.stopped.is_set():
        if current.visible == ready:
            return current
        current.stop()
    display._chti_chat_client = None
    now = time.monotonic()
    if not prompt and now < getattr(display, '_chti_chat_retry', 0):
        return None
    display._chti_chat_retry = now + 3
    try:
        import websocket
        from include.chti_chat_account import load_session, login_dialog
        session = getattr(display, '_chti_account_session', None)
        if session is None:
            session = load_session()
        if session and session.get('expires', 0) <= time.time():
            session = None
        if session is None and prompt:
            display._chti_auth_open = True
            try:
                session = login_dialog(display)
            finally:
                display._chti_auth_open = False
        if not session:
            display._chti_chat_status = 'CONNEXION AU COMPTE REQUISE'
            return None
        display._chti_account_session = session
        account = session['user']
        name = '{:03d} · {} (borne)'.format(account['id'], account['username'])
        current = ChatClient(name, session['token'], visible=ready)
        display._chti_chat_client = current
        display._chti_chat_seen = set()
        display._chti_chat_resolved = set()
        display._chti_chat_unread = 0
        current.set_activity(getattr(display, '_chti_game_activity', {'playing': False}))
        current.start()
        import atexit
        atexit.register(current.stop)
        return current
    except Exception:
        display._chti_chat_status = 'CHAT INDISPONIBLE'
        if prompt:
            display.message(['Chat indisponible : vérifier Internet et python3-websocket.'])
        # Aucun mot de passe ni jeton dans les logs.
        print('[CHTI PRESENCE] Connexion au compte indisponible', flush=True)
        return None


def toggle_ready(display):
    previous = bool(getattr(display, '_chti_ready_online', False))
    display._chti_ready_online = not previous
    display._chti_chat_retry = 0
    current = getattr(display, '_chti_chat_client', None)
    if current is not None:
        current.stop()
        display._chti_chat_client = None
    client = ensure_session(display, prompt=not previous)
    if client is None:
        display._chti_ready_online = previous
        display._chti_chat_retry = 0
        ensure_session(display)
    return bool(getattr(display, '_chti_ready_online', False))


def pump_presence(display):
    """Notifications sur le thread d'affichage, jamais dans le thread reseau."""
    if getattr(display, '_chti_chat_open', False):
        return
    now = time.monotonic()
    if now < getattr(display, '_chti_chat_next_pump', 0):
        return
    display._chti_chat_next_pump = now + .1
    client = getattr(display, '_chti_chat_client', None)
    if client is None:
        return
    for event in _new_events(display, client, display._chti_chat_seen):
        if not event.get('outgoing') and event.get('type') in ('chat', 'invite'):
            display._chti_chat_unread = min(99, display._chti_chat_unread + 1)


QUICK_REPLIES = (
    'Salut !',
    'Tu veux jouer avec moi ?',
    'Oui, je suis prêt.',
    'Attends 2 minutes.',
    'Pas maintenant, merci.',
    'Merci, à bientôt !',
)


def choose_quick_reply(display, keys, client, seen_events, recipient_id, recipient):
    """Choix avec les memes entrees GPIO que les menus de la borne."""
    import pygame
    up, down, left, right, enter, escape = keys
    selected = 0
    while True:
        _new_events(display, client, seen_events)
        status, ident, players, events = client.snapshot()
        if status != 'CONNECTE' or not any(p.get('id') == recipient_id for p in players):
            display.message(['Joueur deconnecte : aucun message envoye.'])
            return None
        w, h = display.screen.get_size()
        gold, white, grey = (245, 189, 55), (238, 240, 245), (162, 176, 194)
        display.screen.fill((11, 19, 32))
        font = pygame.font.Font(None, max(18, int(h * .042)))
        title = pygame.font.Font(None, max(22, int(h * .05)))

        def text(value, x, y, width, color=white, police=None):
            police = police or font
            while value and police.size(value)[0] > width:
                value = value[:-1]
            display.screen.blit(police.render(value, True, color), (int(x), int(y)))

        text('REPONSES RAPIDES', w*.08, h*.055, w*.84, gold, title)
        text('MESSAGE POUR ' + recipient, w*.08, h*.13, w*.84, grey)
        zones = {}
        choices = list(QUICK_REPLIES) + ['RETOUR SANS ENVOYER']
        for i, label in enumerate(choices):
            rect = pygame.Rect(int(w*.08), int(h*(.22+i*.091)), int(w*.84), int(h*.075))
            zones['quick|' + str(i)] = rect
            pygame.draw.rect(display.screen, (130, 91, 26) if i == selected else (23, 40, 61),
                             rect, border_radius=6)
            text(label, rect.x+12, rect.y+int(h*.016), rect.width-24)
        hint = pygame.font.Font(None, max(15, int(h*.029)))
        text('Haut/bas : choisir | Valider : envoyer | Retour : annuler',
             w*.08, h*.91, w*.84, grey, hint)
        display.update_screen()
        key = display.rpi.listen_inputs(['arrows', 'fx', 'alpha'],
                                       ['enter', 'escape', 'single-click'], timeout=150)
        clicked = display.is_clicked(zones, key)
        if clicked:
            index = int(clicked.split('|', 1)[1])
            return QUICK_REPLIES[index] if index < len(QUICK_REPLIES) else None
        if key in escape:
            return None
        if key in up or key in down:
            selected = (selected + (-1 if key in up else 1)) % len(choices)
        elif key in enter:
            return QUICK_REPLIES[selected] if selected < len(QUICK_REPLIES) else None


def show(display, keys):
    import pygame
    up, down, left, right, enter, escape = keys
    if not getattr(display, '_chti_ready_online', False):
        display.message(['F2 : active PRET A JOUER EN LIGNE pour utiliser le chat'])
        return
    client = ensure_session(display, prompt=True)
    if client is None:
        return
    name = client.name
    display._chti_chat_open = True
    display._chti_chat_unread = 0
    selected = None
    action_index = 0
    resolved = display._chti_chat_resolved
    seen_events = display._chti_chat_seen
    note = 'Selectionne un joueur puis ECRIRE ou INVITER.'
    try:
        while True:
            for event in _new_events(display, client, seen_events):
                kind = event.get('type')
                if kind == 'error':
                    note = event.get('message', 'Erreur envoi')
                elif kind == 'reply':
                    note = event.get('name', '?') + (' : invitation acceptee.' if event.get('answer') == 'accept' else ' : invitation refusee.')
                elif event.get('outgoing') and kind == 'chat':
                    note = 'Message envoye.'
                elif event.get('outgoing') and kind == 'invite':
                    note = 'Invitation envoyee - en attente de reponse.'
            status, ident, players, events = client.snapshot()
            if client.auth_failed:
                display._chti_account_session = None
                display.message(['Session expirée : reconnectez-vous à votre compte.'])
                return
            players = [p for p in players if isinstance(p, dict) and p.get('id') != ident]
            ids = [p['id'] for p in players]
            if selected not in ids:
                selected = ids[0] if ids else None
            pending = [e for e in events if e.get('type') == 'invite'
                       and not e.get('outgoing') and e.get('invitation') not in resolved
                       and time.monotonic() - e['_received'] < e.get('ttl', 90)]
            for e in events:
                if e.get('type') == 'reply':
                    resolved.add(e.get('invitation'))
            pending = [e for e in pending if e.get('invitation') not in resolved]
            invitation = pending[0] if pending else None
            w, h = display.screen.get_size()
            display.screen.fill((11, 19, 32))
            gold, white, grey = (245, 189, 55), (238, 240, 245), (162, 176, 194)
            font = pygame.font.Font(None, max(16, int(h * .033)))
            title = pygame.font.Font(None, max(24, int(h * .055)))

            def text(value, x, y, width, color=white, police=None):
                police = police or font
                value = ' '.join(str(value).split())
                while value and police.size(value)[0] > width:
                    value = value[:-1]
                display.screen.blit(police.render(value, True, color), (int(x), int(y)))

            text('CHTIDARTS - JOUEURS ET CHAT', w*.03, h*.035, w*.94, gold, title)
            text(client.name + ' | ' + status, w*.03, h*.11, w*.71, grey)
            zones = {}
            logout_rect = pygame.Rect(int(w*.76), int(h*.105), int(w*.21), int(h*.05))
            zones['F6'] = logout_rect
            pygame.draw.rect(display.screen, (30,51,76), logout_rect, border_radius=5)
            text('F6 : DECONNEXION', logout_rect.x+5, logout_rect.y+3, logout_rect.width-10)
            pygame.draw.rect(display.screen, (23, 40, 61),
                             (int(w*.03), int(h*.18), int(w*.30), int(h*.55)), border_radius=8)
            text('JOUEURS CONNECTES', w*.045, h*.20, w*.27, gold)
            offset = max(0, ids.index(selected)-7) if selected in ids else 0
            for row, player in enumerate(players[offset:offset+8]):
                rect = pygame.Rect(int(w*.04), int(h*(.26+row*.055)), int(w*.28), int(h*.049))
                zones['player|'+player['id']] = rect
                if player['id'] == selected:
                    pygame.draw.rect(display.screen, (130, 91, 26), rect, border_radius=5)
                text(player['name'], rect.x+6, rect.y+3, rect.width-12)
            if not players:
                text('Aucun autre joueur', w*.045, h*.29, w*.27, grey)
            pygame.draw.rect(display.screen, (23, 40, 61),
                             (int(w*.35), int(h*.18), int(w*.62), int(h*.55)), border_radius=8)
            lines = []
            for event in events:
                kind = event.get('type')
                who = 'Moi' if event.get('outgoing') else event.get('name', '?')
                if kind in ('chat', 'invite'):
                    dest = next((p['name'] for p in players if p['id'] == event.get('to')), '?')
                    prefix = ('Moi -> '+dest) if event.get('outgoing') else who
                    lines.append(prefix + ': ' + event.get('text', ''))
                elif kind == 'reply':
                    lines.append(who + (' : invitation acceptee' if event.get('answer') == 'accept'
                                       else ' : invitation refusee'))
                elif kind == 'joined':
                    lines.append(event.get('name', '?') + ' rejoint le salon.')
                elif kind == 'error':
                    lines.append(event.get('message', 'Erreur'))
            # Le journal contient seulement les messages envoyes/reçus par cette borne.
            wrapped = []
            for line in lines:
                words, current = line.split(), ''
                for word in words:
                    candidate = (current+' '+word).strip()
                    if current and font.size(candidate)[0] > w*.58:
                        wrapped.append(current)
                        current = word
                    else:
                        current = candidate
                if current:
                    wrapped.append(current)
            for row, line in enumerate(wrapped[-10:]):
                text(line, w*.37, h*(.21+row*.047), w*.58)
            if invitation:
                note = invitation.get('name', '?') + ' te propose une partie : F3 accepter / F4 refuser'
            elif note.startswith('Selectionne'):
                note = 'Selectionne un joueur puis ECRIRE ou INVITER.'
            text(note, w*.03, h*.755, w*.94, gold)
            buttons = [('F1', 'ECRIRE'), ('F5', 'REPONSES RAPIDES'), ('F2', 'INVITER'),
                       ('F3', 'ACCEPTER'), ('F4', 'REFUSER'), ('back', 'RETOUR')]
            for i, (key, label) in enumerate(buttons):
                rect = pygame.Rect(int(w*(.03+(i%3)*.32)), int(h*(.805+(i//3)*.08)), int(w*.30), int(h*.068))
                zones[key] = rect
                pygame.draw.rect(display.screen, (130, 91, 26) if i == action_index else (30, 51, 76),
                                 rect, border_radius=6)
                text(label, rect.x+7, rect.y+int(h*.02), rect.width-14)
            text('Haut/bas : joueur | Gauche/droite : action | Entree : valider | Echap : retour',
                 w*.03, h*.965, w*.94, grey)
            display.update_screen()
            key = display.rpi.listen_inputs(['arrows', 'fx', 'alpha'],
                                           ['enter', 'escape', 'space', 'single-click'], timeout=150)
            clicked = display.is_clicked(zones, key)
            if clicked:
                key = clicked
            if key == 'F6':
                from include.chti_chat_account import logout
                logout(display)
                return
            if key in escape or key == 'back':
                return
            if isinstance(key, str) and key.startswith('player|'):
                selected = key.split('|', 1)[1]
                continue
            if key in up or key in down:
                if ids:
                    index = ids.index(selected) if selected in ids else 0
                    selected = ids[(index + (-1 if key in up else 1)) % len(ids)]
                continue
            if key in left or key in right:
                action_index = (action_index + (-1 if key in left else 1)) % len(buttons)
                continue
            if key in enter:
                key = buttons[action_index][0]
            if key == 'back':
                return
            if key in ('F1', 'F2', 'F5'):
                if not selected:
                    note = 'Aucun joueur selectionne.'
                    continue
                content = 'Salut, tu veux jouer avec moi ?'
                if key == 'F1':
                    recipient = next((p['name'] for p in players if p['id'] == selected), '?')
                    content = compose_message(display, keys, client, seen_events, recipient)
                    if content is None:
                        continue
                elif key == 'F5':
                    recipient = next((p['name'] for p in players if p['id'] == selected), '?')
                    content = choose_quick_reply(display, keys, client, seen_events, selected, recipient)
                    if content is None:
                        continue
                ok = client.command({'type': 'invite' if key == 'F2' else 'chat',
                                     'to': selected, 'text': content})
                note = 'Envoi en cours...' if ok else 'Chat deconnecte : message non envoye.'
            elif key in ('F3', 'F4'):
                if not invitation:
                    note = 'Aucune invitation en attente.'
                    continue
                ok = client.command({'type': 'reply', 'invitation': invitation['invitation'],
                                     'answer': 'accept' if key == 'F3' else 'refuse'})
                if ok:
                    resolved.add(invitation['invitation'])
                    note = ('Invitation acceptee : retour puis creer/rejoindre la partie.'
                            if key == 'F3' else 'Invitation refusee.')
                else:
                    note = 'Chat deconnecte : reponse non envoyee.'
    finally:
        display._chti_chat_open = False
        display._chti_chat_unread = 0


def set_game_activity(display, playing=False, room='', game='', server='', players=()):
    """Appelé par le match ; aucune requête réseau sur le thread du jeu."""
    data = {'playing':bool(playing),'room':str(room),'game':str(game),
            'server':str(server),'players':list(players)[:26]}
    display._chti_game_activity = data
    client = getattr(display, '_chti_chat_client', None)
    if client is None and playing:
        client = ensure_session(display, prompt=False)
    if client is not None:
        client.set_activity(data)
