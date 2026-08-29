from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from typing import List, Dict, Any, Optional
import os
import json

from app.models.letter import (
    EvaluationRequest,
    EvaluationResponse,
    LetterTemplate,
    ReadingContentResponse,
    SpeechRecognitionRequest,
    SpeechRecognitionResponse,
    ReadingAssessmentRequest,
    ReadingAssessmentResponse,
    ConversationalTutorRequest,
    ConversationalTutorResponse,
    ReadingProcessRequest
)
from app.services.evaluator import (
    load_all_character_templates,
    get_supported_languages_list,
    get_characters_for_language,
    evaluate_strokes
)
from app.services.reading import (
    get_reading_content,
    SraVaaniASRService,
    ReadingEvaluatorService,
    ConversationalTutorService,
    DISCLAIMER
)

app = FastAPI(
    title="Multilingual Tutor - Reading & Writing Mode",
    description="Data-driven Multilingual Tutor supporting Reading Mode (SraVaani ASR, Pronunciation Assessment, Conversational Tutor) & Writing Mode across English, Telugu, Hindi, Malayalam.",
    version="2.1.0"
)

# API Endpoints - Writing Mode (Preserved)
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


# API Endpoints - Reading Mode

@app.get("/api/reading/languages")
def get_reading_supported_languages() -> List[Dict[str, str]]:
    """List supported languages for Reading Mode (English, Telugu, Hindi, Malayalam)."""
    return [
        {"language_code": "en", "language_name": "English"},
        {"language_code": "te", "language_name": "Telugu"},
        {"language_code": "hi", "language_name": "Hindi"},
        {"language_code": "ml", "language_name": "Malayalam"}
    ]

@app.get("/api/reading/content/{language_code}", response_model=ReadingContentResponse)
def get_reading_materials(language_code: str, level: Optional[str] = None):
    """Retrieve structured reading material for specified language and level."""
    try:
        return get_reading_content(language_code=language_code, level=level)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/reading/recognize", response_model=SpeechRecognitionResponse)
def recognize_speech(request: SpeechRecognitionRequest, expected_hint: Optional[str] = None):
    """SraVaani ASR layer: Transcribes speech audio to text."""
    return SraVaaniASRService.transcribe_audio(
        language_code=request.language_code,
        audio_b64=request.audio_b64,
        expected_hint=expected_hint
    )

@app.post("/api/reading/assess", response_model=ReadingAssessmentResponse)
def assess_reading(request: ReadingAssessmentRequest):
    """Decoupled Pronunciation & Reading Assessment layer."""
    return ReadingEvaluatorService.evaluate(
        language_code=request.language_code,
        level=request.level,
        expected_text=request.expected_text,
        recognized_transcript=request.recognized_transcript
    )

@app.post("/api/reading/tutor", response_model=ConversationalTutorResponse)
def conversational_tutor(request: ConversationalTutorRequest):
    """Decoupled Conversational Tutor layer."""
    return ConversationalTutorService.generate_feedback(
        language_code=request.language_code,
        level=request.level,
        expected_text=request.expected_text,
        recognized_transcript=request.recognized_transcript,
        assessment=request.assessment
    )

@app.post("/api/reading/process-full")
def process_full_reading_attempt(
    req: ReadingProcessRequest
):
    """Integrated REST endpoint combining ASR, Assessment, and Conversational Tutor."""
    language_code = req.language_code
    level = req.level
    expected_text = req.expected_text or ""
    audio_b64 = req.audio_b64

    asr_res = SraVaaniASRService.transcribe_audio(
        language_code=language_code,
        audio_b64=audio_b64,
        expected_hint=expected_text
    )

    if not asr_res.success:
        return {
            "success": False,
            "asr": asr_res,
            "error": asr_res.error or "Audio recognition failed",
            "disclaimer": DISCLAIMER
        }

    assessment = ReadingEvaluatorService.evaluate(
        language_code=language_code,
        level=level,
        expected_text=expected_text,
        recognized_transcript=asr_res.transcript
    )

    tutor_res = ConversationalTutorService.generate_feedback(
        language_code=language_code,
        level=level,
        expected_text=expected_text,
        recognized_transcript=asr_res.transcript,
        assessment=assessment
    )

    return {
        "success": True,
        "asr": asr_res,
        "assessment": assessment,
        "tutor": tutor_res,
        "disclaimer": DISCLAIMER
    }


# WebSocket endpoint for real-time continuous audio streaming & tutoring
@app.websocket("/ws/reading/stream")
async def websocket_reading_stream(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data_text = await websocket.receive_text()
            data = json.loads(data_text)

            language_code = data.get("language_code", "en")
            level = data.get("level", "passage")
            expected_text = data.get("expected_text", "")
            audio_chunk_b64 = data.get("audio_b64")

            # Process stream chunk
            asr_res = SraVaaniASRService.transcribe_audio(
                language_code=language_code,
                audio_b64=audio_chunk_b64,
                expected_hint=expected_text
            )

            if not asr_res.success:
                await websocket.send_json({
                    "event": "error",
                    "error": asr_res.error,
                    "disclaimer": DISCLAIMER
                })
                continue

            assessment = ReadingEvaluatorService.evaluate(
                language_code=language_code,
                level=level,
                expected_text=expected_text,
                recognized_transcript=asr_res.transcript
            )

            tutor_res = ConversationalTutorService.generate_feedback(
                language_code=language_code,
                level=level,
                expected_text=expected_text,
                recognized_transcript=asr_res.transcript,
                assessment=assessment
            )

            await websocket.send_json({
                "event": "transcription_update",
                "asr": asr_res.dict(),
                "assessment": assessment.dict(),
                "tutor": tutor_res.dict(),
                "disclaimer": DISCLAIMER
            })
    except WebSocketDisconnect:
        pass
    except Exception as e:
        await websocket.send_json({"event": "error", "error": str(e), "disclaimer": DISCLAIMER})


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
