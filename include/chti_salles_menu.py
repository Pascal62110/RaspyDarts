"""Combine les salles rejoignables du Master et les parties actives du VPS."""
import json
import urllib.request

URL = 'https://video.chtiraspycard.fr/joueurs-salles'


def count(value):
    try:
        return max(0, min(100, int(value)))
    except (TypeError, ValueError):
        return 0


def joinable(room):
    return (not room.get('CHTI_EN_COURS') and count(room.get('PLAYERS')) == 1
            and bool(room.get('GAMENAME')))


def active_rooms(host):
    request = urllib.request.Request(URL, headers={'Accept':'application/json'})
    with urllib.request.urlopen(request, timeout=2) as response:
        raw = response.read(262145)
    if len(raw)>262144:
        raise ValueError('Liste de salles trop volumineuse')
    data = json.loads(raw.decode('utf-8'))
    if not isinstance(data,dict) or not isinstance(data.get('rooms'),list):
        raise ValueError('Reponse des salles invalide')
    return data['rooms']


def merge_rooms(waiting, active, host, previous=()):
    # Les identifiants de salle sont propres au serveur de jeu.
    rows = {}
    for room in waiting:
        if not isinstance(room,dict) or not room.get('GAMENAME'):
            continue
        row = dict(room);row['CHTI_EN_COURS'] = False
        rows[str(row['GAMENAME'])] = row
    for room in active:
        if not isinstance(room,dict) or room.get('state')!='En cours':
            continue
        server = str(room.get('server',''))
        if server.rsplit(':',1)[0].casefold()!=host.casefold():
            continue
        name=room.get('name')
        if not isinstance(name,str) or not name:
            continue
        names=room.get('players',[])
        if not isinstance(names,list):names=[]
        row={'GAMENAME':name,'GAMETYPE':str(room.get('game','?')),
             'GAMECREATOR':'','PLAYERS':count(room.get('count')),
             'CHTI_EN_COURS':True,'CHTI_NOMS':[str(x) for x in names[:26]]}
        rows[name]=row  # La partie qui demarre remplace sa ligne en attente.
    order=[str(r.get('GAMENAME')) for r in previous if isinstance(r,dict)]
    ordered=[]
    for key in order+list(rows):
        if key in rows:ordered.append(rows.pop(key))
    return ordered[:12]


def label(room, index):
    game=str(room.get('GAMETYPE','?')).replace('_',' ')[:16]
    if room.get('CHTI_EN_COURS'):
        import re
        names=[re.sub(r'^\d+\s*·\s*','',n) for n in room.get('CHTI_NOMS',[])]
        versus=' VS '.join(names) if names else str(room.get('GAMENAME',''))
        return '{:02d}  {} | {} | EN COURS'.format(index+1,game,versus)
    creator=str(room.get('GAMECREATOR','?'))[:22]
    status='EN ATTENTE - REJOINDRE' if joinable(room) else 'COMPLET'
    return '{:02d}  {} | {} | {}/2 | {}'.format(index+1,game,creator,count(room.get('PLAYERS')),status)


def colors(room, selected=False):
    if joinable(room):
        return ((40,103,65) if selected else (29,77,49)),(146,255,179)
    return ((111,43,48) if selected else (79,32,40)),(255,155,151)
