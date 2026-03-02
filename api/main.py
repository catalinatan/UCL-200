from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.orm import Session

from api.database import get_db
from api.routers import leaderboard, locations, questions, sessions


@asynccontextmanager
async def lifespan(app: FastAPI):
    from api.seed import seed
    seed()
    yield


app = FastAPI(
    title="UCL Guessr API",
    description="REST API for the UCL campus trivia game — built for UCL's 200th anniversary.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve building photos from src/images/ at /images/<filename>
app.mount("/images", StaticFiles(directory="src/images"), name="images")

app.include_router(locations.router, tags=["Locations"])
app.include_router(questions.router, tags=["Questions"])
app.include_router(sessions.router, tags=["Sessions"])
app.include_router(leaderboard.router, tags=["Leaderboard"])


# --------------------------------------------------------------------------- #
# Health                                                                      #
# --------------------------------------------------------------------------- #

@app.get("/health", tags=["Health"])
def health(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ok", "db": "connected", "timestamp": datetime.utcnow().isoformat()}


# --------------------------------------------------------------------------- #
# Map — server-rendered Leaflet.js HTML                                       #
# --------------------------------------------------------------------------- #

@app.get("/map", response_class=HTMLResponse, tags=["Map"])
def map_html(selected: str = "", db: Session = Depends(get_db)):
    from api.models import Location

    all_locations = db.query(Location).all()

    markers = []
    center_lat, center_lng, zoom = 51.52467, -0.13439, 14

    for loc in all_locations:
        is_selected = loc.key == selected
        if is_selected:
            center_lat, center_lng, zoom = loc.lat, loc.lng, 16

        import os
        img_file = os.path.basename(loc.img_path)
        color = "#e74c3c" if is_selected else "#3388ff"
        size = 22 if is_selected else 14
        border = "3px solid white" if is_selected else "2px solid white"
        shadow = "box-shadow:0 0 6px rgba(0,0,0,0.5)"
        star = " ⭐" if is_selected else ""
        trivia_note = "Currently selected for trivia" if is_selected else "Use the dropdown to select for trivia"

        icon = (
            f"L.divIcon({{"
            f"html: '<div style=\"background:{color};width:{size}px;height:{size}px;"
            f"border-radius:50%;border:{border};{shadow}\"></div>',"
            f"iconSize: [{size}, {size}],"
            f"iconAnchor: [{size // 2}, {size // 2}],"
            f"popupAnchor: [0, -{size // 2}],"
            f"className: ''"
            f"}})"
        )
        popup = (
            f"<div style='width:220px;font-family:Arial,sans-serif;'>"
            f"<h4 style='color:#003366;margin:0 0 8px;'>{loc.key}{star}</h4>"
            f"<img src='http://localhost:8000/images/{img_file}' width='200' "
            f"style='border-radius:5px;margin-bottom:8px;' onerror=\"this.style.display='none'\" />"
            f"<p style='margin:0;font-size:0.85em;color:#555;'>{trivia_note}</p>"
            f"</div>"
        )
        markers.append(
            f"L.marker([{loc.lat}, {loc.lng}], {{icon: {icon}}})\n"
            f"  .bindPopup(`{popup}`)\n"
            f"  .addTo(map);"
        )

    markers_js = "\n".join(markers)

    return f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8" />
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
  <style>
    body {{ margin: 0; padding: 0; }}
    #map {{ width: 100%; height: 100vh; }}
  </style>
</head>
<body>
  <div id="map"></div>
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <script>
    const map = L.map('map').setView([{center_lat}, {center_lng}], {zoom});
    L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
      attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
      maxZoom: 19
    }}).addTo(map);
    {markers_js}
  </script>
</body>
</html>"""
