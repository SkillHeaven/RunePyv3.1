from panda3d.core import ModifierButtons, Vec3
try:
    import direct.showbase.ShowBaseGlobal as sbg
except Exception:  # pragma: no cover - Panda3D may be missing
    sbg = None
from runepy.utils import get_mouse_tile_coords, get_tile_from_mouse
from direct.interval.IntervalGlobal import Sequence, Func
import math
import argparse

from runepy.base_app import BaseApp

from runepy.character import Character
from runepy.debuginfo import DebugInfo
from runepy.camera import CameraControl
from runepy.controls import Controls
from runepy.world import World
from constants import REGION_SIZE, VIEW_RADIUS
from runepy.pathfinding import a_star
from runepy.collision import CollisionControl
from runepy.options_menu import KeyBindingManager, OptionsMenu
from runepy.loading_screen import LoadingScreen
from runepy.debug import get_debug
from runepy.config import load_state, save_state
import atexit


class Client(BaseApp):
    """Application entry point that opens the game window."""

    def __init__(self, debug=False):
        self.debug = debug
        super().__init__()
        atexit.register(self._save_state)

    def initialize(self):
        """Perform heavy initialization for the game mode."""
        self.debug_info = DebugInfo()

        self.mouseWatcherNode.set_modifier_buttons(ModifierButtons())
        self.buttonThrowers[0].node().set_modifier_buttons(ModifierButtons())

        self.loading_screen.update(20, "Generating world")
        def world_progress(frac, text):
            self.loading_screen.update(20 + int(30 * frac), text)

        view_radius = VIEW_RADIUS
        world_radius = view_radius * REGION_SIZE
        self.world = World(
            self.render,
            radius=world_radius,
            debug=self.debug,
            progress_callback=world_progress,
            view_radius=view_radius,
        )

        tile_fit_scale = self.world.tile_size * 0.5
        self.loading_screen.update(50, "Loading character")
        self.character = Character(self.render, self.loader, Vec3(0, 0, 0.5), scale=tile_fit_scale, debug=self.debug)
        if sbg is not None and hasattr(sbg, "base"):
            sbg.base.world = self.world
            sbg.base.character = self.character
        self.camera_control = CameraControl(self.camera, self.render, self.character)
        state = load_state()
        char_pos = state.get("character_pos")
        if isinstance(char_pos, list) and len(char_pos) == 3:
            self.character.model.setPos(*char_pos)
        cam_h = state.get("camera_height")
        if cam_h is not None:
            self.camera.setZ(cam_h)
            self.camera_control.update_camera_focus()
        self.controls = Controls(self, self.camera_control, self.character)
        self.collision_control = CollisionControl(self.camera, self.render)
        self.key_manager = KeyBindingManager(self, {"open_menu": "escape"})
        self.options_menu = OptionsMenu(self, self.key_manager)
        self.key_manager.bind("open_menu", self.options_menu.toggle)

        self.accept("mouse1", self.tile_click_event)
        self.accept("f3", self.debug_info.toggle_region_info)

        self.loading_screen.update(80, "Finalizing")

        # Set a pleasant sky blue background
        self.setBackgroundColor(0.53, 0.81, 0.92)
        if cam_h is None:
            self.camera.setPos(0, 0, 10)
        self.camera.lookAt(0, 0, 0)

        self.taskMgr.add(self.update_tile_hover, "updateTileHoverTask")

    def log(self, *args, **kwargs):
        if self.debug:
            print(*args, **kwargs)

    def update_tile_hover(self, task):
        mpos, tile_x, tile_y = get_mouse_tile_coords(
            self.mouseWatcherNode, self.camera, self.render
        )
        if mpos:
            self.debug_info.update_tile_info(mpos, tile_x, tile_y)
            if -self.world.radius <= tile_x <= self.world.radius and -self.world.radius <= tile_y <= self.world.radius:
                self.world.highlight_tile(tile_x, tile_y)
            else:
                self.world.clear_highlight()
        else:
            self.world.clear_highlight()
        return task.cont


    def tile_click_event(self):
        if self.options_menu.visible:
            return
        self.log("Tile clicked!")
        if self.mouseWatcherNode.hasMouse():
            mpos = self.mouseWatcherNode.getMouse()
            tile_x, tile_y = get_tile_from_mouse(
                self.mouseWatcherNode, self.camera, self.render
            )
            self.log(f"Mouse position detected: {mpos}")
            self.log(f"Clicked tile coords: {(tile_x, tile_y)}")
        else:
            self.log("No mouse detected.")
            return

        self.camera.setH(0)
        self.collision_control.update_ray(self.camNode, mpos)
        self.log("Before traversing for collisions...")
        self.collision_control.traverser.traverse(self.render)
        self.log("After traversing for collisions.")

        collided_obj, pickedPos = self.collision_control.get_collided_object(self.render)

        if collided_obj:
            self.log("Collided with:", collided_obj.getName())

            snapped_x = round(pickedPos.getX())
            snapped_y = round(pickedPos.getY())
            target_pos = Vec3(snapped_x, snapped_y, 0.5)

            if (self.character.get_position() - target_pos).length() > 0.1:
                # Stop any ongoing movement so the path starts from the exact current position
                self.character.cancel_movement()
                current_pos = self.character.get_position()
                current_x, current_y = int(current_pos.getX()), int(current_pos.getY())

                stitched, off_x, off_y = self.world.walkable_window(current_x, current_y)
                start_idx = (current_x - off_x, current_y - off_y)
                end_idx = (snapped_x - off_x, snapped_y - off_y)

                path = a_star(stitched.tolist(), start_idx, end_idx)
                self.log("Calculated Path:", path)

                if path:
                    # Skip the starting tile so movement begins from the
                    # character's actual position without resetting to the
                    # rounded tile coordinate.
                    if path and path[0] == start_idx:
                        path = path[1:]

                    if not path:
                        self.log("Already at destination")
                        return

                    intervals = []
                    prev_world_x, prev_world_y = current_pos.getX(), current_pos.getY()
                    for step in path:
                        world_x = step[0] + off_x
                        world_y = step[1] + off_y
                        self.log(f"Moving character to {(world_x, world_y)}")
                        distance = math.sqrt((world_x - prev_world_x) ** 2 + (world_y - prev_world_y) ** 2)
                        duration = distance / self.character.speed
                        move_interval = self.character.move_to(Vec3(world_x, world_y, 0.5), duration)
                        intervals.append(move_interval)
                        prev_world_x, prev_world_y = world_x, world_y

                    move_sequence = Sequence(*intervals, Func(self.camera_control.update_camera_focus))
                    self.character.start_sequence(move_sequence)
                    self.log(f"Moved to {(world_x, world_y)}")

                self.log(f"After Update: Camera Hpr: {self.camera.getHpr()}")
                self.log(f"After Update: Character Pos: {self.character.get_position()}")

        self.collision_control.cleanup()

    # ------------------------------------------------------------------
    # Editor helpers
    # ------------------------------------------------------------------
    def save_map(self, filename="map.json"):
        """Save the current world grid to ``filename``."""
        self.editor.save_map()
        print(f"Map saved to {filename}")

    def load_map(self, filename="map.json"):
        """Load a map from ``filename`` and rebuild the world."""
        self.editor.load_map()
        # World size may change during map load but pathfinding now stitches
        # regions dynamically so no cached grid is needed.
        print(f"Map loaded from {filename}")

    # ------------------------------------------------------------------
    # State persistence
    # ------------------------------------------------------------------
    def _save_state(self):
        """Save camera height and character position."""
        if not hasattr(self, "character"):
            return
        state = {
            "camera_height": float(self.camera.getZ()),
            "character_pos": [
                float(self.character.model.getX()),
                float(self.character.model.getY()),
                float(self.character.model.getZ()),
            ],
        }
        save_state(state)



def main(args=None):
    """Entry point for the ``runepy`` console script."""
    parser = argparse.ArgumentParser(description="RunePy client")
    parser.add_argument(
        "--mode",
        choices=["game", "editor"],
        default="game",
        help="Start in regular game mode or map editor",
    )
    parsed = parser.parse_args(args)

    if parsed.mode == "editor":
        from runepy.editor_window import EditorWindow

        app = EditorWindow()
    else:
        app = Client()

    from runepy.debug import get_debug
    get_debug().attach(app)

    app.run()


if __name__ == "__main__":
    main()

__all__ = ["Client", "main"]
