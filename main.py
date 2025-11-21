import os
import io
import math
import random
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from database import db, create_document
from schemas import GenerationRequest

# --- App setup ---
app = FastAPI(title="AI Music Studio API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static directories for generated assets
BASE_DIR = "/tmp/ai_music_studio"
AUDIO_DIR = os.path.join(BASE_DIR, "static", "audio")
VIDEO_DIR = os.path.join(BASE_DIR, "static", "video")
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
MIDI_DIR = os.path.join(BASE_DIR, "static", "midi")

for d in [AUDIO_DIR, VIDEO_DIR, UPLOAD_DIR, MIDI_DIR]:
    os.makedirs(d, exist_ok=True)

app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")


# --- Utilities ---

def _sine_wave_to_wav(path: str, seconds: float = 8.0, freq: float = 220.0, sample_rate: int = 44100, volume: float = 0.3):
    import wave, struct
    n_frames = int(seconds * sample_rate)
    with wave.open(path, 'w') as wf:
        wf.setnchannels(2)  # stereo
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(sample_rate)
        for i in range(n_frames):
            t = i / sample_rate
            value = int(volume * 32767 * math.sin(2 * math.pi * freq * t))
            data = struct.pack('<hh', value, value)
            wf.writeframesraw(data)


def _random_bpm_key_style():
    bpms = random.randint(70, 140)
    keys = random.choice(["C Major", "A Minor", "G Minor", "D Major", "F# Minor"])
    style = random.choice(["LoFi", "Trap", "EDM", "Rock", "Bollywood", "Chillhop", "Romantic"])
    return bpms, keys, style


# --- Schemas (local simple ones for responses) ---
class GenerationResponse(BaseModel):
    id: str
    audio_url: str
    audio_format: str = "wav"
    waveform_url: Optional[str] = None
    video_url: Optional[str] = None


# --- Basic endpoints ---
@app.get("/")
def root():
    return {"name": "AI Music Studio API", "status": "ok"}


@app.get("/test")
def test_database():
    info = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "collections": [],
    }
    try:
        if db is not None:
            info["database"] = "✅ Connected"
            info["collections"] = db.list_collection_names()
    except Exception as e:
        info["database"] = f"⚠️ {str(e)}"
    return info


# --- Uploads ---
@app.post("/api/upload/reference")
async def upload_reference(file: UploadFile = File(...)):
    uid = str(uuid.uuid4())
    ext = os.path.splitext(file.filename or "")[1] or ".mp3"
    dest = os.path.join(UPLOAD_DIR, f"ref_{uid}{ext}")
    with open(dest, "wb") as f:
        f.write(await file.read())

    bpm, key, style = _random_bpm_key_style()
    record = {
        "filename": file.filename,
        "stored_path": dest,
        "type": "reference",
        "analysis": {"bpm": bpm, "key": key, "style": style},
        "created_at": datetime.utcnow(),
    }
    try:
        create_document("uploadrecord", record)
    except Exception:
        pass
    return {"id": uid, "analysis": record["analysis"]}


@app.post("/api/upload/voice")
async def upload_voice(file: UploadFile = File(...)):
    uid = str(uuid.uuid4())
    ext = os.path.splitext(file.filename or "")[1] or ".wav"
    dest = os.path.join(UPLOAD_DIR, f"voice_{uid}{ext}")
    with open(dest, "wb") as f:
        f.write(await file.read())

    return {"id": uid, "voice_id": f"voice_custom_{uid[:8]}", "message": "Voice uploaded (simulated)"}


# --- Music generation (simulated) ---
@app.post("/api/generate/music", response_model=GenerationResponse)
async def generate_music(req: GenerationRequest):
    uid = str(uuid.uuid4())
    freq = 110.0 + (req.bpm - 40) * 1.5 if req.bpm else 220.0
    audio_path = os.path.join(AUDIO_DIR, f"{uid}.wav")
    _sine_wave_to_wav(audio_path, seconds=10.0, freq=freq)

    # Save history
    record = {
        "prompt": req.prompt,
        "settings": req.model_dump(),
        "audio_path": audio_path,
        "audio_format": "wav",
        "created_at": datetime.utcnow(),
    }
    try:
        create_document("generationrecord", record)
    except Exception:
        pass

    return GenerationResponse(
        id=uid,
        audio_url=f"/static/audio/{uid}.wav",
        audio_format="wav",
        waveform_url=None,
        video_url=None,
    )


@app.post("/api/generate/video")
async def generate_video(prompt: str = Form(...), music_id: Optional[str] = Form(None)):
    uid = music_id or str(uuid.uuid4())
    # Simulated video generation: return a placeholder gradient animation route for frontend
    video_url = f"/static/video/{uid}.mp4"
    # We don't actually create an mp4, the frontend will display an AI visual instead.
    return {"id": uid, "video_url": video_url, "status": "simulated"}


# --- Exports ---
@app.get("/api/export/audio/{music_id}.{ext}")
async def export_audio(music_id: str, ext: str):
    wav_path = os.path.join(AUDIO_DIR, f"{music_id}.wav")
    if not os.path.exists(wav_path):
        return JSONResponse(status_code=404, content={"error": "Audio not found"})
    # For demo, return WAV regardless of requested ext
    filename = f"track_{music_id}.{ext}"
    return FileResponse(wav_path, media_type="audio/wav", filename=filename)


@app.get("/api/export/stems/{music_id}")
async def export_stems(music_id: str):
    # Create a few alternate sine waves as stems
    stems = {
        "vocals": 440.0,
        "drums": 120.0,
        "bass": 55.0,
        "piano": 261.6,
        "synth": 329.6,
    }
    urls: Dict[str, str] = {}
    for name, f in stems.items():
        p = os.path.join(AUDIO_DIR, f"{music_id}_{name}.wav")
        if not os.path.exists(p):
            _sine_wave_to_wav(p, seconds=6.0, freq=f, volume=0.25)
        urls[name] = f"/static/audio/{music_id}_{name}.wav"
    return {"id": music_id, "stems": urls}


@app.get("/api/export/midi/{music_id}")
async def export_midi(music_id: str):
    # Create a tiny pseudo-MIDI TXT for demo
    midi_txt = os.path.join(MIDI_DIR, f"{music_id}.mid.txt")
    if not os.path.exists(midi_txt):
        with open(midi_txt, "w") as f:
            f.write("MIDI DEMO\nC4:1 D4:1 E4:2 G4:2 C5:4\n")
    return {"id": music_id, "midi_url": f"/static/midi/{music_id}.mid.txt"}


# --- History & presets ---
@app.get("/api/history")
async def get_history(limit: int = 20):
    try:
        docs = db["generationrecord"].find().sort("created_at", -1).limit(limit)
        items = []
        for d in docs:
            d["_id"] = str(d.get("_id"))
            items.append(d)
        return {"items": items}
    except Exception:
        return {"items": []}


class PresetModel(BaseModel):
    title: str
    settings: Dict[str, Any]


@app.post("/api/presets")
async def create_preset(preset: PresetModel):
    try:
        pid = create_document("preset", {**preset.model_dump(), "created_at": datetime.utcnow()})
        return {"id": pid}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/api/presets")
async def list_presets():
    try:
        docs = db["preset"].find().sort("created_at", -1)
        items = []
        for d in docs:
            d["_id"] = str(d.get("_id"))
            items.append(d)
        return {"items": items}
    except Exception:
        return {"items": []}


# --- Theory helpers ---
NOTES_SHARP = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def build_scale(key: str):
    try:
        tonic, quality = key.split()
    except ValueError:
        tonic, quality = key, "Major"
    if tonic not in NOTES_SHARP:
        tonic = "C"
    major_steps = [2, 2, 1, 2, 2, 2, 1]
    minor_steps = [2, 1, 2, 2, 1, 2, 2]
    steps = major_steps if quality.lower().startswith("maj") else minor_steps
    idx = NOTES_SHARP.index(tonic)
    scale = [tonic]
    for s in steps[:-1]:
        idx = (idx + s) % 12
        scale.append(NOTES_SHARP[idx])
    return scale


@app.get("/api/generate/chords")
async def generate_chords(key: str = "C Major"):
    scale = build_scale(key)
    degrees = [0, 5, 3, 4]  # I, vi, IV, V in index terms (approx)
    prog = [f"{scale[d]}{'' if d in [0,3,4] else 'm'}" for d in degrees]
    return {"key": key, "progression": prog}


@app.get("/api/generate/melody")
async def generate_melody(key: str = "C Major", bars: int = 2, bpm: int = 90):
    scale = build_scale(key)
    melody = []
    for _ in range(bars * 4):  # 4 notes per bar
        n = random.choice(scale)
        dur = random.choice([0.5, 1.0, 1.0, 2.0])
        melody.append({"note": n + str(random.choice([4, 5])), "duration": dur})
    return {"key": key, "bpm": bpm, "melody": melody}


# --- Remix ---
@app.post("/api/remix")
async def remix(style: str = Form(...), file: UploadFile = File(...)):
    uid = str(uuid.uuid4())
    ext = os.path.splitext(file.filename or "")[1] or ".mp3"
    dest = os.path.join(UPLOAD_DIR, f"remix_{uid}{ext}")
    with open(dest, "wb") as f:
        f.write(await file.read())

    # Produce a new audio placeholder
    out = os.path.join(AUDIO_DIR, f"{uid}.wav")
    _sine_wave_to_wav(out, seconds=8.0, freq=random.choice([200, 240, 300]))
    return {"id": uid, "style": style, "audio_url": f"/static/audio/{uid}.wav"}


# --- Mastering ---
@app.post("/api/master")
async def master_track(music_id: str = Form(...), preset: str = Form("Clean Balanced Master")):
    wav_path = os.path.join(AUDIO_DIR, f"{music_id}.wav")
    if not os.path.exists(wav_path):
        return JSONResponse(status_code=404, content={"error": "Audio not found"})
    # Simulate: return same file with preset metadata
    return {"id": music_id, "preset": preset, "audio_url": f"/static/audio/{music_id}.wav"}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
