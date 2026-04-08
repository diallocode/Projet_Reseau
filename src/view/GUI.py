import pygame
import os
from model.Battlefield import Battlefield
from Constant import (
    ROWS, COLS, CELL_SIZE,RED, BLUE, DARK, GOLD, BLACK,
    IMAGE_FILES, BANNER_HEIGHT, BACKGROUND, VIEW_ELEVATION
)
from view.View import View
from util.Functions import elevation_color


class GUI(View):
    """
    Manages the Graphical User Interface (GUI) for the battle simulation using Pygame.
    Optimized for high-quality sprite rendering in zoom mode, incorporating a camera system
    and a minimap.
    """
    def __init__(self, battlefield: Battlefield, generaux, view_elevation=VIEW_ELEVATION):
        """
        Initializes the Pygame environment and assets.

        :param battlefield: The core simulation model containing units and generals.
        :type battlefield: Battlefield
        """
        self.battlefield = battlefield
        self.generaux = generaux # List of General
        self.winner = None
        self.pause = False
        self.show_info_panel = True
        self.view_elevation = view_elevation
        


        # Animation banners
        self.banner_anim_progress = [0.0, 0.0]
        self.banner_open_speed = 0.01

        # --- Initialize Pygame ---
        pygame.init()
        self.hp_font = pygame.font.SysFont(None, 18)
        info_object = pygame.display.Info()


        # --- World Map Dimensions ---
        self.map_w, self.map_h = COLS * CELL_SIZE , ROWS * CELL_SIZE

        # --- Display Window Dimensions (Fullscreen) ---

        self.screen_w = info_object.current_w - 80
        self.screen_h = info_object.current_h - 80

        # Creates the Pygame window at the physical screen size
        self.screen = pygame.display.set_mode((self.screen_w, self.screen_h))
        pygame.display.set_caption("Battlefield Simulation")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont(None, 24)

        # --- Load Background ---
        self.background = self.load_background()

        # --- Load Unit Sprites ---
        self.unit_images = self.load_unit_sprites()

        # --- Mini-map configuration ---
        self.minimap_w = self.map_w//20
        self.minimap_h = self.map_h//20
        self.minimap_border = 3
        self.minimap_x = self.screen_w - self.minimap_w - 10
        self.minimap_y = self.screen_h - self.minimap_h - 10

        # Camera configuration (zoom view)
        self.zoom_factor = 2.0  # Default zoom

        # Capture variables (initialized to center the camera)
        self.zoom_x = CELL_SIZE * COLS //2 - self.screen_w//(2*self.zoom_factor)
        self.zoom_y = CELL_SIZE * ROWS //2 - self.screen_h//(2*self.zoom_factor)
        # Minimap rendering variables (size of the area viewed by the camera)
        self.capture_w = self.screen_w
        self.capture_h = self.screen_h
        self.capture_x = self.zoom_x
        self.capture_y = self.zoom_y
        # Camera movement: minimap click/drag state
        self.minimap_dragging = False

    def load_background(self):
        """
        Loads and scales the background image to match the world map dimensions.

        :return: The scaled Pygame Surface for the background.
        :rtype: pygame.Surface
        """
        if self.view_elevation:
            surf = pygame.Surface((self.map_w, self.map_h))

            for r in range(ROWS):
                for c in range(COLS):
                    e = self.battlefield.heightmap[r][c]
                    color = elevation_color(e)
                    pygame.draw.rect(
                        surf,
                        color,
                        (c*CELL_SIZE, r*CELL_SIZE, CELL_SIZE, CELL_SIZE)
                    )
        else:
            path = os.path.dirname(__file__)
            bg_path = os.path.join(path, BACKGROUND)
            if os.path.exists(bg_path):
                bg = pygame.image.load(bg_path).convert()
                # The background is scaled to match the total map dimensions (e.g., 3600x3600)
                return pygame.transform.scale(bg, (self.map_w, self.map_h))
            surf = pygame.Surface((self.map_w, self.map_h))
            surf.fill((90, 200, 90))
        return surf



    def load_unit_sprites(self):
        """
        Loads and scales unit sprites to CELL_SIZE dimensions.

        :return: A dictionary mapping unit keys to their scaled Pygame Surface.
        :rtype: dict
        """
        path = os.path.dirname(__file__)
        images = {}
        for key, file in IMAGE_FILES.items():
            full_path = os.path.join(path, file)
            if os.path.exists(full_path):
                img = pygame.image.load(full_path).convert_alpha()
                # Original sprites are stored at CELL_SIZE
                img = pygame.transform.scale(img, (CELL_SIZE, CELL_SIZE))
                images[key] = img
        return images

    def draw_minimap(self):
        """
        Renders a miniature tactical map, showing unit positions and the camera's view frame.
        The map is scaled based on the world map dimensions.
        """

        # 1. Draw the minimap background and border
        pygame.draw.rect(self.screen, DARK, (self.minimap_x, self.minimap_y, self.minimap_w, self.minimap_h))
        pygame.draw.rect(self.screen, (0, 0, 0), (self.minimap_x, self.minimap_y, self.minimap_w, self.minimap_h),self.minimap_border)

        # Scale is the ratio between the minimap size and the actual map size
        scale_x = self.minimap_w / self.map_w
        scale_y = self.minimap_h / self.map_h

        # --- Draw units ---
        for unit in self.battlefield.troupes.values():
            color =DARK

            # Use unit ID to determine team color
            color = RED if unit.id < 1000 else BLUE

            if not unit.is_alive():
                continue

            # World coordinates (based on CELL_SIZE)
            ux = unit.position[1] * CELL_SIZE
            uy = unit.position[0] * CELL_SIZE

            # Minimap coordinates (World * Scale) + Minimap offset
            mx = self.minimap_x + int(ux * scale_x)
            my = self.minimap_y + int(uy * scale_y)

            # Draw the unit (3x3 pixel point)
            pygame.draw.rect(self.screen, color, (mx, my, 3, 3))

        # 2. Draw the camera rectangle (view frame)

        # Scale the capture area (which is in world coordinates) to the minimap scale
        zx = int(self.capture_x * scale_x)
        zy = int(self.capture_y * scale_y)
        zw = int(self.capture_w * scale_x)
        zh = int(self.capture_h * scale_y)

        # Draw the rectangle (view frame)
        pygame.draw.rect(
            self.screen,
            (255, 255, 0),  # Bright Yellow
            (self.minimap_x + zx, self.minimap_y + zy, zw, zh),
            2
        )

    # Camera movement: check if the mouse is inside the minimap
    def _is_in_minimap(self, x, y):
        return (
            self.minimap_x <= x <= self.minimap_x + self.minimap_w and
            self.minimap_y <= y <= self.minimap_y + self.minimap_h
        )

    # Camera movement: set camera position from minimap coordinates
    def _set_camera_from_minimap(self, mouse_x, mouse_y):
        # Convert minimap coords to world coords, then center the camera
        scale_x = self.minimap_w / self.map_w
        scale_y = self.minimap_h / self.map_h
        world_x = (mouse_x - self.minimap_x) / scale_x
        world_y = (mouse_y - self.minimap_y) / scale_y

        capture_w = int(self.screen_w / self.zoom_factor)
        capture_h = int(self.screen_h / self.zoom_factor)

        self.zoom_x = world_x - capture_w / 2
        self.zoom_y = world_y - capture_h / 2

    def draw_banner(self, surface, x, y, w, h, color, anim):
        """
        Draws an animated medieval-style banner with an optional tip.

        :param surface: The Pygame surface to draw on.
        :type surface: pygame.Surface
        :param x: X-coordinate of the banner's top-left corner.
        :type x: int
        :param y: Y-coordinate of the banner's top-left corner.
        :type y: int
        :param w: Width of the banner.
        :type w: int
        :param h: Full height of the banner.
        :type h: int
        :param color: The main RGB color of the banner.
        :type color: tuple
        :param anim: Animation progress factor (0.0 to 1.0).
        :type anim: float
        :param danger_level: Optional parameter for future color interpolation (currently unused).
        :type danger_level: float
        """

        animated_h = int(h * anim)

        pygame.draw.rect(surface, color, (x, y, w, animated_h))

        if anim > 0.6:
            tip_anim = (anim - 0.6) / 0.4
            tip_anim = min(max(tip_anim, 0), 1)

            tip_height = int(25 * tip_anim)

            pygame.draw.polygon(
                surface,
                color,
                [
                    (x, y + animated_h),
                    (x + w, y + animated_h),
                    (x + w // 2, y + animated_h + tip_height)
                ]
            )

        pygame.draw.rect(surface, GOLD, (x, y, w, animated_h), 4)
        if anim > 0.6:
            pygame.draw.polygon(
                surface,
                GOLD,
                [
                    (x, y + animated_h),
                    (x + w, y + animated_h),
                    (x + w // 2, y + animated_h + tip_height)
                ],
                4
            )

    def draw_text_shadow(self, surface, text, x, y, color):
        """
        Renders text with a black drop-shadow offset for better readability.

        :param surface: The Pygame surface to draw on.
        :type surface: pygame.Surface
        :param text: The text string to render.
        :type text: str
        :param x: X-coordinate for the text.
        :type x: int
        :param y: Y-coordinate for the text.
        :type y: int
        :param color: The main RGB color of the text.
        :type color: tuple
        """
        shadow = self.font.render(text, True, (0, 0, 0))
        surface.blit(shadow, (x + 2, y + 2))
        txt = self.font.render(text, True, color)
        surface.blit(txt, (x, y))


    def draw_info_panel(self):
        """
        Aggregates and renders the HUD info panels (Banners) for the Generals,
        displaying unit counts and animating the banner's opening.
        """
        banner_height = BANNER_HEIGHT
        banner_width = self.screen_w // 4
        margin = 10

        for i, g in enumerate(self.generaux[:2]):



            # Pick side and color
            if i == 0:
                base_x = margin
                color = (170, 40, 40)  # Red
            else:
                base_x = self.screen_w - banner_width - margin
                color = (40, 80, 180)  # Blue

            # Animate
            self.banner_anim_progress[i] = min(1.0, self.banner_anim_progress[i] + self.banner_open_speed)

            # Draw banner
            self.draw_banner(
                self.screen,
                base_x,
                margin,
                banner_width,
                banner_height,
                color,
                self.banner_anim_progress[i],
            )

            # Draw text only after banner partly opened
            if self.banner_anim_progress[i] > 0.4:
                x = base_x + 20
                y = margin + 10

                self.draw_text_shadow(self.screen, g.name + " : " + str(g.strategy), x, y, (255, 230, 200))

                unit_counts = {}
                for u in g.get_my_units(self.battlefield):
                    if u.is_alive():
                        unit_counts[u.name] = unit_counts.get(u.name, 0) + 1

                y += 30
                for unit_type, count in unit_counts.items():
                    self.draw_text_shadow(self.screen, f"{unit_type}: {count}", x, y, (255, 255, 255))
                    y += 18


    def draw_camera_view(self):
        """
        Renders the visible portion of the battlefield using a camera-based view.

        This method implements a strict camera system similar to RTS games:
        - Only the area of the map currently covered by the camera is rendered.
        - The camera view is defined by the zoom factor and the screen size.
        - The background is cropped to the camera rectangle before being scaled.
        - Units are rendered only if they are inside the camera's field of view.
        - The final camera surface is scaled to fill the entire screen.

        The method also clamps the camera position to ensure it never moves
        outside the bounds of the map, preventing any visual artifacts such
        as black borders or static background areas.

        Additionally, the camera capture coordinates and dimensions are updated
        for synchronization with the minimap rendering.

        Rendering steps:
            1. Compute the camera capture size based on zoom factor.
            2. Clamp camera position within map boundaries.
            3. Crop the background to the camera rectangle.
            4. Draw visible units relative to the camera.
            5. Scale the camera view to screen resolution.
            6. Update minimap capture variables.
        """
        capture_w = int(self.screen_w / self.zoom_factor)
        capture_h = int(self.screen_h / self.zoom_factor)

        capture_w = min(capture_w, self.map_w)
        capture_h = min(capture_h, self.map_h)

        max_x = self.map_w - capture_w
        max_y = self.map_h - capture_h

        self.zoom_x = max(0, min(self.zoom_x, max_x))
        self.zoom_y = max(0, min(self.zoom_y, max_y))

        camera_surface = pygame.Surface((capture_w, capture_h))

        camera_surface.blit(
            self.background,
            (0, 0),
            pygame.Rect(self.zoom_x, self.zoom_y, capture_w, capture_h)
        )

        for unit in self.battlefield.troupes.values():
            if not unit.is_alive():
                continue

            ux = unit.position[1] * CELL_SIZE
            uy = unit.position[0] * CELL_SIZE

            if (ux >= self.zoom_x and ux < self.zoom_x + capture_w and
                uy >= self.zoom_y and uy < self.zoom_y + capture_h):

                rel_x = ux - self.zoom_x
                rel_y = uy - self.zoom_y

                id = 1 if unit.id < 1000 else 2

                key = f"{unit.name}_{id}"
                if key in self.unit_images:
                    camera_surface.blit(
                        self.unit_images[key],
                        (rel_x, rel_y)
                    )

        scaled_view = pygame.transform.scale(
            camera_surface,
            (self.screen_w, self.screen_h)
        )

        self.screen.blit(scaled_view, (0, 0))

        self.capture_x = self.zoom_x
        self.capture_y = self.zoom_y
        self.capture_w = capture_w
        self.capture_h = capture_h


    def display_pause_overlay(self):
        """Displays a semi-transparent dark veil and the PAUSE text."""
        overlay = pygame.Surface((self.screen_w, self.screen_h))
        overlay.set_alpha(128)
        overlay.fill(BLACK)
        self.screen.blit(overlay, (0, 0))

        text = self.font.render("PAUSE", True, (255, 255, 255))
        rect = text.get_rect(center=(self.screen_w // 2, self.screen_h // 2))
        self.screen.blit(text, rect)

    def show_winner(self):
        """Displays the winner with a final message."""
        overlay = pygame.Surface((self.screen_w, self.screen_h))
        overlay.set_alpha(200)
        overlay.fill(BLACK)
        self.screen.blit(overlay, (0, 0))

        large_font = pygame.font.SysFont(None, 64)
        msg = f"Victory : {self.winner.name} : {self.winner.strategy} !"

        text_surf = large_font.render(msg, True, GOLD)
        text_rect = text_surf.get_rect(center=(self.screen_w // 2, self.screen_h // 2 - 20))
        self.screen.blit(text_surf, text_rect)

        sub_text = self.font.render("Press ESC to exit", True, (200, 200, 200))
        sub_rect = sub_text.get_rect(center=(self.screen_w // 2, self.screen_h // 2 + 40))
        self.screen.blit(sub_text, sub_rect)


    def show_info_pannel(self):
        """Sets the visibility of the top info panel to True."""
        self.show_info_panel = True

    def hide_info_pannel(self):
        """Sets the visibility of the top info panel to False."""
        self.show_info_panel = False

    def handle_events(self):
        """
        Processes keyboard inputs for camera movement (ZQSD), accelerated camera
        movement (SHIFT + ZQSD), and zoom control (M/N).

        The camera position (self.zoom_x, self.zoom_y) is updated based on
        keyboard input, allowing for faster navigation when a SHIFT key is held down.
        Zoom factor (self.zoom_factor) is also adjusted.
        Movement bounds (clamping) are applied within the draw_camera_view method.
        """
        keys = pygame.key.get_pressed()

        # Define base movement speed and accelerated speed
        base_speed = 10
        fast_speed = 40  # Faster speed

        # Check if the LEFT SHIFT or RIGHT SHIFT key is pressed
        is_shift_pressed = keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]

        # Determine the speed factor: fast if SHIFT is held, otherwise base speed
        speed_factor = fast_speed if is_shift_pressed else base_speed

        # ZQSD movement: Modifies the camera's top-left coordinates (self.zoom_x, self.zoom_y)
        if keys[pygame.K_z]:
            self.zoom_y -= speed_factor
        if keys[pygame.K_s]:
            self.zoom_y += speed_factor
        if keys[pygame.K_q]:
            self.zoom_x -= speed_factor
        if keys[pygame.K_d]:
            self.zoom_x += speed_factor

        # Zoom control: M (zoom in), N (zoom out)
        if keys[pygame.K_m]:
            # Increase zoom factor (up to max 10.0)
            self.zoom_factor = min(10.0, self.zoom_factor + 0.1)

        if keys[pygame.K_n]:
            # Decrease zoom factor (down to min 1.0)
            self.zoom_factor = max(1.0, self.zoom_factor - 0.1)

        # Camera movement: click/drag on minimap to move the camera
        mouse_x, mouse_y = pygame.mouse.get_pos()
        left_pressed = pygame.mouse.get_pressed(num_buttons=3)[0]
        if left_pressed and (self._is_in_minimap(mouse_x, mouse_y) or self.minimap_dragging):
            self.minimap_dragging = True
            self._set_camera_from_minimap(mouse_x, mouse_y)
        elif not left_pressed:
            self.minimap_dragging = False


    def update(self):
        """
        Main render loop called every frame to update the display.
        It calls draw_camera_view, draw_minimap, and overlay methods.
        """
        self.handle_events()
        #self.screen.blit(self.background, (0, 0))

        self.draw_camera_view()
        self.draw_minimap()

        if self.pause:
            self.display_pause_overlay()

        if self.winner is not None:
            self.show_winner()

        if self.show_info_panel:
            self.draw_info_panel()

        pygame.display.flip()

    def set_winner(self, winner_name: str):
        """
        Updates the game state to declare a winner and pauses the simulation.

        :param winner_name: The name of the winning general.
        :type winner_name: str
        """
        self.winner = winner_name
        self.pause = True

