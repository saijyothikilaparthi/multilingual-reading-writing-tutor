import json
import os
import math
from typing import List, Dict, Optional
from app.models.letter import Point, Stroke, ReferenceStroke, LetterTemplate, EvaluationResponse

CHARACTERS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "characters")

def load_all_character_templates() -> Dict[str, LetterTemplate]:
    templates = {}
    if not os.path.exists(CHARACTERS_DIR):
        return templates

    for lang_folder in os.listdir(CHARACTERS_DIR):
        lang_path = os.path.join(CHARACTERS_DIR, lang_folder)
        if os.path.isdir(lang_path):
            for file_name in os.listdir(lang_path):
                if file_name.endswith(".json"):
                    file_path = os.path.join(lang_path, file_name)
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        strokes = [
                            ReferenceStroke(
                                stroke_number=s.get("stroke_number", idx + 1),
                                start=Point(**s["start"]),
                                end=Point(**s["end"]),
                                points=[Point(**p) for p in s["points"]],
                                direction_description=s.get("direction_description", "")
                            )
                            for idx, s in enumerate(data.get("strokes", []))
                        ]
                        template = LetterTemplate(
                            language=data["language"],
                            language_code=data.get("language_code", "en"),
                            character=data["character"],
                            unicode=data["unicode"],
                            letter_id=data.get("letter_id", f"{data.get('language_code')}_{data['unicode']}"),
                            is_verified=data.get("is_verified", False),
                            data_status=data.get("data_status"),
                            source=data.get("source"),
                            strokes=strokes
                        )
                        templates[template.letter_id] = template
    return templates

def get_supported_languages_list() -> List[Dict[str, str]]:
    templates = load_all_character_templates()
    langs = {}
    for t in templates.values():
        if t.language_code not in langs:
            langs[t.language_code] = {
                "language_code": t.language_code,
                "language_name": t.language.capitalize(),
                "language": t.language
            }
    return list(langs.values())

def get_characters_for_language(language_code: str) -> List[Dict[str, str]]:
    templates = load_all_character_templates()
    chars = []
    for t in templates.values():
        if t.language_code == language_code or t.language == language_code:
            chars.append({
                "letter_id": t.letter_id,
                "character": t.character,
                "char": t.character,
                "unicode": t.unicode,
                "language": t.language,
                "is_verified": t.is_verified,
                "data_status": t.data_status
            })
    return chars

def distance(p1: Point, p2: Point) -> float:
    return math.sqrt((p1.x - p2.x) ** 2 + (p1.y - p2.y) ** 2)

def evaluate_strokes(letter_id: str, user_strokes: List[Stroke], canvas_w: float, canvas_h: float) -> EvaluationResponse:
    templates = load_all_character_templates()
    if letter_id not in templates:
        return EvaluationResponse(
            success=False,
            score=0.0,
            message=f"Template for '{letter_id}' not found."
        )

    template = templates[letter_id]
    ref_strokes = template.strokes

    if not user_strokes:
        return EvaluationResponse(
            success=False,
            score=0.0,
            message=f"No strokes provided. Please draw character '{template.character}'."
        )

    normalized_user_strokes: List[List[Point]] = []
    for stroke in user_strokes:
        norm_points = []
        for p in stroke.points:
            norm_x = p.x / canvas_w if canvas_w > 0 and p.x > 1.0 else p.x
            norm_y = p.y / canvas_h if canvas_h > 0 and p.y > 1.0 else p.y
            norm_points.append(Point(x=norm_x, y=norm_y))
        if norm_points:
            normalized_user_strokes.append(norm_points)

    if len(normalized_user_strokes) < len(ref_strokes):
        return EvaluationResponse(
            success=False,
            score=30.0,
            message=f"You drew {len(normalized_user_strokes)} stroke(s), but '{template.character}' requires {len(ref_strokes)} strokes. Please try again!"
        )

    stroke_scores = []

    for i, ref in enumerate(ref_strokes):
        best_stroke_score = 0.0
        
        for u_stroke in normalized_user_strokes:
            u_start = u_stroke[0]
            u_end = u_stroke[-1]

            start_dist = distance(u_start, ref.start)
            start_score = max(0.0, 100.0 - (start_dist * 200.0))

            end_dist = distance(u_end, ref.end)
            end_score = max(0.0, 100.0 - (end_dist * 200.0))

            reverse_start_dist = distance(u_start, ref.end)
            reverse_end_dist = distance(u_end, ref.start)
            reverse_score = max(0.0, 100.0 - ((reverse_start_dist + reverse_end_dist) * 100.0)) - 10.0

            endpoint_score = max(0.5 * start_score + 0.5 * end_score, reverse_score)

            mid_ref = ref.points[len(ref.points) // 2]
            min_mid_dist = min(distance(p, mid_ref) for p in u_stroke)
            trajectory_score = max(0.0, 100.0 - (min_mid_dist * 200.0))

            curr_score = (endpoint_score * 0.6) + (trajectory_score * 0.4)
            if curr_score > best_stroke_score:
                best_stroke_score = curr_score

        stroke_scores.append(best_stroke_score)

    overall_score = sum(stroke_scores) / len(stroke_scores) if stroke_scores else 0.0
    is_success = overall_score >= 55.0

    if is_success:
        msg = f"Excellent writing! You drew '{template.character}' correctly."
    elif overall_score >= 35.0:
        msg = f"Close! Pay attention to starting points and stroke order, and try again."
    else:
        msg = f"Keep practicing! Watch the demonstration to see how to form '{template.character}'."

    return EvaluationResponse(
        success=is_success,
        score=round(overall_score, 1),
        message=msg,
        details={"stroke_scores": [round(s, 1) for s in stroke_scores]}
    )
