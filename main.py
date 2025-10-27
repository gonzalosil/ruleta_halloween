# main.py
import math, pygame
from config import *
from wheel import Wheel

def main():
    pygame.init()
    flags = pygame.FULLSCREEN if FULLSCREEN else 0
    screen = pygame.display.set_mode((WIDTH, HEIGHT), flags)
    pygame.display.set_caption("Ruleta Halloween – 7 segmentos")

    clock = pygame.time.Clock()
    wheel = Wheel(screen)
    running = True

    while running:
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                running = False
            elif e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    running = False
                elif e.key == pygame.K_SPACE and not wheel.is_spinning:
                    wheel.start_spin()

                # --- Calibración en vivo ---
                elif e.key == pygame.K_c:
                    wheel.show_calib = not wheel.show_calib
                elif e.key == pygame.K_r:
                    wheel.image_offset = 0.0
                    wheel.pointer_offset = 0.0
                    wheel.rebuild_labels()
                elif e.key == pygame.K_LEFT:
                    wheel.adjust_image_offset(-math.radians(1))   # reconstruye capa
                elif e.key == pygame.K_RIGHT:
                    wheel.adjust_image_offset(+math.radians(1))   # reconstruye capa
                elif e.key == pygame.K_UP:
                    wheel.adjust_pointer_offset(+math.radians(1))
                elif e.key == pygame.K_DOWN:
                    wheel.adjust_pointer_offset(-math.radians(1))

        wheel.update()
        wheel.draw()

        # Hint inferior
        font = pygame.font.SysFont("Arial", 22)
        hint = "ESPACIO=Girar  •  C=Calibración  •  ←/→ imagen  •  ↑/↓ puntero  •  R=Reset  •  ESC=Salir"
        text = font.render(hint, True, TEXT_COLOR)
        screen.blit(text, text.get_rect(midbottom=(WIDTH//2, HEIGHT-10)))

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()

if __name__ == "__main__":
    main()
