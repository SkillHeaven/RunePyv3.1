# RunePy

RunePy is a small demonstration project built with [Panda3D](https://www.panda3d.org/). The code creates a grid of tiles and lets a simple character move across the map using A* pathfinding. It provides a basic camera and control system to experiment with Panda3D's API.

## Features

- Tile-based world generated at runtime
- Character model that moves to the clicked tile
- Top‑down camera with zoom controls
- Debug overlay displaying tile information
- Simple collision and ray casting
- Camera zoom limits keep the view between a minimum and maximum height
- Built-in map editor with hotkeys for saving and loading maps
- Tiles support custom metadata loaded from map files
- Individual tiles darken slightly when hovered to show the current mouse
  position

## Repository Layout

| File | Description |
|------|-------------|
| `runepy/client.py` | Entry point that opens the window. |
| `runepy/world.py` | Map generation logic. |
| `runepy/map_editor.py` | Utilities for editing tiles. |
| `runepy/character.py` | Represents the player model and movement logic. |
| `runepy/camera.py` | Manages the camera position and orientation. |
| `runepy/controls.py` | Handles mouse wheel zooming and other input bindings. |
| `runepy/collision.py` | Utilities for ray casting with Panda3D's collision system. |
| `runepy/pathfinding.py` | Implementation of a basic A* search with optional weighted costs and movement patterns. |
| `runepy/debuginfo.py` | Draws onscreen debug text such as mouse and tile coordinates. |
| `runepy/utils.py` | Shared helpers like `get_mouse_tile_coords`. |

## Requirements

- Python 3
- [Panda3D](https://www.panda3d.org/) 1.10 or newer

Install Panda3D using `pip` if it is not already available:

```bash
pip install panda3d
```

## Running the example

After installing the requirements, launch the program using one of the following commands:

**Windows PowerShell**
```powershell
./run.ps1
```

**Direct Python**
```bash
python -m runepy
```

To launch the map editor instead of the game, run:

```bash
python -m runepy --mode editor
```

A window will open containing a grid of tiles. Clicking on a tile moves the smiley‑face character to that location using pathfinding. Use the mouse wheel to zoom the camera in or out.

Zooming is always handled by the mouse wheel and cannot be changed. In the editor the camera pans up/down with ``W`` and ``S`` while the ``A`` and ``D`` keys for left/right movement remain rebindable.

Press ``Esc`` in either mode to open an options menu where you can rebind the available controls, including the editor's side movement and save/load shortcuts. When this menu is visible, gameplay clicks are ignored so you can't interact with the world through the menu.

## Configuration

Default key bindings are defined in ``config.json`` at the repository root. Edit this file to customize the controls that are initially loaded by both the game and the editor.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

## Numeric map layers

`array_map.py` contains a `RegionArrays` helper for storing map data in
efficient `numpy` arrays. Each layer (height, terrain, overlay and collision)
is saved to a single `.npz` archive:

```python
from runepy.array_map import RegionArrays

region = RegionArrays.empty((64, 64))
region.save("region_01.npz")
loaded = RegionArrays.load("region_01.npz")
```



## Utilities

`utils.py` contains small helper functions used throughout the project. In particular
`get_mouse_tile_coords` and `get_tile_from_mouse` translate the mouse position into
tile coordinates using the camera and render nodes. Pass the current camera and
`render` root when calling these helpers.

## Tests

Run the test suite with `pytest -q` from the repository root:

```bash
pytest -q
```

All tests should pass. There are currently four tests covering the A* pathfinding
implementation including optional movement offsets and weighted tiles.
