# Prompting notes for MotoForge

Use terms that describe **asset pipeline constraints**, not just visual vibe.

Better:

> Generate a streetfighter motorcycle, game-ready low-poly, readable silhouette, named parts, collision proxies, LODs, deterministic seed, separated materials, GLB export.

Avoid:

> Make a cool 3D motorcycle.

Good config dimensions to control:

- `preset`: base motorcycle family
- `silhouette`: extra posture bias
- `style`: material/shape language
- `detail`: segment count and visual density
- `seed`: deterministic variation
- `variantStrength`: safe proportion variation
- `collision`: none/simple/detailed
- `lods`: export multiple detail levels

For less toy-like results, prefer:

```json
{
  "preset": "streetfighter",
  "style": "realistic_lowpoly",
  "detail": "high",
  "collision": "detailed",
  "seed": 42,
  "variantStrength": 0.35
}
```
