"""
Editor of the screens of menus on the borne (Paramètres > Modifier les écrans) : the buttons
of a menu moved, resized by their handles, added or deleted, their shortcut changed, with the
keyboard (a key held down repeats), the buttons of the borne, the darts (keys of the
navigation, docs/menu/menus.md section 9), the mouse or a finger (a button or its handles
dragged).

The screen is frozen when it opens : each button keeps the place it has on the screen (free
placement, section 7.5), so moving one never moves the others. Saved in the menus of the
theme (themes/<theme>/menu/menus.yaml), the previous file kept as menus.yaml.bak
"""

import copy
import os
import re
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
# Steps of a move or a resize, in parts of the screen (0 : one pixel ; + and - change it)
STEPS = (0, 0.0025, 0.005, 0.01, 0.02, 0.05)
FIRST_STEP = 3
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
# A key held down : repeated after this delay, at this interval (ms)
REPEAT = (350, 60)
# Keys which can be a shortcut of a button
SHORTCUT_KEYS = re.compile(r'^(F([1-9]|1[0-2])|[a-z0-9])$')
# A drag drawn again at most every (s) : a drawing takes 50 to 90 ms on a Pi 3
DRAG_FRAME = 0.04


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
        self.step = FIRST_STEP
        self.mode = 'select'
        self.handle = 4
        self.menu_rect = pygame.Rect(0, 0, 0, 0)
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

    def button_name(self, button):
        return self.screen.lang.translate(self.screen.button_text(button))

    # ------------------------------------------------------------------ drawing
    def background(self):
        '''
        The background of the menu (its own image, or the one of the theme) and its title
        '''
        screen = self.screen
        block = self.menu.get('background')
        # On black : a background with transparency let the screen before show through
        screen.screen.fill((0, 0, 0))
        if block is not None:
            block = cmenustyle.merge({'fit': 'cover'}, block) if isinstance(block, dict) else block
            screen.screen.blit(screen.menu_painter().background(block, self.size), (0, 0))
        else:
            screen.display_background()
        # Its own title : the screen stays recognisable
        title = screen.menu_text_look(self.name, 'title')[0]
        subtitle = screen.menu_text_look(self.name, 'subtitle')[0]
        if title or subtitle:
            screen.styled_title(self.name, title, subtitle)

    def step_text(self):
        step = STEPS[self.step]
        return '1 px' if step == 0 else f"{step * 100:g} %"

    def step_pixels(self, axis):
        step = STEPS[self.step]
        return 1 if step == 0 else max(1, int(round(step * self.size[0 if axis == 'x' else 1])))

    def help_text(self):
        key = {'move': 'editor-help-move', 'resize': 'editor-help-resize'}.get(self.mode, 'editor-help-select')
        return f"{self.translate(dict(SCREENS)[self.name])} · {self.translate(key).replace('{step}', self.step_text())}"

    def help_bar(self):
        '''
        The keys of the moment, in a thin band at the bottom (the title of the menu stays
        visible at the top), and the button Menu (adding, saving, leaving : also Back)
        '''
        screen = self.screen
        height = max(24, int(self.size[1] / 28))
        band = pygame.Surface((self.size[0], height), pygame.SRCALPHA)
        band.fill((0, 0, 0, 190))
        screen.screen.blit(band, (0, self.size[1] - height))
        font = screen.font(screen.defaultfontpath, int(height * 0.7))
        self.menu_rect = pygame.Rect(self.size[0] - int(self.size[0] / 9), self.size[1] - height + 2,
                                     int(self.size[0] / 9) - 4, height - 4)
        text = font.render(self.help_text(), True, (255, 255, 255))
        room = self.menu_rect.x - 16
        if text.get_width() > room:
            text = pygame.transform.smoothscale(text, (room, text.get_height()))
        screen.screen.blit(text, (8, self.size[1] - height + (height - text.get_height()) // 2))
        pygame.draw.rect(screen.screen, MOVING, self.menu_rect, border_radius=height // 3)
        label = font.render(self.translate('editor-menu-button'), True, (0, 0, 0))
        screen.screen.blit(label, label.get_rect(center=self.menu_rect.center))

    def handle_rects(self, rect):
        '''
        The squares of the handles of a rect (the one moved bigger while it is resized)
        '''
        side = max(12, int(self.size[1] / 50))
        squares = []
        for number, (part_x, part_y) in enumerate(HANDLES):
            bigger = self.mode == 'resize' and number == self.handle
            square = pygame.Rect(0, 0, side * 2 if bigger else side, side * 2 if bigger else side)
            square.center = (rect.x + int(rect.width * part_x), rect.y + int(rect.height * part_y))
            squares.append(square)
        return squares

    def draw(self):
        '''
        The whole screen of the editor : the menu, its buttons at their place (the one chosen
        last, over the others, framed, with its handles), the bar of the keys
        '''
        screen = self.screen
        started = time.perf_counter()
        painter = screen.menu_painter()
        self.background()
        shortcuts = cmenustyle.merge({'show': screen.colorset.get('main-sub-menu-shortcuts') is not None, 'format': '{key}',
                                      'position': 'top_left' if self.menu.get('layout') == 'tiles' else 'left'},
                                     self.menu.get('shortcuts') or {})
        for index in sorted(range(1, len(self.items) + 1), key=lambda number: number == self.selected):
            item = self.items[index - 1]
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
            if self.mode != 'move':
                # Its handles (dragged with the mouse or a finger) ; the one moved by the
                # arrows : bigger, gold
                for number, square in enumerate(self.handle_rects(rect)):
                    current = self.mode == 'resize' and number == self.handle
                    pygame.draw.rect(screen.screen, MOVING if current else (255, 255, 255), square)
                    pygame.draw.rect(screen.screen, (0, 0, 0), square, 2)
        self.help_bar()
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

    def listen(self):
        return self.screen.rpi.listen_inputs(['arrows', 'fx', 'alpha', 'math', 'num'],
                                             ['escape', 'PLAYERBUTTON', 'BACKUPBUTTON', 'GAMEBUTTON', 'single-click',
                                              'enter', 'space'],
                                             events=[(self.screen.wait_event_time, 'EVENT', 'wait')])

    def run(self):
        '''
        The editor until it is saved or given up : True if the menu was saved. A key held down
        repeats while it runs
        '''
        pygame.key.set_repeat(*REPEAT)
        try:
            return self.loop()
        finally:
            pygame.key.set_repeat()

    def loop(self):
        while True:
            self.draw()
            key = self.listen()
            if isinstance(key, tuple):
                choice = self.clicked(key)
                if choice is not None:
                    key = choice
                else:
                    continue
            if self.mode == 'move':
                self.moving(key)
                continue
            if self.mode == 'resize':
                self.resizing(key)
                continue
            direction = self.direction_of(key)
            if direction is not None:
                self.selected = self.screen.move_selection(self.rects(), self.selected, direction)
                continue
            if self.key_in(key, 'back') or key == 'menu':
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

    # ------------------------------------------------------------------ mouse and finger
    def clicked(self, position):
        '''
        A click (or a touch) : the button Menu ('menu') ; a handle of the button chosen or a
        button dragged ; a button chosen ; the button already chosen clicked without moving it :
        its actions ('enter'). None : done here
        '''
        if self.menu_rect.collidepoint(position):
            self.mode = 'select'
            return 'menu'
        if 1 <= self.selected <= len(self.items) and self.mode != 'move':
            for number, square in enumerate(self.handle_rects(self.items[self.selected - 1]['rect'])):
                if square.inflate(10, 10).collidepoint(position):
                    self.drag(position, number)
                    return None
        # The button on top first : the chosen one is drawn over the others
        order = sorted(range(1, len(self.items) + 1), key=lambda number: number == self.selected, reverse=True)
        index = next((number for number in order if self.items[number - 1]['rect'].collidepoint(position)), None)
        self.screen.logs.debug(f"Menu editor : click at {position}, button {index}")
        if index is None:
            return None
        already = index == self.selected
        self.selected = index
        self.mode = 'select'
        if not self.drag(position, None) and already:
            return 'enter'
        return None

    def pointer_events(self):
        '''
        Positions of the pointer since the last call, and whether it was released : the mouse,
        or a finger (the clicks SDL makes from the touches are left aside)
        '''
        width, height = self.size
        positions, released = [], False
        for event in pygame.event.get((pygame.MOUSEMOTION, pygame.MOUSEBUTTONUP, pygame.FINGERMOTION, pygame.FINGERUP)):
            if event.type in (pygame.FINGERMOTION, pygame.FINGERUP):
                positions.append((int(event.x * width), int(event.y * height)))
                released = released or event.type == pygame.FINGERUP
            elif not getattr(event, 'touch', False):
                positions.append(event.pos)
                released = released or event.type == pygame.MOUSEBUTTONUP
        return positions, released

    def drag(self, start, handle):
        '''
        The button chosen dragged (handle None) or resized by a handle, until the mouse button
        or the finger is released : True if it moved
        '''
        item = self.items[self.selected - 1]
        before = pygame.Rect(item['rect'])
        touch = getattr(self.screen.rpi, 'last_input_touch', False)
        moved, drawn = False, 0
        while True:
            positions, released = self.pointer_events()
            if positions:
                delta_x, delta_y = positions[-1][0] - start[0], positions[-1][1] - start[1]
                if moved or abs(delta_x) > 3 or abs(delta_y) > 3:
                    moved = True
                    if handle is None:
                        item['rect'] = self.clamp(before.move(delta_x, delta_y))
                    else:
                        item['rect'] = self.stretched(before, handle, delta_x, delta_y)
                    self.changed = True
            if released or (not touch and not pygame.mouse.get_pressed()[0]):
                break
            if moved and time.perf_counter() - drawn > DRAG_FRAME:
                self.draw()
                drawn = time.perf_counter()
            pygame.time.wait(10)
        return moved

    # ------------------------------------------------------------------ actions
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

    def shortcut_text(self, button):
        keys = cmenus.as_list(button.get('shortcut'))
        if not keys or str(keys[0]).lower() == 'none':
            return self.translate('editor-shortcut-none')
        # The keys which are words : their name (Échap, Entrée, Espace)
        key = str(keys[0])
        return self.translate(f'editor-key-{key}') if key in ('escape', 'enter', 'space') else key

    def button_actions(self):
        '''
        The button chosen : moved, resized, its shortcut changed, or deleted
        '''
        item = self.items[self.selected - 1]
        name = self.button_name(item['button'])
        while True:
            items = [{'id': 'move', 'action': 'move', 'text': 'editor-move', 'shortcut': 'F1'},
                     {'id': 'resize', 'action': 'resize', 'text': 'editor-resize', 'shortcut': 'F2'},
                     {'id': 'shortcut', 'action': 'shortcut', 'shortcut': 'F3',
                      'text': f"{self.translate('editor-shortcut')} : {self.shortcut_text(item['button'])}"},
                     {'id': 'delete', 'action': 'delete', 'text': 'editor-delete', 'shortcut': 'F4'}]
            back = {'id': 'back', 'action': 'back', 'text': 'back', 'footer': 'left', 'shortcut': 'escape'}
            choice = self.screen.run_menu('editor_button', items + [back], items + [back], title=name).get('id')
            if choice == 'shortcut':
                self.shortcut(item)
                continue
            if choice in ('move', 'resize'):
                self.mode = choice
                self.handle = 4
            elif choice == 'delete' and self.screen.ask_yes_no(f"{self.translate('editor-delete-confirm')} ({name})"):
                ident = self.menus.button_id(item['button'])
                if not item.get('new'):
                    self.removed.append(ident)
                del self.items[self.selected - 1]
                self.selected = max(1, min(self.selected, len(self.items)))
                self.changed = True
            return

    def shortcut(self, item):
        '''
        The shortcut of a button : changed (the key pressed ; taken from another button of
        the screen if wanted) or removed
        '''
        button = item['button']
        has = self.shortcut_text(button) != self.translate('editor-shortcut-none')
        items = [{'id': 'change', 'action': 'change', 'text': 'editor-shortcut-change', 'shortcut': 'F1'}]
        if has:
            items.append({'id': 'remove', 'action': 'remove', 'text': 'editor-shortcut-remove', 'shortcut': 'F2'})
        back = {'id': 'back', 'action': 'back', 'text': 'back', 'footer': 'left', 'shortcut': 'escape'}
        title = f"{self.button_name(button)} · {self.translate('editor-shortcut')} : {self.shortcut_text(button)}"
        choice = self.screen.run_menu('editor_button', items + [back], items + [back], title=title).get('id')
        if choice == 'remove':
            button.pop('shortcut', None)
            self.changed = True
            return
        if choice != 'change':
            return
        self.screen.display_background()
        self.screen.menu_header(self.button_name(button), self.translate('editor-shortcut-press'))
        self.screen.update_screen()
        while True:
            key = self.listen()
            if self.key_in(key, 'back'):
                return
            key = str(key)
            if SHORTCUT_KEYS.match(key):
                break
        # Another button of the screen with this key : it loses it if wanted
        for other in self.items:
            if other is not item and key in [str(value) for value in cmenus.as_list(other['button'].get('shortcut'))]:
                question = self.translate('editor-shortcut-taken').replace('{key}', key).replace(
                    '{button}', self.button_name(other['button']))
                if not self.screen.ask_yes_no(question):
                    return
                other['button'].pop('shortcut', None)
        button['shortcut'] = key
        self.changed = True

    def clamp(self, rect):
        '''
        A rect kept on the screen
        '''
        rect = pygame.Rect(rect)
        rect.width = min(rect.width, self.size[0])
        rect.height = min(rect.height, self.size[1])
        rect.x = max(0, min(rect.x, self.size[0] - rect.width))
        rect.y = max(0, min(rect.y, self.size[1] - rect.height))
        return rect

    def stretched(self, rect, handle, delta_x, delta_y):
        '''
        A rect whose handle moved : the edges it is on, kept on the screen and not too small
        '''
        part_x, part_y = HANDLES[handle]
        smallest_x, smallest_y = int(SMALLEST * self.size[0]), int(SMALLEST * self.size[1])
        left, top, right, bottom = rect.left, rect.top, rect.right, rect.bottom
        if part_x == 0:
            left = max(0, min(left + delta_x, right - smallest_x))
        elif part_x == 1:
            right = min(self.size[0], max(right + delta_x, left + smallest_x))
        if part_y == 0:
            top = max(0, min(top + delta_y, bottom - smallest_y))
        elif part_y == 1:
            bottom = min(self.size[1], max(bottom + delta_y, top + smallest_y))
        return pygame.Rect(left, top, right - left, bottom - top)

    def stepped(self, key):
        '''
        + and - : the step (one pixel to 5 % of the screen). True if the key was one of them
        '''
        if key in self.keys['plus']:
            self.step = min(len(STEPS) - 1, self.step + 1)
        elif key in self.keys['minus']:
            self.step = max(0, self.step - 1)
        else:
            return False
        return True

    def moving(self, key):
        '''
        Move of the button chosen : arrows (by the step), + and - (the step), validate or
        back (done)
        '''
        item = self.items[self.selected - 1]
        direction = self.direction_of(key)
        if direction is not None:
            step_x, step_y = self.step_pixels('x'), self.step_pixels('y')
            move = {'up': (0, -step_y), 'down': (0, step_y), 'left': (-step_x, 0), 'right': (step_x, 0)}[direction]
            item['rect'] = self.clamp(item['rect'].move(*move))
            self.changed = True
        elif self.stepped(key):
            pass
        elif self.key_in(key, 'validate') or self.key_in(key, 'back'):
            self.mode = 'select'

    def resizing(self, key):
        '''
        Resize of the button chosen by one of its handles : arrows (the handle, by the step),
        + and - (the step), validate (the next handle), back (done)
        '''
        item = self.items[self.selected - 1]
        direction = self.direction_of(key)
        if direction is not None:
            delta_x = {'left': -1, 'right': 1}.get(direction, 0) * self.step_pixels('x')
            delta_y = {'up': -1, 'down': 1}.get(direction, 0) * self.step_pixels('y')
            item['rect'] = self.stretched(item['rect'], self.handle, delta_x, delta_y)
            self.changed = True
        elif self.stepped(key):
            pass
        elif self.key_in(key, 'validate'):
            self.handle = (self.handle + 1) % len(HANDLES)
        elif self.key_in(key, 'back'):
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
                choices.append((self.button_name(button), self.clean(button)))
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
        A game chosen by its category then its name (in columns), None : back
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
            choice = self.screen.run_menu('editor_games', items + [back], items + [back],
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
