from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from typing import List, Dict, Any
import os

from app.models.letter import EvaluationRequest, EvaluationResponse, LetterTemplate
from app.services.evaluator import (
    load_all_character_templates,
    get_supported_languages_list,
    get_characters_for_language,
    evaluate_strokes
)

app = FastAPI(
    title="Multilingual Tutor - Writing Mode",
    description="Data-driven Writing Tutor vertical slice supporting Indian Languages & English",
    version="2.0.0"
)

# API Endpoints
@app.get("/api/languages")
def get_supported_languages() -> List[Dict[str, str]]:
    """Retrieve list of supported languages."""
    return get_supported_languages_list()

@app.get("/api/languages/{language_code}/characters")
def get_language_characters(language_code: str) -> List[Dict[str, Any]]:
    """Retrieve list of available character files for a language."""
    chars = get_characters_for_language(language_code)
    if not chars:
        raise HTTPException(status_code=404, detail=f"Language '{language_code}' not supported or has no character data.")
    return chars

@app.get("/api/templates/{letter_id}", response_model=LetterTemplate)
def get_letter_template(letter_id: str):
    """Retrieve explicit character data and reference strokes for a letter."""
    templates = load_all_character_templates()
    if letter_id not in templates:
        raise HTTPException(status_code=404, detail=f"Character template '{letter_id}' not found.")
    return templates[letter_id]

@app.post("/api/evaluate", response_model=EvaluationResponse)
def evaluate_writing(request: EvaluationRequest):
    """Evaluate student canvas strokes against reference character template."""
    return evaluate_strokes(
        letter_id=request.letter_id,
        user_strokes=request.user_strokes,
        canvas_w=request.canvas_width,
        canvas_h=request.canvas_height
    )

# Serve static frontend files
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
def read_root():
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "Multilingual Tutor API is running."}
