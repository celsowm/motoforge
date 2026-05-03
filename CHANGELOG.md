# Changelog

## 0.0.3

- Adicionado preset `streetfighter` com postura naked/agressiva.
- Adicionado `--seed` e `--variant-strength` para variações determinísticas de proporção.
- Adicionado `--collision none|simple|detailed` com proxies nomeados `UCX_*` para uso em engines.
- Adicionado `--lods` para exportar `LOD0`, `LOD1` e `LOD2` como arquivos `.glb` separados.
- Adicionados espelhos, piscas, placa, dashboard, radiador, suspensões traseiras e decals geométricos.
- Adicionado comando `motoforge batch` para gerar múltiplas motos a partir de um JSON.
- Adicionado comando `motoforge presets` para listar presets sem abrir Blender.
- Manifest atualizado para `schema_version: 2` com metadados de pipeline de game.
- Validador atualizado para conferir partes novas e proxies de colisão.

## 0.0.2

- Adicionado preset `sport_bike` com rabeta mais alta, guidão baixo, carenagens laterais, nose cowl e windscreen.
- Adicionado `--detail low|medium|high`.
- Adicionado `--style realistic_lowpoly|stylized|cyberpunk|cartoon`.
- Adicionado `--silhouette cafe|scrambler|sporty|dirt|chopper`.
- Adicionado `--wheel-detail none|spokes|alloy`.
- Rodas ganharam blocos de pneu, calipers, discos com vents e opção de raios/alloy.
- Adicionados corrente/correia visual e links laterais.
- Adicionado carregamento por JSON com `--config`.
- Adicionado render automático de preview `.png`.
- Adicionado manifest `.json` com versão, opções, materiais, partes e estatísticas básicas.
- Adicionado `motoforge validate`.

## 0.0.1

- Primeira versão do app MotoForge.
- Gerador procedural Blender/Python para moto low-poly.
- Presets: `cafe_racer`, `dirt_bike`, `cyber_scrambler`.
- Exportação GLB via `bpy.ops.export_scene.gltf`.
- Wrapper CLI `motoforge`.
