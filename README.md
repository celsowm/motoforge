# MotoForge 0.0.3

MotoForge é um gerador procedural de motos em Python para Blender, pensado para protótipos de games. Ele cria uma moto low-poly/stylized com partes nomeadas, materiais separados, preview, manifest e exportação GLB.

A ideia é usar Blender como ferramenta de modelagem procedural e importar o `.glb` resultante em Three.js, Godot, Unity ou Unreal.

## Requisitos

- Python 3.10+
- Blender instalado e disponível como `blender` no PATH, ou `BLENDER_PATH=/caminho/para/blender`

## Instalação local

```bash
pip install -e .
```

## Gerar uma moto

Via Blender diretamente:

```bash
blender --background --python src/motoforge/blender_entry.py -- \
  --preset streetfighter \
  --style realistic_lowpoly \
  --detail high \
  --seed 42 \
  --variant-strength 0.35 \
  --collision detailed \
  --output dist/streetfighter.glb
```

Via CLI:

```bash
motoforge --preset sport_bike --detail high --style cyberpunk --output dist/sport.glb
```

## Gerar LODs

```bash
motoforge --config examples/streetfighter_lods.json
```

Isso gera arquivos parecidos com:

```text
dist/streetfighter_lods_lod0.glb
dist/streetfighter_lods_lod1.glb
dist/streetfighter_lods_lod2.glb
```

Cada LOD também recebe preview e manifest próprios, a menos que `preview` ou `manifest` sejam definidos como string vazia.

## Config JSON

```json
{
  "preset": "streetfighter",
  "output": "dist/streetfighter_lods.glb",
  "detail": "high",
  "style": "realistic_lowpoly",
  "silhouette": "streetfighter",
  "wheelDetail": "alloy",
  "collision": "detailed",
  "lods": true,
  "seed": 42,
  "variantStrength": 0.35,
  "primaryColor": "#111111",
  "accentColor": "#d7ff2f"
}
```

## Presets

```bash
motoforge presets
```

Disponíveis na v0.0.3:

- `cafe_racer`
- `cyber_scrambler`
- `dirt_bike`
- `sport_bike`
- `streetfighter`

## Geração em lote

```bash
motoforge batch examples/batch_variants.json
```

O formato do batch é:

```json
{
  "defaults": {
    "style": "realistic_lowpoly",
    "detail": "medium",
    "collision": "simple"
  },
  "jobs": [
    { "preset": "streetfighter", "output": "dist/streetfighter_a.glb", "seed": 101, "variantStrength": 0.25 },
    { "preset": "sport_bike", "output": "dist/sport_b.glb", "seed": 202, "variantStrength": 0.30 }
  ]
}
```

## Validação

```bash
motoforge validate dist/streetfighter_lods_lod0.glb
```

O validador checa se o `.glb` existe, se o manifest existe, se a versão bate, se partes principais aparecem e se há proxies de colisão quando `collision` está habilitado.

## Novidades da v0.0.3

- variações determinísticas por seed
- preset `streetfighter`
- LOD set export
- proxies de colisão `UCX_*`
- espelhos, piscas, placa, dashboard, radiador, suspensões e decals
- batch generation
- manifest schema v2 com metadados de pipeline

## Observação

O projeto gera geometria procedural simples, não substitui modelagem manual high-end. O objetivo é produzir uma base menos infantil e mais editável para prototipagem rápida.
