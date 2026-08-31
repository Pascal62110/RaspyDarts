#!/usr/bin/env python3
"""
Test minimal du tactile sous pygame/SDL, independant de RaspyDarts.
Touche l'ecran : chaque evenement recu est affiche dans le terminal.
Appuie sur ECHAP (clavier) ou ferme la fenetre pour quitter.
"""
import os
import pygame

print("SDL_VIDEODRIVER =", os.environ.get("SDL_VIDEODRIVER", "(non defini)"))
pygame.init()
print("pygame:", pygame.ver, "SDL:", pygame.get_sdl_version())
print("Drivers video dispo:", pygame.display.get_driver())

screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
print("Pilote video reellement utilise:", pygame.display.get_driver())
print("Resolution:", screen.get_size())
print("Nombre de peripheriques tactiles vus par SDL:")
try:
    print("  get_num_touch_devices ->", pygame.touch.get_num_devices())
except Exception as e:
    print("  (pygame.touch indisponible:", e, ")")

print("\n>>> Touche l'ecran maintenant. ECHAP pour quitter.\n")
font = pygame.font.Font(None, 48)
last = "En attente d'un evenement..."

running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            running = False
        elif event.type in (pygame.FINGERDOWN, pygame.FINGERUP, pygame.FINGERMOTION):
            last = f"TACTILE {pygame.event.event_name(event.type)} x={event.x:.3f} y={event.y:.3f}"
            print(last)
        elif event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
            last = f"SOURIS {pygame.event.event_name(event.type)} pos={event.pos} bouton={event.button}"
            print(last)
        elif event.type == pygame.MOUSEMOTION:
            # trop verbeux pour le terminal, on l'affiche juste a l'ecran
            last = f"SOURIS MOTION pos={event.pos}"

    screen.fill((20, 20, 30))
    img = font.render(last, True, (255, 255, 255))
    screen.blit(img, (40, 40))
    pygame.display.flip()

pygame.quit()
