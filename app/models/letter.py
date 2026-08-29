from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

# Existing Writing Mode Models
class Point(BaseModel):
    x: float = Field(..., description="X coordinate relative to canvas width [0, 1]")
    y: float = Field(..., description="Y coordinate relative to canvas height [0, 1]")
    t: Optional[float] = Field(None, description="Timestamp in milliseconds")

class Stroke(BaseModel):
    points: List[Point] = Field(..., description="Ordered list of points forming a single continuous stroke")

class ReferenceStroke(BaseModel):
    stroke_number: int = Field(..., description="Stroke order number (1-based index)")
    start: Point = Field(..., description="Starting coordinate [0, 1]")
    end: Point = Field(..., description="Ending coordinate [0, 1]")
    points: List[Point] = Field(..., description="Ordered path waypoints [0, 1]")
    direction_description: str = Field(..., description="Direction description")

class LetterTemplate(BaseModel):
    language: str = Field(..., description="Language name e.g. 'english', 'telugu'")
    language_code: str = Field(..., description="Language code e.g. 'en', 'te', 'hi', 'ml'")
    character: str = Field(..., description="Unicode character glyph e.g. 'A', 'అ'")
    unicode: str = Field(..., description="Hex Unicode e.g. 'U+0041', 'U+0C05'")
    letter_id: str = Field(..., description="Unique template identifier e.g. 'en_A', 'te_U+0C05'")
    is_verified: bool = Field(default=False, description="True if stroke coordinates are verified from handwriting dataset")
    data_status: Optional[str] = Field(None, description="Status of stroke data accuracy")
    source: Optional[str] = Field(None, description="Citation or source of stroke coordinates")
    strokes: List[ReferenceStroke] = Field(..., description="Ordered list of strokes")

class EvaluationRequest(BaseModel):
    letter_id: str = Field(..., description="Letter template identifier")
    user_strokes: List[Stroke] = Field(..., description="List of strokes captured from the user canvas")
    canvas_width: float = Field(..., description="Width of the canvas when drawing")
    canvas_height: float = Field(..., description="Height of the canvas when drawing")

class EvaluationResponse(BaseModel):
    success: bool = Field(..., description="Whether the writing meets evaluation criteria")
    score: float = Field(..., description="Overall accuracy score [0 - 100]")
    message: str = Field(..., description="Feedback message for the student")
    details: Optional[dict] = Field(default=None, description="Detailed stroke level scores/feedback")


# Reading Mode Models

class ReadingContentItem(BaseModel):
    id: str = Field(..., description="Content item ID e.g. 'basic_1', 'word_1', 'passage_1'")
    level: str = Field(..., description="Level: 'basic', 'word_sentence', 'passage', 'free'")
    expected_text: str = Field(..., description="Expected text to read (empty for free reading)")
    display_text: str = Field(..., description="Text displayed to child")
    transliteration: Optional[str] = Field(None, description="Optional phonetic guide or transliteration")
    audio_hint_url: Optional[str] = Field(None, description="Optional audio sample URL for target item")

class ReadingContentResponse(BaseModel):
    language_code: str
    language_name: str
    level: str
    items: List[ReadingContentItem]

class SpeechRecognitionRequest(BaseModel):
    language_code: str = Field(..., description="Language code: en, te, hi, ml")
    audio_b64: Optional[str] = Field(None, description="Base64 encoded audio bytes (WAV/WEBM/PCM)")
    sample_rate: int = Field(default=16000, description="Audio sample rate in Hz")

class SpeechRecognitionResponse(BaseModel):
    success: bool
    transcript: str
    language_code: str
    confidence: float = Field(default=1.0)
    service_used: str = Field(default="SraVaani ASR")
    error: Optional[str] = None

class ReadingAssessmentRequest(BaseModel):
    language_code: str
    level: str = Field(..., description="basic, word_sentence, passage, free")
    expected_text: str
    recognized_transcript: str

class ErrorDetail(BaseModel):
    token: str
    error_type: str = Field(..., description="missing, mispronounced, substituted, extra")
    expected: Optional[str] = None
    got: Optional[str] = None
    tip: Optional[str] = None

class ReadingAssessmentResponse(BaseModel):
    is_correct: bool
    accuracy_score: float = Field(..., description="0-100 score")
    recognized_transcript: str
    expected_text: str
    errors: List[ErrorDetail]
    disclaimer: str = Field(
        default="This is an educational learning & support tool, not a medical diagnostic system."
    )

class ConversationalTutorRequest(BaseModel):
    language_code: str
    level: str
    expected_text: str
    recognized_transcript: str
    assessment: ReadingAssessmentResponse

class ConversationalTutorResponse(BaseModel):
    message: str
    encouragement: str
    action_suggested: str = Field(..., description="retry, next, continue, practice_more")
    audio_feedback_text: str
    disclaimer: str = Field(
        default="This is an educational learning & support tool, not a medical diagnostic system."
    )
