from typing import List, Optional
from pydantic import BaseModel, Field

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
    language_code: str = Field(..., description="Language code e.g. 'en', 'te', 'hi'")
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
