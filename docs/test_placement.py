"""
Test des regles de placement (docs/menu/menus.md, section 12) : les rectangles des boutons
calcules par le jeu (include/cmenustyle.py) et par la page (docs/menus-layout.js) doivent etre
identiques au pixel, pour des menus d'exemple, en 1024x600 (Pi de developpement) et en
1920x1080 (borne), avec et sans resolution de reference.
Usage : python docs/test_placement.py   (depuis la racine du depot ; Node.js requis)
"""
import json
import os
import subprocess
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from include import cmenustyle  # noqa: E402

SCREENS = [(1024, 600), (1920, 1080)]
RESOLUTIONS = [None, [1024, 600], [1920, 1080], [1280, 720]]


def cases():
    ''' Menus d'exemple : ceux du jeu, et des dispositions variees '''
    defaults = yaml.safe_load(open(os.path.join(ROOT, 'menus', 'defaults.yaml'), encoding='utf-8'))
    menus = [menu for menu in (defaults.get('menus') or {}).values() if isinstance(menu, dict) and menu.get('buttons')]
    nine = [{'id': f'b{i}'} for i in range(9)]
    menus += [
        {'layout': 'list', 'buttons': nine},
        {'layout': 'grid', 'columns': 4, 'buttons': nine + [{'id': 'x', 'space_before': 1.5}]},
        {'layout': 'tiles', 'columns': 3, 'buttons': nine},
        {'layout': 'tiles', 'columns': 2, 'buttons': nine[:5], 'align': 'top'},
        {'layout': 'list', 'overflow': 'scroll', 'buttons': nine * 3},
        {'layout': 'list', 'buttons': nine * 2, 'area': {'x': '10%', 'y': 0.2, 'width': 0.5, 'height': 0.5},
         'gap': {'x': 0.01, 'y': 0.03}, 'button_size': {'width': 0.8, 'height': 0.1}},
        {'layout': 'grid', 'columns': 3, 'buttons': [{'id': 'a'}, {'id': 'b', 'space_before': 0.5}, {'id': 'c'},
                                                       {'id': 'd', 'place': {'x': 0.9, 'y': 0.05, 'width': 0.05, 'height': 0.08,
                                                                             'anchor': 'top_right'}},
                                                       {'id': 'e', 'place': {'x': 512, 'y': 300, 'width': 100, 'height': 50,
                                                                             'anchor': 'center'}}]},
        # Boutons sur plusieurs cases (span) : les autres se rangent autour
        {'layout': 'grid', 'columns': 3, 'buttons': [{'id': 'a'}, {'id': 'b', 'span': {'columns': 2}}, {'id': 'c'},
                                                       {'id': 'd', 'span': {'columns': 2, 'rows': 2}}, {'id': 'e'},
                                                       {'id': 'f'}, {'id': 'g', 'space_before': 0.5}, {'id': 'h'}]},
        {'layout': 'list', 'buttons': nine[:4] + [{'id': 'w', 'span': {'columns': 2, 'rows': 2}}] + nine[4:7]},
        {'layout': 'tiles', 'columns': 3, 'buttons': [{'id': 't1', 'span': {'columns': 3}}] + nine[:5]},
        {'layout': 'grid', 'columns': 2, 'buttons': [{'id': 'r', 'span': {'rows': 3}}] + nine * 2},
        # Cases fixes (cell) : placees d'abord, les autres autour
        {'layout': 'grid', 'columns': 3, 'buttons': [{'id': 'a'}, {'id': 'z', 'cell': {'row': 1, 'column': 2}}, {'id': 'b'},
                                                       {'id': 'y', 'cell': {'row': 3, 'column': 0}, 'span': {'columns': 2}},
                                                       {'id': 'c'}, {'id': 'x', 'cell': {'row': 1, 'column': 2}}]},
        {'layout': 'list', 'buttons': nine[:3] + [{'id': 'k', 'cell': {'row': 5, 'column': 4}}]},
        # Parts de colonne (demi, tiers, quart) et plusieurs zones
        {'layout': 'list', 'buttons': [{'id': 'h1', 'span': {'columns': 0.5}}, {'id': 'h2', 'span': {'columns': 0.5}}, {'id': 'w'},
                                       {'id': 'q1', 'span': {'columns': 0.25}}, {'id': 't1', 'span': {'columns': 0.333}},
                                       {'id': 'f', 'cell': {'row': 3, 'column': 0.5}, 'span': {'columns': 0.5}}]},
        {'layout': 'grid', 'columns': 2, 'buttons': nine[:4] + [{'id': 'z1', 'zone': 'right'}, {'id': 'z2', 'zone': 'right'},
                                                                 {'id': 'z3', 'zone': 'unknown'}],
         'zones': {'right': {'layout': 'list', 'area': {'x': 0.75, 'y': 0.2, 'width': 0.2, 'height': 0.6}}}},
        # Ecart a gauche (space_left, en parts de colonne) et rangee vide gardee
        {'layout': 'grid', 'columns': 2, 'buttons': [{'id': 'g1', 'space_left': 0.5, 'span': {'columns': 0.5}}, {'id': 'g2'},
                                                       {'id': 'g3', 'space_left': 0.25}, {'id': 'g4', 'cell': {'row': 4, 'column': 0}}]},
    ]
    result = []
    for menu in menus:
        buttons = [button for button in menu['buttons'] if not button.get('footer') and button.get('visible', True) is not False]
        for screen in SCREENS:
            for resolution in RESOLUTIONS:
                for selected in (1, len(buttons)):
                    result.append({'menu': {key: value for key, value in menu.items() if key != 'buttons'},
                                   'buttons': buttons, 'screen': list(screen), 'resolution': resolution,
                                   'selected': selected})
    return result


def main():
    tests = cases()
    expected = []
    for test in tests:
        rects, page, pages = cmenustyle.layout(test['menu'], test['buttons'], tuple(test['screen']),
                                               test['resolution'], test['selected'])
        expected.append({'rects': {str(index): list(rect) for index, rect in rects.items()}, 'page': page, 'pages': pages})
    script = (
        "const L = require(process.argv[1]); const tests = JSON.parse(require('fs').readFileSync(0, 'utf8'));"
        "console.log(JSON.stringify(tests.map(t => { const r = L.layout(t.menu, t.buttons, t.screen, t.resolution, t.selected); return { rects: r.rects, page: r.page, pages: r.pages }; })));"
    )
    run = subprocess.run(['node', '-e', script, os.path.join(ROOT, 'docs', 'menus-layout.js')],
                         input=json.dumps(tests), capture_output=True, text=True, check=True)
    got = json.loads(run.stdout)
    errors = 0
    for test, want, have in zip(tests, expected, got):
        if want != have:
            errors += 1
            if errors <= 5:
                print('DIFFERENT :', json.dumps(test)[:200])
                print('  jeu  :', want)
                print('  page :', have)
    print(f"{len(tests)} cas, {errors} differences")
    sys.exit(1 if errors else 0)


if __name__ == '__main__':
    main()
