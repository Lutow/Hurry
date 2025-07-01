from fastapi import APIRouter, HTTPException
import requests
import json
from unidecode import unidecode
from starlette.responses import JSONResponse

import logging

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s | %(levelname)s | %(message)s",
    filename="app.log",  # <--- Fichier de log
    filemode="a",  # "a" pour ajouter à la fin, "w" pour écraser à chaque run
    encoding="utf-8"  # Pour éviter les erreurs d'encodage
)

logger = logging.getLogger(__name__)

router = APIRouter()

API_KEY = "Va2ayuXTn1wEGJuQCFSGmLxRh5kOsKUm"


def normalize(s: str) -> str:
    return unidecode(s or "").strip().upper()


def fetch_ratp_disruptions(api_key):
    url = "https://prim.iledefrance-mobilites.fr/marketplace/disruptions_bulk/disruptions/v2"
    headers = {
        "accept": "application/json",
        "apiKey": api_key
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Verifie si la requête a reussi
        return response.json()  # Retourne les donnees JSON de la reponse
    except requests.exceptions.RequestException as e:
        logger.error(f"An error occurred: {e}")
        return None


def filter_metro_rer(data: dict) -> dict:
    disruptions = data.get("disruptions", [])
    lines = data.get("lines", [])

    allowed_modes = {"METRO", "RER"}

    allowed_disruption_ids = set()
    allowed_line_ids = set()

    for line in lines:
        mode = normalize(line.get("mode"))
        if mode in allowed_modes:
            allowed_line_ids.add(line["id"])
            for obj in line.get("impactedObjects", []):
                for did in obj.get("disruptionIds", []):
                    allowed_disruption_ids.add(did)

    filtered_disruptions = [d for d in disruptions if d["id"] in allowed_disruption_ids]
    filtered_lines = [l for l in lines if l["id"] in allowed_line_ids]

    return {
        "disruptions": filtered_disruptions,
        "lines": filtered_lines
    }


@router.get("/api/ratp-disruptions")
def get_ratp_disruptions():
    raw = fetch_ratp_disruptions(API_KEY)
    if not raw:
        raise HTTPException(status_code=500, detail="Erreur récupération IDFM")

    filtered = filter_metro_rer(raw)
    logger.info(f"🟢 {len(filtered['disruptions'])} perturbations retenues (métro/RER)")
    logger.info(f"🟢 {len(filtered['lines'])} lignes retenues (métro/RER)")
    return JSONResponse(content=filtered)

