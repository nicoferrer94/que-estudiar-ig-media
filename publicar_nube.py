#!/usr/bin/env python3
"""Publicador en la nube de @que.estudiar.argentina (lo corre GitHub Actions cada 15 min cerca de cada horario).

Horarios: 12:30 y 20:00 hora argentina (UTC-3). Si GitHub se atrasa, recupera el horario hasta 3 h después.
Cola: cola/<NN-nombre>.json = {"video": "reels/<archivo>.mp4", "caption": "...", "thumb_offset": "3800"}
      (la sube la Mac; se publica en orden alfabético).
Al publicar: mueve el json a publicados/ con el link, y anota el horario en estado.json. El workflow hace el commit.
Secretos: IG_ACCESS_TOKEN, IG_USER_ID.  Prueba sin publicar: DRY_RUN=1.
"""
import datetime, json, os, sys, time, urllib.error, urllib.parse, urllib.request

G = "https://graph.facebook.com/v26.0"
RAW = "https://raw.githubusercontent.com/nicoferrer94/que-estudiar-ig-media/main/"
HORAS = ["12:30", "20:00"]
RECUPERA = datetime.timedelta(hours=3)
ART = datetime.timezone(datetime.timedelta(hours=-3))
TOKEN, USER = os.environ["IG_ACCESS_TOKEN"], os.environ["IG_USER_ID"]
DRY = os.environ.get("DRY_RUN") == "1"


def call(path, data=None):
    req = urllib.request.Request(f"{G}/{path}", data=None if data is None else urllib.parse.urlencode(data).encode(),
                                 headers={"Authorization": "Bearer " + TOKEN})
    try:
        return json.loads(urllib.request.urlopen(req, timeout=120).read())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"{e.code} {e.read()[:400]!r}")


def slot_pendiente(est):
    now = datetime.datetime.now(ART)
    for d in (now.date() - datetime.timedelta(days=1), now.date()):
        for h in HORAS:
            slot = datetime.datetime.combine(d, datetime.time(*map(int, h.split(":"))), ART)
            k = slot.strftime("%Y-%m-%dT%H:%M")
            if k not in est["hechos"] and slot <= now < slot + RECUPERA:
                return k
    return None


def main():
    est = json.load(open("estado.json")) if os.path.exists("estado.json") else {"hechos": []}
    k = os.environ.get("FORZAR_HORARIO") or slot_pendiente(est)
    if not k:
        print("nada que publicar ahora"); return
    cola = sorted(f for f in os.listdir("cola") if f.endswith(".json"))
    if not cola:
        print(f"horario {k}: la cola está vacía"); sys.exit(1)
    nombre = cola[0]; item = json.load(open(f"cola/{nombre}"))
    url = RAW + item["video"]
    print(f"horario {k}: {nombre} → {url}")
    if DRY:
        print(urllib.request.urlopen(urllib.request.Request(url, method="HEAD"), timeout=60).headers.get("Content-Length"), "bytes; caption:", item["caption"][:80])
        return
    p = {"media_type": "REELS", "video_url": url, "caption": item["caption"], "share_to_feed": "true"}
    if item.get("thumb_offset"): p["thumb_offset"] = item["thumb_offset"]
    for intento in range(1, 4):
        c = call(f"{USER}/media", p)
        for _ in range(90):
            s = call(f"{c['id']}?fields=status_code,status")
            if s.get("status_code") in ("FINISHED", "ERROR", "EXPIRED"): break
            time.sleep(10)
        if s.get("status_code") == "FINISHED": break
        print(f"contenedor {c['id']} en {s} (intento {intento})"); time.sleep(30)
    else:
        sys.exit(f"no se pudo procesar {nombre}")
    pub = call(f"{USER}/media_publish", {"creation_id": c["id"]})
    info = call(f"{pub['id']}?fields=permalink,timestamp")
    print(f"publicado {nombre} → {info.get('permalink')}")
    item.update(horario=k, media_id=pub["id"], permalink=info.get("permalink"), publicado=info.get("timestamp"))
    json.dump(item, open(f"publicados/{nombre}", "w"), ensure_ascii=False, indent=1)
    os.remove(f"cola/{nombre}")
    est["hechos"].append(k); json.dump(est, open("estado.json", "w"), indent=1)


if __name__ == "__main__":
    main()
