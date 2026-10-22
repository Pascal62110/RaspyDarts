# -*- coding: utf-8 -*-
'''
Emojis in the texts drawn by pygame : drawn with the colour emoji font (Noto Color Emoji,
package fonts-noto-color-emoji) at the height of the text. Without this font they are left out
(the fonts of the game have none of them : they were shown as squares)
'''
import os

import pygame

EMOJI_FONT = '/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf'
# Its only size : its emojis are pictures of this size, scaled to the height of the text
EMOJI_SIZE = 109
# Joiners of the emojis (variation selector, zero width joiner) : not drawn alone
JOINERS = ('️', '‍')

_font = None


def is_emoji(char):
    '''
    An emoji (pictographs, symbols, dingbats, arrows and stars)
    '''
    code = ord(char)
    return code >= 0x1F000 or 0x2600 <= code <= 0x27BF or 0x2B00 <= code <= 0x2BFF


def emoji_font():
    '''
    The emoji font, None if it is not installed
    '''
    global _font
    if _font is None:
        try:
            _font = pygame.font.Font(EMOJI_FONT, EMOJI_SIZE) if os.path.isfile(EMOJI_FONT) else False
        except Exception:    # pylint: disable=broad-except
            _font = False
    return _font or None


def render(font, text, color):
    '''
    The text in this font and colour, its emojis in colour at its height (left out without the
    emoji font)
    '''
    text = ''.join(char for char in str(text) if char not in JOINERS)
    if not any(is_emoji(char) for char in text):
        return font.render(text, True, color)
    emojis = emoji_font()
    if emojis is None:
        return font.render(' '.join(''.join(char for char in text if not is_emoji(char)).split()), True, color)
    # Runs of text and of emojis, side by side
    runs = []
    for char in text:
        kind = is_emoji(char)
        if runs and runs[-1][0] == kind:
            runs[-1][1] += char
        else:
            runs.append([kind, char])
    height = font.get_height()
    parts = []
    for kind, chunk in runs:
        if kind:
            picture = emojis.render(chunk, True, (255, 255, 255))
            width = max(1, round(picture.get_width() * height / picture.get_height()))
            parts.append(pygame.transform.smoothscale(picture, (width, height)))
        else:
            parts.append(font.render(chunk, True, color))
    surface = pygame.Surface((sum(part.get_width() for part in parts), max(part.get_height() for part in parts)),
                             pygame.SRCALPHA)
    pos_x = 0
    for part in parts:
        surface.blit(part, (pos_x, (surface.get_height() - part.get_height()) // 2))
        pos_x += part.get_width()
    return surface
