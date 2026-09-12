import logging

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

import directus_client
from gpx import cumulative_distance_km, parse_gpx
from render import render_elevation_png, render_map_png

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("map-generator")

app = FastAPI()


class GenerateRequest(BaseModel):
    item_id: int


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/generate")
def generate(req: GenerateRequest):
    item_id = req.item_id

    try:
        item = directus_client.get_item(item_id)
    except Exception as exc:
        logger.exception("Failed to read itinerario %s from Directus", item_id)
        raise HTTPException(status_code=502, detail=f"Could not read itinerario {item_id}: {exc}") from exc

    traccia_gpx = item.get("traccia_gpx")
    if not traccia_gpx:
        raise HTTPException(status_code=422, detail=f"Itinerario {item_id} has no traccia_gpx")

    try:
        gpx_bytes = directus_client.download_asset(traccia_gpx)
        points = parse_gpx(gpx_bytes)
    except Exception as exc:
        logger.exception("Failed to parse GPX for itinerario %s", item_id)
        raise HTTPException(status_code=422, detail=f"Could not parse GPX for itinerario {item_id}: {exc}") from exc

    distances_km = cumulative_distance_km(points)

    try:
        map_png = render_map_png(points)
        elevation_png = render_elevation_png(distances_km, points)
    except Exception as exc:
        logger.exception("Failed to render images for itinerario %s", item_id)
        raise HTTPException(status_code=500, detail=f"Could not render images for itinerario {item_id}: {exc}") from exc

    for old_file_id in (item.get("mappa_statica"), item.get("profilo_altimetrico")):
        if old_file_id:
            try:
                directus_client.delete_file(old_file_id)
            except Exception:
                logger.warning("Failed to delete previous file %s for itinerario %s", old_file_id, item_id)

    try:
        mappa_id = directus_client.upload_file(f"itinerario-{item_id}-mappa.png", map_png)
        profilo_id = directus_client.upload_file(f"itinerario-{item_id}-profilo.png", elevation_png)
        directus_client.patch_item(item_id, {"mappa_statica": mappa_id, "profilo_altimetrico": profilo_id})
    except Exception as exc:
        logger.exception("Failed to save generated images for itinerario %s", item_id)
        raise HTTPException(
            status_code=502, detail=f"Could not save generated images for itinerario {item_id}: {exc}"
        ) from exc

    logger.info("Generated map/elevation images for itinerario %s", item_id)
    return {"mappa_statica": mappa_id, "profilo_altimetrico": profilo_id}
