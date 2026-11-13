# que-estudiar-ig-media

Publicador en la nube de @que.estudiar.argentina.
- La Mac (~/.que-estudiar-bot/guardian.py) sube cada reel de la cola a `reels/` y su ficha a `cola/`.
- GitHub Actions (`.github/workflows/publicar.yml`) publica el primero de `cola/` a las 12:30 y 20:00 (hora argentina) y lo pasa a `publicados/`.
- Para volver a publicar desde la Mac: en guardian.py poner `NUBE = False`.
