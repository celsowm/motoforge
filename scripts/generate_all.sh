#!/usr/bin/env bash
set -euo pipefail

BLENDER_BIN="${BLENDER_PATH:-blender}"

"$BLENDER_BIN" --background --python src/motoforge/blender_entry.py -- --config examples/sport_bike.json
"$BLENDER_BIN" --background --python src/motoforge/blender_entry.py -- --config examples/cyber_scrambler_high.json
"$BLENDER_BIN" --background --python src/motoforge/blender_entry.py -- --config examples/streetfighter_lods.json

python -m motoforge batch examples/batch_variants.json --blender "$BLENDER_BIN"
