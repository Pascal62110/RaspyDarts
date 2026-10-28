"""Un compte authentifie par borne reseau ; aucun nom saisi librement."""
import json
import queue
import re
import ssl
import threading
import time
import urllib.request


def server_user(session):
    from include.caccount import BASE, COOKIE
    token = session.get('token', '')
    if not isinstance(token, str) or not re.fullmatch(r'[A-Za-z0-9_-]{30,128}', token):
        return None
    request = urllib.request.Request(BASE + '/joueurs-auth/me', headers={
        'Cookie': COOKIE + '=' + token, 'Cache-Control': 'no-store'})
    with urllib.request.urlopen(request, timeout=8, context=ssl.create_default_context()) as response:
        data = json.loads(response.read(8192).decode('utf-8'))
    user = data.get('user')
    if user is None:
        return None
    if (not isinstance(user, dict) or type(user.get('id')) is not int or user['id'] < 1
            or not isinstance(user.get('username'), str)
            or not re.fullmatch(r'[A-Za-z0-9_-]{3,18}', user['username'])):
        raise ValueError('Identite du serveur invalide')
    return {'id': user['id'], 'username': user['username']}


def wait_user(display, session):
    import pygame
    results = queue.Queue(maxsize=1)
    def worker():
        try:
            results.put((server_user(session), False))
        except Exception:
            results.put((None, True))
    threading.Thread(target=worker, daemon=True).start()
    clock = pygame.time.Clock()
    previous = getattr(display, '_lobby_auth_open', False)
    display._lobby_auth_open = True
    try:
        while True:
            try:
                user, failed = results.get_nowait()
                if failed:
                    raise RuntimeError('Serveur inaccessible. Verifiez Internet puis reessayez.')
                return user
            except queue.Empty:
                pass
            for event in pygame.event.get():
                if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                    raise RuntimeError('Verification annulee.')
            w, h = display.screen.get_size()
            display.screen.fill((11, 19, 32))
            font = pygame.font.Font(None, max(22, int(h * .045)))
            for index, line in enumerate(('PARTIE RESEAU', 'Verification de votre compte...', 'Echap : retour')):
                image = font.render(line, True, (238, 240, 245))
                display.screen.blit(image, ((w-image.get_width())//2, int(h*(.3+index*.13))))
            display.update_screen()
            clock.tick(30)
    finally:
        display._lobby_auth_open = previous


def network_players(display):
    from include import caccount as accounts
    from include.cchat import ensure_session
    session = getattr(display, '_lobby_account_session', None) or accounts.load_session()
    for attempt in range(2):
        if not isinstance(session, dict) or session.get('expires', 0) <= time.time():
            session = accounts.login_dialog(display)
        if not session:
            return 1, 'escape', False
        try:
            user = wait_user(display, session)
        except RuntimeError as error:
            display.message([str(error)], wait=2200)
            return 1, 'escape', False
        if user is not None:
            break
        # Session refusee par le VPS : ne jamais utiliser son identite locale.
        current = getattr(display, '_lobby_chat_client', None)
        if current is not None:
            current.stop()
        display._lobby_chat_client = None
        display._lobby_account_session = None
        accounts.forget_session()
        session = None
    else:
        display.message(['Connexion au compte requise. Reessayez.'], wait=1800)
        return 1, 'escape', False
    session = dict(session, user=user)
    current = getattr(display, '_lobby_chat_client', None)
    if current is not None and (current.token != session['token'] or current.auth_failed):
        current.stop()
        display._lobby_chat_client = None
    display._lobby_account_session = session
    display._lobby_ready_online = True
    display._lobby_chat_retry = 0
    if ensure_session(display, prompt=False) is None:
        display.message(['Connexion au salon impossible. Reessayez.'], wait=1800)
        return 1, 'escape', False
    label = '{:03d} · {}'.format(user['id'], user['username'])
    display.message(['Joueur reseau :', label], wait=1000)
    return 1, [label], False
