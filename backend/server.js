const express = require("express");
const path = require("path");
const { v4: uuidv4 } = require("uuid");
const locations = require("./data/locations");

const app = express();
app.use(express.json());

// Serve building images from src/images/ at /images/:filename
app.use("/images", express.static(path.join(__dirname, "../src/images")));

const PORT = 3000;
const GAME_DURATION_SECONDS = 90;

// In-memory session store: sessionId -> GameSession
const sessions = new Map();

function createSession() {
  return {
    id: uuidv4(),
    started_at: null,   // set on first answer submission
    answered: {},       // { locationKey: { correct: bool, correct_answer: str } }
  };
}

function getRemainingSeconds(session) {
  if (!session.started_at) return GAME_DURATION_SECONDS;
  const elapsed = (Date.now() - session.started_at) / 1000;
  return Math.max(0, GAME_DURATION_SECONDS - elapsed);
}

function isGameOver(session) {
  return (
    getRemainingSeconds(session) <= 0 ||
    Object.keys(session.answered).length >= locations.length
  );
}

function shuffleOptions(loc) {
  const opts = [...loc.options, loc.answer];
  for (let i = opts.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [opts[i], opts[j]] = [opts[j], opts[i]];
  }
  return opts;
}

// POST /api/games — create a new game session
app.post("/api/games", (req, res) => {
  const session = createSession();
  sessions.set(session.id, session);
  res.json({ session_id: session.id });
});

// GET /api/games/:id — get current game state
app.get("/api/games/:id", (req, res) => {
  const session = sessions.get(req.params.id);
  if (!session) return res.status(404).json({ error: "Session not found" });

  const remaining_seconds = getRemainingSeconds(session);
  const score = Object.values(session.answered).filter((a) => a.correct).length;

  res.json({
    session_id: session.id,
    is_started: session.started_at !== null,
    is_over: isGameOver(session),
    remaining_seconds: Math.floor(remaining_seconds),
    score,
    total: locations.length,
    answered_locations: Object.keys(session.answered),
  });
});

// GET /api/locations — list all location keys and image paths
app.get("/api/locations", (req, res) => {
  res.json(locations.map(({ key, img_path }) => ({ key, img_path })));
});

// GET /api/locations/:key/question — get shuffled question for a location
app.get("/api/locations/:key/question", (req, res) => {
  const loc = locations.find((l) => l.key === req.params.key);
  if (!loc) return res.status(404).json({ error: "Location not found" });

  res.json({
    key: loc.key,
    question: loc.trivia_question,
    options: shuffleOptions(loc),
  });
});

// POST /api/games/:id/answer — submit an answer
app.post("/api/games/:id/answer", (req, res) => {
  const session = sessions.get(req.params.id);
  if (!session) return res.status(404).json({ error: "Session not found" });

  if (isGameOver(session)) {
    return res.status(400).json({ error: "Game is already over" });
  }

  const { location_key, answer } = req.body;
  if (!location_key || !answer) {
    return res.status(400).json({ error: "location_key and answer are required" });
  }

  const loc = locations.find((l) => l.key === location_key);
  if (!loc) return res.status(404).json({ error: "Location not found" });

  if (session.answered[location_key]) {
    return res.status(400).json({ error: "Location already answered" });
  }

  // Start timer on first answer
  if (!session.started_at) {
    session.started_at = Date.now();
  }

  const correct = answer === loc.answer;
  session.answered[location_key] = { correct, correct_answer: loc.answer };

  const score = Object.values(session.answered).filter((a) => a.correct).length;
  const remaining_seconds = getRemainingSeconds(session);

  res.json({
    correct,
    correct_answer: loc.answer,
    score,
    total_answered: Object.keys(session.answered).length,
    is_over: isGameOver(session),
    remaining_seconds: Math.floor(remaining_seconds),
  });
});

// GET /api/map?selected=<key> — serve Leaflet.js map HTML
app.get("/api/map", (req, res) => {
  const selected = req.query.selected || "";

  const markersJs = locations
    .map((loc) => {
      const isSelected = loc.key === selected;
      const imgFile = path.basename(loc.img_path);
      const color = isSelected ? "#e74c3c" : "#3388ff";
      const size = isSelected ? 22 : 14;
      const border = isSelected ? "3px solid white" : "2px solid white";
      const shadow = "box-shadow:0 0 6px rgba(0,0,0,0.5)";
      const icon = `L.divIcon({
        html: '<div style="background:${color};width:${size}px;height:${size}px;border-radius:50%;border:${border};${shadow}"></div>',
        iconSize: [${size}, ${size}],
        iconAnchor: [${size / 2}, ${size / 2}],
        popupAnchor: [0, -${size / 2}],
        className: ''
      })`;
      const popup = `<div style="width:220px;font-family:Arial,sans-serif;">
        <h4 style="color:#003366;margin:0 0 8px;">${loc.key}${isSelected ? " ⭐" : ""}</h4>
        <img src="http://localhost:${PORT}/images/${imgFile}" width="200"
             style="border-radius:5px;margin-bottom:8px;" onerror="this.style.display='none'" />
        <p style="margin:0;font-size:0.85em;color:#555;">
          ${isSelected ? "Currently selected for trivia" : "Use the dropdown to select for trivia"}
        </p>
      </div>`;
      return `L.marker([${loc.lat}, ${loc.lng}], {icon: ${icon}})
        .bindPopup(\`${popup}\`)
        .addTo(map);`;
    })
    .join("\n");

  const centerLat = selected
    ? (locations.find((l) => l.key === selected) || { lat: 51.52467, lng: -0.13439 }).lat
    : 51.52467;
  const centerLng = selected
    ? (locations.find((l) => l.key === selected) || { lat: 51.52467, lng: -0.13439 }).lng
    : -0.13439;
  const zoom = selected ? 16 : 14;

  res.send(`<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8" />
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
  <style>
    body { margin: 0; padding: 0; }
    #map { width: 100%; height: 100vh; }
  </style>
</head>
<body>
  <div id="map"></div>
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <script>
    const map = L.map('map').setView([${centerLat}, ${centerLng}], ${zoom});
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
      maxZoom: 19
    }).addTo(map);
    ${markersJs}
  </script>
</body>
</html>`);
});

app.listen(PORT, () => {
  console.log(`UCL Guessr backend running on http://localhost:${PORT}`);
});
