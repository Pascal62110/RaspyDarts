"""
Look of the menus described by files (docs/menu/menus.md, sections 4, 7 and 12) : where the
buttons go (layout, free places, pages) and how a button looks in each of its states
(shape, background colour and image, border, icon, text). Buttons of the style « classic »
are drawn by Screen as always (menu_item, logo_item) : this module draws the other styles.

The layout is computed without pygame (rectangles of integers) : the configurator of the
GitHub page does the same computations, a test compares both
"""

import math
import os

from include import cpaths

# Values of a style when nothing is said (section 7.2)
STYLE_DEFAULTS = {
    'shape': 'rounded',
    'radius': 0.25,
    'background': {'color': 'menu-buttons', 'image': None, 'fit': 'stretch', 'position': 'center',
                   'offset': [0, 0], 'size': [1.0, 1.0], 'opacity': 1.0, 'slice': 12},
    'border': {'width': 0, 'color': 'menu-border'},
    'shadow': False,
    'text': {'font': None, 'size': 0.045, 'color': 'menu-text', 'align': 'center', 'position': 'center',
             'offset': [0, 0], 'shadow': False, 'bold': False},
    'icon': {'position': 'left', 'size': 0.7, 'fit': 'contain'},
    'selected': {'background': {'color': 'menu-selected'}, 'text': {'color': 'menu-text-white'}},
    'disabled': {'background': {'color': '#808080'}, 'text': {'color': '#C0C0C0'}},
    'pressed': {'scale': 0.96},
}
STATES = ('selected', 'disabled', 'pressed')

# Layouts (section 7.4)
LAYOUT_DEFAULTS = {
    'list': {'area': {'x': 0.25, 'y': 0.18, 'width': 0.5, 'height': 0.72}, 'columns': 1,
             'button_size': {'width': 1.0, 'height': 0.09}},
    'grid': {'area': {'x': 0.1, 'y': 0.18, 'width': 0.8, 'height': 0.72}, 'columns': 3,
             'button_size': {'width': 1.0, 'height': 0.09}},
    'tiles': {'area': {'x': 0.1, 'y': 0.18, 'width': 0.8, 'height': 0.72}, 'columns': 3,
              'button_size': {'width': 1.0, 'height': None}},
}
GAP_DEFAULT = {'x': 0.02, 'y': 0.015}
ANCHORS = {'top_left': (0, 0), 'top_right': (1, 0), 'bottom_left': (0, 1), 'bottom_right': (1, 1),
           'center': (0.5, 0.5), 'top': (0.5, 0), 'bottom': (0.5, 1), 'left': (0, 0.5), 'right': (1, 0.5)}


def merge(base, top):
    '''
    The values of top over those of base, dictionaries key by key
    '''
    if not isinstance(base, dict) or not isinstance(top, dict):
        return top if top is not None else base
    result = dict(base)
    for key, value in top.items():
        result[key] = merge(result.get(key), value) if isinstance(value, dict) else value
    return result


class Units:
    '''
    Values of a file in pixels of the screen (section 4) : fractions of the screen, or
    pixels of a reference resolution, or percentages ('50%'). Rounded once
    '''

    def __init__(self, screen_size, resolution=None):
        self.width, self.height = screen_size
        self.reference = resolution if isinstance(resolution, (list, tuple)) and len(resolution) == 2 else None

    def length(self, value, axis):
        '''
        A position or a size along x or y, in pixels (a float : rounded by the caller)
        '''
        size = self.width if axis == 'x' else self.height
        if isinstance(value, str) and value.strip().endswith('%'):
            return float(value.strip()[:-1]) / 100 * size
        value = float(value or 0)
        if self.reference is not None:
            return value * size / (self.reference[0] if axis == 'x' else self.reference[1])
        return value * size

    def text(self, value):
        '''
        Size of a text : a part of the height of the screen, or pixels of the reference
        '''
        return max(1, int(round(self.length(value, 'y'))))


def round_half_up(value):
    '''
    Rounding of the rules of placement (0.5 goes up), the same in JavaScript (Math.round)
    '''
    return int(math.floor(value + 0.5))


def layout(menu, buttons, screen_size, resolution=None, selected=1):
    '''
    Rectangles (x, y, width, height) of the buttons of a menu (section 12) : those of the
    layout, page of the selected button only, then those placed freely.
    Returns ({index : rect}, page, pages) ; index from 1 in the order of buttons
    '''
    units = Units(screen_size, resolution)
    kind = str(menu.get('layout') or 'list')
    defaults = LAYOUT_DEFAULTS.get(kind, LAYOUT_DEFAULTS['list'])
    area = merge(defaults['area'], menu.get('area') or {})
    columns = max(1, int(menu.get('columns') or defaults['columns']))
    size = merge(defaults['button_size'], menu.get('button_size') or {})
    gap = merge(GAP_DEFAULT, menu.get('gap') or {})

    area_x, area_y = units.length(area['x'], 'x'), units.length(area['y'], 'y')
    area_w, area_h = units.length(area['width'], 'x'), units.length(area['height'], 'y')
    gap_x, gap_y = units.length(gap['x'], 'x'), units.length(gap['y'], 'y')
    column_w = (area_w - (columns - 1) * gap_x) / columns
    button_w = float(size['width']) * column_w

    flowing = [index for index, button in enumerate(buttons, 1) if not button.get('place')]
    if size.get('height') is not None:
        button_h = units.length(size['height'], 'y')
    else:
        # Square tiles : as large as all their rows hold in the area (3 rows at least, then pages)
        needed = max(1, min(3, math.ceil(len(flowing) / columns)))
        button_w = button_h = min(button_w, (area_h - (needed - 1) * gap_y) / needed)
    rows = []
    for position, index in enumerate(flowing):
        if position % columns == 0:
            rows.append([])
        rows[-1].append(index)

    # Rows of each page : as many as the area holds (space_before included)
    pages, page_rows, used = [], [], 0.0
    for row in rows:
        space = sum(float(buttons[index - 1].get('space_before', 0) or 0) for index in row) * button_h
        height = space + button_h + (gap_y if page_rows else 0)
        if page_rows and used + height > area_h + 0.5:
            pages.append(page_rows)
            page_rows, used = [], 0.0
            height = space + button_h
        page_rows.append(row)
        used += height
    if page_rows:
        pages.append(page_rows)
    if str(menu.get('overflow') or 'pages') == 'scroll':
        pages = [sum(pages, [])] if pages else []

    page = 0
    for number, rows_of_page in enumerate(pages):
        if any(selected in row for row in rows_of_page):
            page = number

    rects = {}
    if pages:
        rows_of_page = pages[page]
        # Above each row : its space_before, and a gap after the first row
        heights = []
        for position, row in enumerate(rows_of_page):
            space = sum(float(buttons[index - 1].get('space_before', 0) or 0) for index in row) * button_h
            heights.append(space + (gap_y if position else 0))
        block_h = sum(heights) + len(rows_of_page) * button_h
        top = area_y + ((area_h - block_h) / 2 if str(menu.get('align') or 'center') == 'center' else 0)
        if str(menu.get('overflow') or 'pages') == 'scroll' and block_h > area_h:
            # The selected button stays in the area
            row_of = next(position for position, row in enumerate(rows_of_page) if selected in row)
            selected_bottom = sum(heights[:row_of + 1]) + (row_of + 1) * button_h
            top = area_y - max(0, selected_bottom - area_h)
        pos_y = top
        for position, row in enumerate(rows_of_page):
            pos_y += heights[position]
            # Columns of the row centred in the area (a last row not full too)
            used_w = len(row) * column_w + (len(row) - 1) * gap_x
            left = area_x + (area_w - used_w) / 2
            for column, index in enumerate(row):
                pos_x = left + column * (column_w + gap_x) + (column_w - button_w) / 2
                rects[index] = (round_half_up(pos_x), round_half_up(pos_y), round_half_up(button_w), round_half_up(button_h))
            pos_y += button_h

    for index, button in enumerate(buttons, 1):
        place = button.get('place')
        if not isinstance(place, dict):
            continue
        width = units.length(place.get('width', 0.1), 'x')
        height = units.length(place.get('height', 0.08), 'y')
        anchor = ANCHORS.get(str(place.get('anchor') or 'top_left'), (0, 0))
        pos_x = units.length(place.get('x', 0), 'x') - anchor[0] * width
        pos_y = units.length(place.get('y', 0), 'y') - anchor[1] * height
        rects[index] = (round_half_up(pos_x), round_half_up(pos_y), round_half_up(width), round_half_up(height))
    return rects, page, len(pages)


class Painter:
    '''
    Draws the buttons, fonds and titles of the styles other than « classic ». Every surface
    drawn is kept (a few menus : the same buttons are drawn again and again)
    '''

    CACHE = 192

    def __init__(self, screen):
        self.screen = screen
        self.surfaces = {}
        self.images = {}

    # ------------------------------------------------------------------ values
    def color(self, value, default=(128, 128, 128)):
        '''
        A colour of the theme (Colorset.cfg) or '#RRGGBB(AA)' : a tuple, None if none
        '''
        if value is None or value is False:
            return None
        if isinstance(value, (list, tuple)):
            return tuple(int(part) for part in value)
        value = str(value)
        if value.startswith('#') and len(value) in (7, 9):
            try:
                return tuple(int(value[i:i + 2], 16) for i in range(1, len(value), 2))
            except ValueError:
                return default
        color = self.screen.colorset.get(value)
        return tuple(color) if isinstance(color, (list, tuple)) else default

    def image_path(self, path):
        '''
        File of an image : in the theme, then in ~/.raspydarts, then in the game
        '''
        if not path:
            return None
        path = str(path)
        theme_dir = getattr(self.screen.file_class, 'theme_dir', '') or ''
        candidates = [path, os.path.join(theme_dir, path), os.path.join(cpaths.user_dir(), path),
                      os.path.join(cpaths.ROOT_DIR, path), os.path.join(cpaths.ROOT_DIR, 'images', path)]
        for candidate in candidates:
            if os.path.isfile(candidate):
                return candidate
        relative = path[7:] if path.startswith('images/') else path
        return self.screen.file_class.get_full_filename(relative, 'images')

    def image(self, path):
        '''
        An image (with transparency), None if it cannot be read
        '''
        import pygame
        full = self.image_path(path)
        if full is None:
            return None
        if full not in self.images:
            try:
                self.images[full] = pygame.image.load(full).convert_alpha()
            except Exception as error:    # pylint: disable=broad-except
                self.screen.logs.warning(f"Menus : image {path} not read ({error})")
                self.images[full] = None
        return self.images[full]

    def font_path(self, name):
        '''
        File of a font : in the theme, ~/.raspydarts/fonts, the game ; the font of the theme else
        '''
        if name:
            found = self.screen.file_class.get_full_filename(str(name), 'fonts')
            if found:
                return found
        return self.screen.defaultfontpath

    # ------------------------------------------------------------------ drawing
    def state_style(self, style, state):
        '''
        A style in a state : the values of the state over the normal ones
        '''
        style = merge(STYLE_DEFAULTS, style or {})
        if state in STATES:
            style = merge(style, style.get(state) or {})
        return style

    def fill_image(self, picture, size, block):
        '''
        An image filling a surface of this size as the background asks (fit, section 7.3 bis)
        '''
        import pygame
        width, height = size
        surface = pygame.Surface(size, pygame.SRCALPHA)
        fit = str(block.get('fit') or 'stretch')
        image_w, image_h = picture.get_size()
        anchor = ANCHORS.get(str(block.get('position') or 'center'), (0.5, 0.5))
        offset = block.get('offset') or [0, 0]
        if fit == 'stretch':
            surface.blit(pygame.transform.smoothscale(picture, size), (0, 0))
        elif fit in ('cover', 'contain', 'center'):
            if fit == 'cover':
                ratio = max(width / image_w, height / image_h)
            elif fit == 'contain':
                ratio = min(width / image_w, height / image_h)
            else:
                part = block.get('size') or [1.0, 1.0]
                ratio = min(width * float(part[0]) / image_w, height * float(part[1]) / image_h)
            scaled = pygame.transform.smoothscale(picture, (max(1, int(image_w * ratio)), max(1, int(image_h * ratio))))
            pos_x = (width - scaled.get_width()) * anchor[0] + float(offset[0]) * width
            pos_y = (height - scaled.get_height()) * anchor[1] + float(offset[1]) * height
            surface.blit(scaled, (int(pos_x), int(pos_y)))
        elif fit == 'tile':
            for pos_x in range(0, width, image_w):
                for pos_y in range(0, height, image_h):
                    surface.blit(picture, (pos_x, pos_y))
        elif fit == 'slice':
            border = max(1, min(int(block.get('slice') or 12), image_w // 2 - 1, image_h // 2 - 1, width // 2, height // 2))
            inner_w, inner_h = image_w - 2 * border, image_h - 2 * border
            target_w, target_h = width - 2 * border, height - 2 * border
            for (sx, sw, tx, tw) in ((0, border, 0, border), (border, inner_w, border, target_w),
                                     (image_w - border, border, width - border, border)):
                for (sy, sh, ty, th) in ((0, border, 0, border), (border, inner_h, border, target_h),
                                         (image_h - border, border, height - border, border)):
                    if tw > 0 and th > 0 and sw > 0 and sh > 0:
                        part = picture.subsurface(pygame.Rect(sx, sy, sw, sh))
                        surface.blit(pygame.transform.smoothscale(part, (tw, th)), (tx, ty))
        return surface

    def background(self, block, size, radius=0, shape='rectangle'):
        '''
        A background (colour and/or image) of this size, cut to the shape
        '''
        import pygame
        if isinstance(block, str):
            block = {'image': block} if '/' in block or block.lower().endswith(('.png', '.jpg', '.jpeg')) else {'color': block}
        block = block or {}
        surface = pygame.Surface(size, pygame.SRCALPHA)
        if shape == 'none':
            return surface
        color = self.color(block.get('color'))
        if color is not None:
            pygame.draw.rect(surface, color, surface.get_rect(), border_radius=radius)
        picture = self.image(block.get('image')) if block.get('image') else None
        if picture is not None:
            filled = self.fill_image(picture, size, block)
            if radius > 0:
                # Cut to the rounded shape
                mask = pygame.Surface(size, pygame.SRCALPHA)
                pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(), border_radius=radius)
                filled.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
            surface.blit(filled, (0, 0))
        opacity = float(block.get('opacity', 1.0) if block.get('opacity') is not None else 1.0)
        if opacity < 1.0:
            surface.fill((255, 255, 255, int(255 * max(0.0, opacity))), special_flags=pygame.BLEND_RGBA_MULT)
        return surface

    def text(self, surface, text, rect, settings, units):
        '''
        A text in a rectangle of the surface : font, size (reduced if too wide), colour,
        position, offset, shadow
        '''
        import pygame
        if not text or float(settings.get('size') or 0) <= 0:
            return
        size = units.text(settings.get('size') or 0.045)
        path = self.font_path(settings.get('font'))
        color = self.color(settings.get('color'), (0, 0, 0))
        while True:
            font = self.screen.font(path, size)
            rendered = font.render(str(text), True, color[:3])
            if rendered.get_width() <= rect.width * 0.94 or size <= 6:
                break
            size = int(size * 0.9)
        position = str(settings.get('position') or 'center')
        anchor = ANCHORS.get(position, (0.5, 0.5))
        align = str(settings.get('align') or 'center')
        horizontal = {'left': 0.0, 'right': 1.0}.get(align, anchor[0]) if position in ('center', 'top', 'bottom') else anchor[0]
        margin = rect.height * 0.08
        offset = settings.get('offset') or [0, 0]
        pos_x = rect.x + margin + (rect.width - 2 * margin - rendered.get_width()) * horizontal + float(offset[0]) * rect.width
        pos_y = rect.y + margin + (rect.height - 2 * margin - rendered.get_height()) * anchor[1] + float(offset[1]) * rect.height
        if settings.get('shadow'):
            shade = font.render(str(text), True, (0, 0, 0))
            shade.set_alpha(150)
            surface.blit(shade, (int(pos_x) + max(1, size // 20), int(pos_y) + max(1, size // 20)))
        surface.blit(rendered, (int(pos_x), int(pos_y)))

    def button(self, key, style, size, text, icon, state, units):
        '''
        A button of this size in a state (normal, selected, disabled, pressed) : a surface
        with transparency, kept for the next times
        '''
        import pygame
        cache_key = (key, state, tuple(size), text, icon, repr(style))
        surface = self.surfaces.get(cache_key)
        if surface is not None:
            return surface
        values = self.state_style(style, state)
        width, height = size
        shape = str(values.get('shape') or 'rounded')
        radius = values.get('radius', 0.25)
        radius = height // 2 if shape == 'pill' else 0 if shape == 'rectangle' else \
            int(float(radius) * height) if float(radius) <= 1 else int(units.length(radius, 'y'))
        surface = pygame.Surface(size, pygame.SRCALPHA)
        if values.get('shadow') and shape != 'none':
            shade = pygame.Surface(size, pygame.SRCALPHA)
            pygame.draw.rect(shade, (0, 0, 0, 90), shade.get_rect(), border_radius=radius)
            surface.blit(shade, (max(2, height // 25), max(2, height // 25)))
        surface.blit(self.background(values.get('background'), size, radius, shape), (0, 0))
        border = values.get('border') or {}
        if int(border.get('width') or 0) > 0 and shape != 'none':
            pygame.draw.rect(surface, self.color(border.get('color'), (0, 0, 0)), surface.get_rect(),
                             width=int(border['width']), border_radius=radius)
        text_rect = pygame.Rect(0, 0, width, height)
        picture = self.image(icon) if icon else None
        if picture is not None:
            settings = values.get('icon') or {}
            side = int(min(width, height) * float(settings.get('size') or 0.7))
            position = str(settings.get('position') or 'left')
            box = pygame.Rect(0, 0, side, side)
            if position == 'top':
                box.midtop = (width // 2, int(height * 0.06))
                text_rect = pygame.Rect(0, box.bottom, width, height - box.bottom)
            elif position == 'center':
                box.center = (width // 2, height // 2)
            elif position == 'right':
                box.midright = (width - int(height * 0.1), height // 2)
                text_rect = pygame.Rect(0, 0, box.x, height)
            else:
                box.midleft = (int(height * 0.1), height // 2)
                text_rect = pygame.Rect(box.right, 0, width - box.right, height)
            surface.blit(self.fill_image(picture, box.size, {'fit': settings.get('fit') or 'contain'}), box.topleft)
        self.text(surface, text, text_rect, values.get('text') or {}, units)
        # Scale of the state (selected : larger) done once, and the format of the screen :
        # scaled and converted at each move, a button took 100 ms to draw on a Pi 3
        scale = self.scale_of(style, state)
        if scale != 1.0:
            surface = pygame.transform.smoothscale(surface, (max(1, int(width * scale)), max(1, int(height * scale))))
        surface = surface.convert_alpha()
        if len(self.surfaces) >= self.CACHE:
            self.surfaces.pop(next(iter(self.surfaces)))
        self.surfaces[cache_key] = surface
        return surface

    @staticmethod
    def scale_of(style, state):
        '''
        Scale of a button in a state (scale : 1.08 = 8 % larger, around its centre)
        '''
        values = merge(STYLE_DEFAULTS, style or {})
        if state in STATES:
            values = merge(values, values.get(state) or {})
        try:
            return max(0.5, min(2.0, float(values.get('scale') or 1.0)))
        except (TypeError, ValueError):
            return 1.0
