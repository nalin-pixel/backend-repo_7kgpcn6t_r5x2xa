"""
Database Schemas for AI Music Studio

Each Pydantic model represents a collection in MongoDB.
Collection name = lowercase of class name.
"""
from __future__ import annotations
from pydantic import BaseModel, Field
from typing import List, Optional, Literal, Dict, Any

# ---------- Core domain models ----------

InstrumentType = Literal[
    "drums", "bass", "guitar", "piano", "synth", "strings", "brass", "pads", "vox"
]

class InstrumentSettings(BaseModel):
    type: InstrumentType
    name: Optional[str] = None
    volume: float = Field(0.8, ge=0.0, le=1.0)
    pan: float = Field(0.0, ge=-1.0, le=1.0)
    eq_low: float = Field(0.0, ge=-12.0, le=12.0)
    eq_mid: float = Field(0.0, ge=-12.0, le=12.0)
    eq_high: float = Field(0.0, ge=-12.0, le=12.0)
    reverb: float = Field(0.1, ge=0.0, le=1.0)
    delay: float = Field(0.0, ge=0.0, le=1.0)
    # Drum-specific
    kick_intensity: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    snare_type: Optional[str] = None
    hihat_pattern: Optional[str] = None
    # Bass-specific
    bass_type: Optional[Literal["808", "sub", "plucked"]] = None
    distortion: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    # Synth-specific
    synth_type: Optional[Literal["pad", "lead", "pluck"]] = None
    modulation: Optional[float] = Field(default=None, ge=0.0, le=1.0)

class VoiceSettings(BaseModel):
    voice_id: str = "ai_voice_female_01"
    gender: Optional[Literal["male", "female", "neutral"]] = None
    reverb: float = Field(0.1, ge=0.0, le=1.0)
    echo: float = Field(0.0, ge=0.0, le=1.0)
    autotune: float = Field(0.2, ge=0.0, le=1.0)
    pitch_shift: float = Field(0.0, ge=-12.0, le=12.0)

class LoopOptions(BaseModel):
    intro: bool = True
    verse: bool = True
    chorus: bool = True
    drop: bool = False
    outro: bool = True

class GenerationRequest(BaseModel):
    prompt: str = Field(..., description="Text or lyrics-to-music prompt")
    lyrics: Optional[str] = None
    style: Optional[str] = Field(default="LoFi")
    bpm: int = Field(default=90, ge=40, le=200)
    key: Optional[str] = Field(default="C Minor")
    mood: Optional[str] = Field(default="Chill")
    instruments: List[InstrumentSettings] = Field(default_factory=list)
    voice: Optional[VoiceSettings] = None
    mastering_preset: Optional[str] = Field(default="Clean Balanced Master")
    loop_options: LoopOptions = Field(default_factory=LoopOptions)
    reference_upload_id: Optional[str] = None

class GenerationRecord(BaseModel):
    prompt: str
    settings: Dict[str, Any]
    audio_path: Optional[str] = None
    audio_format: str = "wav"
    video_path: Optional[str] = None
    stems_paths: Optional[Dict[str, str]] = None
    midi_paths: Optional[Dict[str, str]] = None

class Preset(BaseModel):
    title: str
    settings: Dict[str, Any]

class UploadRecord(BaseModel):
    filename: str
    kind: Literal["reference", "voice"] = "reference"
    analysis: Optional[Dict[str, Any]] = None

# Expose minimal example schemas so Database Viewer can work if needed
class User(BaseModel):
    name: str
    email: str
    address: str
    age: Optional[int] = None
    is_active: bool = True

class Product(BaseModel):
    title: str
    description: Optional[str] = None
    price: float
    category: str
    in_stock: bool = True
