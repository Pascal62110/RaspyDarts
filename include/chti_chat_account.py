"""Connexion ChtiDarts pour borne : TLS, mot de passe masqué, session privée."""
import json
import os
import queue
import ssl
import threading
import time
import urllib.request
import urllib.error
from http.cookies import SimpleCookie
from pathlib import Path

BASE = 'https://video.chtiraspycard.fr'
COOKIE = '__Host-chti_session'


def session_file():
    return Path(os.path.expanduser('~/.pydarts/chat_account.json'))


def forget_session():
    try:
        session_file().unlink()
    except FileNotFoundError:
        pass


def load_session():
    try:
        data = json.loads(session_file().read_text(encoding='utf-8'))
        if (isinstance(data, dict) and isinstance(data.get('token'), str)
                and 30 <= len(data['token']) <= 128
                and all(c.isalnum() or c in '_-' for c in data['token'])
                and isinstance(data.get('user'), dict)
                and isinstance(data['user'].get('id'), int)
                and isinstance(data['user'].get('username'), str)
                and data.get('expires', 0) > time.time()):
            return data
    except (OSError, ValueError, TypeError):
        pass
    return None


def save_session(data):
    path = session_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name+'.tmp')
    fd = os.open(str(temp), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, 'w', encoding='utf-8') as file:
            json.dump(data, file)
        os.replace(str(temp), str(path))
    finally:
        try:
            temp.unlink()
        except FileNotFoundError:
            pass


def authenticate(username, password, remember=False):
    """Le mot de passe n'est ni enregistré ni inclus dans les journaux."""
    payload = json.dumps({'username':username, 'password':password,
                          'remember':bool(remember)}).encode('utf-8')
    request = urllib.request.Request(BASE+'/joueurs-auth/login', data=payload,
        headers={'Content-Type':'application/json', 'Origin':BASE}, method='POST')
    try:
        with urllib.request.urlopen(request, timeout=10, context=ssl.create_default_context()) as response:
            data = json.loads(response.read(8192).decode('utf-8'))
            cookie = SimpleCookie()
            for value in response.headers.get_all('Set-Cookie', []):
                cookie.load(value)
            token = cookie[COOKIE].value
        return {'token':token, 'user':data['user'],
                'expires':time.time()+(30*86400 if remember else 12*3600)}
    except urllib.error.HTTPError as error:
        if error.code == 401:
            raise ValueError('Pseudo ou mot de passe incorrect.')
        if error.code == 429:
            raise ValueError('Trop de tentatives. Attendez une minute.')
        if error.code == 400:
            raise ValueError('Pseudo : 3 à 18 caractères. Mot de passe : 10 minimum.')
        raise ValueError('Connexion au compte indisponible. Réessayez.')
    except (OSError, ValueError, KeyError):
        raise ValueError('Serveur inaccessible. Vérifiez la connexion Internet.')


def login_dialog(display):
    import pygame
    values = ['', '']
    focus = 0
    remember = False
    notice = 'Compte obligatoire. Inscription sur video.chtiraspycard.fr/joueurs'
    results = queue.Queue(maxsize=1)
    busy = False
    clock = pygame.time.Clock()
    backdrop = display.screen.copy()
    old_open = getattr(display, '_chti_chat_open', False)
    display._chti_chat_open = True
    old_repeat = pygame.key.get_repeat()
    pygame.key.set_repeat(450, 35)
    def worker(name, password, saved):
        try:
            results.put((authenticate(name,password,saved), None))
        except Exception as error:
            results.put((None, str(error)))
    try:
        while True:
            if busy:
                try:
                    result,error = results.get_nowait()
                except queue.Empty:
                    pass
                else:
                    busy = False
                    values[1] = ''
                    if result:
                        try:
                            if remember:
                                save_session(result)
                            else:
                                forget_session()
                        except OSError:
                            # Connexion valide, conservation limitée à la mémoire.
                            pass
                        return result
                    notice = error
            w,h = display.screen.get_size()
            display.screen.fill((11,19,32))
            font = pygame.font.Font(None, max(18,int(h*.038)))
            title = pygame.font.Font(None,max(24,int(h*.055)))
            def text(value,x,y,color=(238,240,245),police=None,width=None):
                police=police or font
                if width:
                    while value and police.size(value)[0]>width:
                        value=value[1:]
                display.screen.blit(police.render(value,True,color),(int(x),int(y)))
            text('CONNEXION AU COMPTE CHTIDARTS',w*.07,h*.08,(245,189,55),title)
            zones=[]
            for i,label in enumerate(('Pseudo','Mot de passe')):
                y=h*(.23+i*.17)
                text(label,w*.09,y-h*.045)
                rect=pygame.Rect(int(w*.08),int(y),int(w*.84),int(h*.09))
                zones.append(rect)
                pygame.draw.rect(display.screen,(23,40,61),rect,border_radius=6)
                pygame.draw.rect(display.screen,(245,189,55) if focus==i else (65,90,120),rect,2,border_radius=6)
                shown=values[i] if i==0 else '*'*len(values[i])
                text(shown+('|' if focus==i and not busy else ''),rect.x+12,rect.y+h*.02,width=rect.width-24)
            check=pygame.Rect(int(w*.08),int(h*.59),int(w*.84),int(h*.075))
            zones.append(check)
            text(('[X] ' if remember else '[ ] ')+'Rester connecté sur cette borne (30 jours)',w*.09,h*.60,
                 (245,189,55) if focus==2 else (238,240,245))
            button=pygame.Rect(int(w*.08),int(h*.70),int(w*.84),int(h*.09))
            zones.append(button)
            pygame.draw.rect(display.screen,(130,91,26) if focus==3 else (30,51,76),button,border_radius=6)
            text('CONNEXION...' if busy else 'SE CONNECTER',button.x+12,button.y+h*.02)
            # Découpe du message en lignes, jamais de mot de passe affiché.
            words=notice.split(); lines=['']
            for word in words:
                if font.size(lines[-1]+' '+word)[0]>w*.84:
                    lines.append(word)
                else:
                    lines[-1]=(lines[-1]+' '+word).strip()
            for i,line in enumerate(lines[:2]):
                text(line,w*.08,h*(.83+i*.045),(245,189,55))
            text('Tab / Haut / Bas : choisir | Entrée : valider | Échap : retour',w*.08,h*.95,(162,176,194),
                 pygame.font.Font(None,max(15,int(h*.028))))
            display.update_screen()
            submit=False
            for event in pygame.event.get():
                if event.type==pygame.QUIT:
                    return None
                if event.type==pygame.KEYDOWN and event.key==pygame.K_ESCAPE:
                    return None
                if busy:
                    continue
                if event.type==pygame.MOUSEBUTTONDOWN and event.button==1:
                    for i,rect in enumerate(zones):
                        if rect.collidepoint(event.pos):
                            focus=i
                            if i==2:
                                remember=not remember
                            if i==3:
                                submit=True
                if event.type!=pygame.KEYDOWN:
                    continue
                if event.key in (pygame.K_TAB,pygame.K_DOWN,pygame.K_UP):
                    focus=(focus+(-1 if event.key==pygame.K_UP else 1))%4
                elif event.key in (pygame.K_RETURN,pygame.K_KP_ENTER):
                    if focus==0:
                        focus=1
                    elif focus==2:
                        remember=not remember
                    else:
                        submit=True
                elif focus==2 and event.key==pygame.K_SPACE:
                    remember=not remember
                elif focus<2:
                    if event.key==pygame.K_BACKSPACE:
                        values[focus]=values[focus][:-1]
                    else:
                        for c in getattr(event,'unicode',''):
                            limit=18 if focus==0 else 128
                            if c.isprintable() and len(values[focus])<limit:
                                if focus==1 or c.isascii() and (c.isalnum() or c in '_-'):
                                    values[focus]+=c
            if submit and not busy:
                if len(values[0])<3 or len(values[1])<10:
                    notice='Pseudo : 3 caractères minimum. Mot de passe : 10 minimum.'
                else:
                    busy=True
                    notice='Vérification du compte...'
                    threading.Thread(target=worker,args=(values[0],values[1],remember),daemon=True).start()
            clock.tick(40)
    finally:
        values[1]=''
        pygame.key.set_repeat(*old_repeat)
        display._chti_chat_open=old_open
        display.screen.blit(backdrop,(0,0))


def logout(display):
    session = getattr(display, '_chti_account_session', None)
    client = getattr(display, '_chti_chat_client', None)
    if client:
        client.stop()
    display._chti_chat_client = None
    display._chti_account_session = None
    display._chti_ready_online = False
    display._chti_chat_status = 'CONNEXION AU COMPTE REQUISE'
    display._chti_chat_retry = 0
    try:
        forget_session()
    except OSError:
        pass
    if session:
        def revoke():
            request=urllib.request.Request(BASE+'/joueurs-auth/logout',data=b'{}',
                headers={'Origin':BASE,'Content-Type':'application/json',
                         'Cookie':COOKIE+'='+session['token']},method='POST')
            try:
                urllib.request.urlopen(request,timeout=8,context=ssl.create_default_context()).close()
            except Exception:
                pass
        threading.Thread(target=revoke,daemon=True).start()
