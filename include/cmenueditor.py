"""
Editor of the screens of menus on the borne (Paramètres > Modifier les écrans) : the buttons
of a menu moved, resized by their handles, added or deleted, with the keyboard, the buttons
of the borne or the darts (keys of the navigation, docs/menu/menus.md section 9).

The screen is frozen when it opens : each button keeps the place it has on the screen (free
placement, section 7.5), so moving one never moves the others. Saved in the menus of the
theme (themes/<theme>/menu/menus.yaml), the previous file kept as menus.yaml.bak
"""

import copy
import os
import shutil
import time

import pygame

from include import cmenus
from include import cmenustyle

try:
    import yaml
except ImportError:
    yaml = None

# Menus the editor changes (name of the menu, text of the list of the screens)
SCREENS = (('main', 'editor-screen-main'), ('miscellaneous', 'editor-screen-miscellaneous'),
           ('settings', 'editor-screen-settings'))
# Steps of a move, in parts of the screen (+ and - change it)
STEPS = (0.0025, 0.005, 0.01, 0.02, 0.05)
# Handles of a button : (part of the width, part of the height) of the handle on its rect
HANDLES = ((0, 0), (0.5, 0), (1, 0), (1, 0.5), (1, 1), (0.5, 1), (0, 1), (0, 0.5))
# Frame of the button moved or resized, and its handle moved
MOVING = (255, 200, 0)
# Smallest button, in parts of the screen
SMALLEST = 0.02
# Keys added by the game to the buttons it shows (not written in the file)
RUNTIME_KEYS = ('logo_image', 'game_logo', 'unavailable')
# Keys of the automatic layouts : a button placed freely does not use them
LAYOUT_KEYS = ('span', 'cell', 'zone', 'space_before', 'space_left')


class Editor:
    '''
    The editor of one menu, drawn and driven by the Screen of the game
    '''

    def __init__(self, screen, name, keys):
        self.screen = screen
        self.name = name
        self.keys = keys
        self.menus = screen.menus()
        self.menu = self.menus.menu(name)
        self.resolution = self.menus.data.get('resolution')
        self.size = screen.screen.get_size()
        self.units = cmenustyle.Units(self.size, self.resolution)
        self.removed = []
        self.changed = False
        self.step = 2
        self.mode = 'select'
        self.handle = 4
        # The buttons shown in the menu (not those at the bottom), with their place on the screen
        shown = [button for button in self.menus.buttons(name)
                 if button.get('visible', True) is not False and not button.get('footer')]
        rects = cmenustyle.layout(self.menu, shown, self.size, self.resolution)[0]
        self.items = []
        for index, button in enumerate(shown, 1):
            if index in rects:
                self.items.append({'button': self.clean(button), 'rect': pygame.Rect(rects[index])})
        self.selected = 1

    @staticmethod
    def clean(button):
        '''
        A copy of a button without what the game added to it while showing it
        '''
        button = copy.deepcopy(button)
        for key in RUNTIME_KEYS:
            button.pop(key, None)
        return button

    def translate(self, key):
        return self.screen.lang.translate(key)

    # ------------------------------------------------------------------ drawing
    def background(self):
        '''
        The background of the menu (its own image, or the one of the theme)
        '''
        painter = self.screen.menu_painter()
        block = self.menu.get('background')
        if block is not None:
            block = cmenustyle.merge({'fit': 'cover'}, block) if isinstance(block, dict) else block
            self.screen.screen.fill((0, 0, 0))
            self.screen.screen.blit(painter.background(block, self.size), (0, 0))
        else:
            # On black : a background with transparency let the screen before show through
            self.screen.screen.fill((0, 0, 0))
            self.screen.display_background()

    def help_text(self):
        if self.mode == 'move':
            step = f"{STEPS[self.step] * 100:g}"
            return self.translate('editor-help-move').replace('{step}', step)
        if self.mode == 'resize':
            return self.translate('editor-help-resize')
        return self.translate('editor-help-select')

    def draw(self):
        '''
        The whole screen of the editor : the menu, its buttons at their place, the one chosen
        framed (its handles when it is resized), the bar of the editor
        '''
        screen = self.screen
        started = time.perf_counter()
        painter = screen.menu_painter()
        self.background()
        title = f"{self.translate('editor-title')} : {self.translate(dict(SCREENS)[self.name])}"
        screen.menu_header(title, self.help_text())
        shortcuts = cmenustyle.merge({'show': screen.colorset.get('main-sub-menu-shortcuts') is not None, 'format': '{key}',
                                      'position': 'top_left' if self.menu.get('layout') == 'tiles' else 'left'},
                                     self.menu.get('shortcuts') or {})
        for index, item in enumerate(self.items, 1):
            button = item['button']
            shown = screen.favorite_button(button) if self.name == 'main' else button
            style = screen.button_style(self.menu, shown)
            state = 'selected' if index == self.selected else ('disabled' if shown.get('unavailable') else 'normal')
            text = '' if shown.get('text', True) is None or ('text' not in shown and shown.get('logo')) else \
                screen.lang.translate(screen.button_text(shown))
            painter.draw_button(screen.screen, item['rect'], style, text, screen.button_icon(shown), state, self.units,
                                shortcut=screen.button_label(shown, self.menu) if shortcuts.get('show') else None,
                                shortcuts=shortcuts)
        if 1 <= self.selected <= len(self.items):
            rect = self.items[self.selected - 1]['rect']
            # The button chosen framed : green, gold while it is moved or resized
            color = screen.colorset['menu-ok'] if self.mode == 'select' else MOVING
            pygame.draw.rect(screen.screen, color, rect.inflate(8, 8), 3 if self.mode == 'select' else 5)
            if self.mode == 'resize':
                side = max(12, int(self.size[1] / 50))
                for number, (part_x, part_y) in enumerate(HANDLES):
                    # The handle moved by the arrows : bigger, gold
                    current = number == self.handle
                    square = pygame.Rect(0, 0, side * 2 if current else side, side * 2 if current else side)
                    square.center = (rect.x + int(rect.width * part_x), rect.y + int(rect.height * part_y))
                    pygame.draw.rect(screen.screen, MOVING if current else (255, 255, 255), square)
                    pygame.draw.rect(screen.screen, (0, 0, 0), square, 2)
        screen.update_screen()
        screen.logs.debug(f"Menu editor : drawn in {(time.perf_counter() - started) * 1000:.0f} ms")

    def rects(self):
        '''
        Places of the buttons, which can be chosen
        '''
        return {index: tuple(item['rect']) for index, item in enumerate(self.items, 1)}

    # ------------------------------------------------------------------ keys
    def key_in(self, key, direction):
        return key in set(self.menus.keys(direction)) or (direction == 'validate' and key in self.keys['enter']) or \
            (direction == 'back' and key in self.keys['escape'])

    def direction_of(self, key):
        for direction in ('up', 'down', 'left', 'right'):
            if self.key_in(key, direction):
                return direction
        return None

    def run(self):
        '''
        The editor until it is saved or given up : True if the menu was saved
        '''
        while True:
            self.draw()
            key = self.screen.rpi.listen_inputs(['arrows', 'fx', 'alpha', 'math'],
                                                ['escape', 'PLAYERBUTTON', 'BACKUPBUTTON', 'GAMEBUTTON', 'single-click',
                                                 'enter', 'space'],
                                                events=[(self.screen.wait_event_time, 'EVENT', 'wait')])
            if self.mode == 'move':
                self.moving(key)
                continue
            if self.mode == 'resize':
                self.resizing(key)
                continue
            clicked = self.screen.is_clicked({index: pygame.Rect(rect) for index, rect in self.rects().items()}, key)
            if clicked:
                self.selected = clicked
                key = 'enter'
            direction = self.direction_of(key)
            if direction is not None:
                self.selected = self.screen.move_selection(self.rects(), self.selected, direction)
                continue
            if self.key_in(key, 'back'):
                # The screen is all the menu's : adding, saving and leaving are behind Back
                choice = self.editor_menu()
                if choice == 'save' and self.save():
                    return True
                if choice == 'quit' and self.give_up():
                    return False
                if choice == 'add':
                    self.add()
                continue
            if self.key_in(key, 'validate') and 1 <= self.selected <= len(self.items):
                self.button_actions()

    def editor_menu(self):
        '''
        Back in the editor : a button added, the screen saved, or left without saving
        (back : the editor again)
        '''
        items = [{'id': 'add', 'action': 'add', 'text': 'editor-add-title', 'shortcut': 'F1'},
                 {'id': 'save', 'action': 'save', 'text': 'editor-save-quit', 'shortcut': 'F2'},
                 {'id': 'quit', 'action': 'quit', 'text': 'editor-quit', 'shortcut': 'F3'}]
        back = {'id': 'back', 'action': 'back', 'text': 'editor-continue', 'footer': 'left', 'shortcut': 'escape'}
        title = f"{self.translate('editor-title')} : {self.translate(dict(SCREENS)[self.name])}"
        return self.screen.run_menu('editor_menu', items + [back], items + [back], title=title).get('id')

    def give_up(self):
        '''
        Leaving without saving : asked if something changed
        '''
        return not self.changed or self.screen.ask_yes_no(self.translate('editor-discard'))

    def button_actions(self):
        '''
        The button chosen : moved, resized or deleted
        '''
        items = [{'id': 'move', 'action': 'move', 'text': 'editor-move', 'shortcut': 'F1'},
                 {'id': 'resize', 'action': 'resize', 'text': 'editor-resize', 'shortcut': 'F2'},
                 {'id': 'delete', 'action': 'delete', 'text': 'editor-delete', 'shortcut': 'F3'}]
        back = {'id': 'back', 'action': 'back', 'text': 'back', 'footer': 'left', 'shortcut': 'escape'}
        item = self.items[self.selected - 1]
        title = self.screen.lang.translate(self.screen.button_text(item['button']))
        choice = self.screen.run_menu('editor_button', items + [back], items + [back], title=title).get('id')
        if choice in ('move', 'resize'):
            self.mode = choice
            self.handle = 4
            self.before = pygame.Rect(item['rect'])
        elif choice == 'delete' and self.screen.ask_yes_no(f"{self.translate('editor-delete-confirm')} ({title})"):
            ident = self.menus.button_id(item['button'])
            if not item.get('new'):
                self.removed.append(ident)
            del self.items[self.selected - 1]
            self.selected = max(1, min(self.selected, len(self.items)))
            self.changed = True

    def clamp(self, rect):
        '''
        A rect kept on the screen
        '''
        rect.width = min(rect.width, self.size[0])
        rect.height = min(rect.height, self.size[1])
        rect.x = max(0, min(rect.x, self.size[0] - rect.width))
        rect.y = max(0, min(rect.y, self.size[1] - rect.height))
        return rect

    def moving(self, key):
        '''
        Move of the button chosen : arrows (by the step), + and - (the step), validate (done),
        back (its place before)
        '''
        rect = self.items[self.selected - 1]['rect']
        direction = self.direction_of(key)
        if direction is not None:
            step_x = max(1, int(round(STEPS[self.step] * self.size[0])))
            step_y = max(1, int(round(STEPS[self.step] * self.size[1])))
            move = {'up': (0, -step_y), 'down': (0, step_y), 'left': (-step_x, 0), 'right': (step_x, 0)}[direction]
            rect.move_ip(*move)
            self.clamp(rect)
            self.changed = True
        elif key in self.keys['plus']:
            self.step = min(len(STEPS) - 1, self.step + 1)
        elif key in self.keys['minus']:
            self.step = max(0, self.step - 1)
        elif self.key_in(key, 'validate'):
            self.mode = 'select'
        elif self.key_in(key, 'back'):
            self.items[self.selected - 1]['rect'] = self.before
            self.mode = 'select'

    def resizing(self, key):
        '''
        Resize of the button chosen by one of its handles : arrows (the handle, by the step),
        + and - (the next handle, the one before), validate (done), back (its size before)
        '''
        rect = self.items[self.selected - 1]['rect']
        direction = self.direction_of(key)
        if direction is not None:
            part_x, part_y = HANDLES[self.handle]
            step_x = max(1, int(round(STEPS[self.step] * self.size[0])))
            step_y = max(1, int(round(STEPS[self.step] * self.size[1])))
            smallest_x, smallest_y = int(SMALLEST * self.size[0]), int(SMALLEST * self.size[1])
            left, top, right, bottom = rect.left, rect.top, rect.right, rect.bottom
            delta_x = {'left': -step_x, 'right': step_x}.get(direction, 0)
            delta_y = {'up': -step_y, 'down': step_y}.get(direction, 0)
            # The handle moves the edges it is on
            if part_x == 0:
                left = max(0, min(left + delta_x, right - smallest_x))
            elif part_x == 1:
                right = min(self.size[0], max(right + delta_x, left + smallest_x))
            if part_y == 0:
                top = max(0, min(top + delta_y, bottom - smallest_y))
            elif part_y == 1:
                bottom = min(self.size[1], max(bottom + delta_y, top + smallest_y))
            self.items[self.selected - 1]['rect'] = pygame.Rect(left, top, right - left, bottom - top)
            self.changed = True
        elif key in self.keys['plus']:
            self.handle = (self.handle + 1) % len(HANDLES)
        elif key in self.keys['minus']:
            self.handle = (self.handle - 1) % len(HANDLES)
        elif self.key_in(key, 'validate'):
            self.mode = 'select'
        elif self.key_in(key, 'back'):
            self.items[self.selected - 1]['rect'] = self.before
            self.mode = 'select'

    # ------------------------------------------------------------------ adding
    def addable(self):
        '''
        Buttons which can be added : those of the game for this menu which are not shown,
        and for the main menu the favorites, the categories and the games
        '''
        present = {self.menus.button_id(item['button']) for item in self.items}
        choices = []
        defaults = cmenus.Menus(self.screen.logs, None, None).menu(self.name).get('buttons') or []
        for button in defaults:
            ident = self.menus.button_id(button)
            if ident not in present and not button.get('footer') and button.get('visible', True) is not False:
                choices.append((self.screen.lang.translate(self.screen.button_text(button)), self.clean(button)))
        if self.name == 'main':
            actions = {str(item['button'].get('action')) for item in self.items}
            for slot, favorite in self.screen.favorites().numbered():
                if f'favorite:{slot}' not in actions:
                    text = f"{self.translate('favorite')} {slot[3:]} : {favorite['game'].replace('_', ' ')}"
                    choices.append((text, {'id': slot, 'action': f'favorite:{slot}'}))
            # As in the screen of the categories : their logo, their name
            for category, logo in (('classic', 'menu_classic'), ('fun', 'menu_fun'), ('sport', 'menu_sport'),
                                   ('favorites', 'menu_favoris')):
                if f'category:{category}' not in actions:
                    text = f'dmd-game-{category}'
                    choices.append((f"{self.translate('editor-category')} : {self.translate(text)}",
                                    {'id': f'category-{category}', 'action': f'category:{category}',
                                     'text': text, 'logo': logo}))
            choices.append((self.translate('editor-add-game'), 'game'))
        return choices

    def choose_game(self):
        '''
        A game chosen by its category then its name, None : back
        '''
        back = {'id': 'back', 'action': 'back', 'text': 'back', 'footer': 'left', 'shortcut': 'escape'}
        categories = [{'id': category, 'action': category, 'text': text, 'shortcut': f'F{number}'}
                      for number, (category, text) in enumerate((('classic', 'Classics'), ('fun', 'Fun'), ('sport', 'Sports')), 1)]
        while True:
            category = self.screen.run_menu('editor_add', categories + [back], categories + [back],
                                            title=self.translate('editor-add-game')).get('id')
            if category == 'back':
                return None
            games = sorted(self.screen.get_games_list(category))
            items = [{'id': f'game{number}', 'action': 'game', 'text': game} for number, game in enumerate(games)]
            choice = self.screen.run_menu('editor_add', items + [back], items + [back],
                                          title=self.translate('editor-add-game')).get('id')
            if choice != 'back':
                return games[int(choice[4:])]

    def add(self):
        '''
        A button added in the middle of the screen, as big as the others (then to be placed)
        '''
        choices = self.addable()
        back = {'id': 'back', 'action': 'back', 'text': 'back', 'footer': 'left', 'shortcut': 'escape'}
        items = [{'id': f'add{number}', 'action': 'add', 'text': text} for number, (text, _) in enumerate(choices)]
        for number, item in enumerate(items[:9], 1):
            item['shortcut'] = f'F{number}'
        choice = self.screen.run_menu('editor_add', items + [back], items + [back],
                                      title=self.translate('editor-add-title')).get('id')
        if choice == 'back':
            return
        button = choices[int(choice[3:])][1]
        if button == 'game':
            game = self.choose_game()
            if game is None:
                return
            name = game.replace(' ', '_')
            button = {'id': f'game-{name}', 'action': f'game:{name}', 'text': game}
        # An id not used in this menu
        ident, number = self.menus.button_id(button), 2
        used = {self.menus.button_id(item['button']) for item in self.items}
        while self.menus.button_id(button) in used:
            button['id'] = f"{ident}-{number}"
            number += 1
        widths = sorted(item['rect'].width for item in self.items) or [int(self.size[0] / 4)]
        heights = sorted(item['rect'].height for item in self.items) or [int(self.size[1] / 10)]
        rect = pygame.Rect(0, 0, widths[len(widths) // 2], heights[len(heights) // 2])
        rect.center = (self.size[0] // 2, self.size[1] // 2)
        self.items.append({'button': button, 'rect': rect, 'new': True})
        if ident in self.removed:
            self.removed.remove(ident)
        self.selected = len(self.items)
        self.changed = True

    # ------------------------------------------------------------------ saving
    def place_of(self, rect):
        '''
        Free placement of a rect, in the units of the file (section 4)
        '''
        reference = self.units.reference
        values = {}
        for key, value, axis in (('x', rect.x, 'x'), ('y', rect.y, 'y'), ('width', rect.width, 'x'), ('height', rect.height, 'y')):
            size = self.size[0] if axis == 'x' else self.size[1]
            if reference is None:
                values[key] = round(value / size, 4)
            else:
                values[key] = int(round(value * (reference[0] if axis == 'x' else reference[1]) / size))
        return values

    def file_path(self):
        theme_dir = getattr(self.screen.file_class, 'theme_dir', None)
        return os.path.join(theme_dir, cmenus.THEME_FILE) if theme_dir else None

    def save(self):
        '''
        The menu written in the menus of the theme : its whole list of buttons (the hidden
        ones and those at the bottom kept), each button shown placed where it is
        '''
        path = self.file_path()
        try:
            if yaml is None or path is None:
                raise RuntimeError('no PyYAML or no theme')
            content = {}
            if os.path.isfile(path):
                with open(path, encoding='utf-8') as file:
                    content = yaml.safe_load(file) or {}
            menus = content.setdefault('menus', {})
            menu = menus.get(self.name) if isinstance(menus.get(self.name), dict) else {}
            menus[self.name] = menu
            placed = {self.menus.button_id(item['button']): item for item in self.items}
            buttons = []
            for button in self.menu.get('buttons') or []:
                if not isinstance(button, dict):
                    continue
                ident = self.menus.button_id(button)
                if ident in self.removed:
                    continue
                button = self.clean(button)
                if ident in placed:
                    item = placed.pop(ident)
                    button = dict(item['button'])
                    for key in LAYOUT_KEYS:
                        button.pop(key, None)
                    button['place'] = self.place_of(item['rect'])
                buttons.append(button)
            # The buttons added : after the others, before those at the bottom
            at = next((index for index, button in enumerate(buttons) if button.get('footer')), len(buttons))
            for item in placed.values():
                button = dict(item['button'])
                button['place'] = self.place_of(item['rect'])
                buttons.insert(at, button)
                at += 1
            menu['buttons'] = buttons
            menu.pop('button_changes', None)
            removed = [str(ident) for ident in cmenus.as_list(menu.get('removed'))]
            menu['removed'] = sorted(set(removed + self.removed)) if set(removed + self.removed) else None
            if menu['removed'] is None:
                menu.pop('removed')
            os.makedirs(os.path.dirname(path), exist_ok=True)
            if os.path.isfile(path):
                shutil.copyfile(path, f'{path}.bak')
            temporary = f'{path}.tmp'
            with open(temporary, 'w', encoding='utf-8') as file:
                yaml.safe_dump(content, file, allow_unicode=True, sort_keys=False, default_flow_style=False)
            os.replace(temporary, path)
            self.screen.logs.info(f"Menus : {self.name} saved by the editor in {path}")
        except Exception as error:    # pylint: disable=broad-except
            self.screen.logs.error(f"Menus : {self.name} not saved ({error})")
            self.screen.message([self.translate('editor-not-saved')], 2500, 'menu-ko', 'middle', 'big')
            return False
        # The menus read again, their drawings forgotten
        self.screen.menus_read = None
        self.screen.menu_backgrounds.clear()
        self.screen.menu_composites.clear()
        self.screen.message([self.translate('editor-saved')], 1500, None, 'middle', 'big')
        return True


def screens_menu(screen, keys):
    '''
    Paramètres > Modifier les écrans : the screen chosen, then its editor, until back
    '''
    back = {'id': 'back', 'action': 'back', 'text': 'back', 'footer': 'left', 'shortcut': 'escape'}
    items = [{'id': name, 'action': name, 'text': text, 'shortcut': f'F{number}'}
             for number, (name, text) in enumerate(SCREENS, 1)]
    choice = None
    while True:
        # Back from an editor : its screen chosen again
        choice = screen.run_menu('edit_screens', items + [back], items + [back], initial=choice,
                                 title=screen.lang.translate('edit-screens')).get('id')
        if choice == 'back':
            return
        Editor(screen, choice, keys).run()
