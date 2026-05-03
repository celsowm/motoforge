#!/usr/bin/env python
"""Simple GLB viewer using pyvista (VTK) - more reliable on Windows."""

import sys
from pathlib import Path

import pyvista as pv


def main():
    if len(sys.argv) < 2:
        print(f"Usage: python {sys.argv[0]} <file.glb>")
        sys.exit(1)

    filepath = Path(sys.argv[1])
    if not filepath.exists():
        print(f"File not found: {filepath}")
        sys.exit(1)

    print(f"Loading: {filepath}")
    data = pv.read(str(filepath))

    pv.set_plot_theme("document")
    plotter = pv.Plotter(title=str(filepath.name), window_size=(1280, 720))

    if isinstance(data, pv.MultiBlock):
        print(f"Loaded scene with {len(data)} blocks")
        merged = data.combine()
        plotter.add_mesh(merged, color="lightgray", show_edges=True, line_width=0.5)
    else:
        print(f"Loaded mesh with {data.n_points} points, {data.n_cells} cells")
        plotter.add_mesh(data, color="lightgray", show_edges=True, line_width=0.5)

    plotter.add_axes()
    plotter.show_grid()
    plotter.enable_anti_aliasing()
    plotter.show()


if __name__ == "__main__":
    main()
