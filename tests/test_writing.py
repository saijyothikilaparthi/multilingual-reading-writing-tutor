import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_read_root():
    response = client.get("/")
    assert response.status_code == 200

def test_get_languages():
    response = client.get("/api/languages")
    assert response.status_code == 200
    languages = response.json()
    assert isinstance(languages, list)
    lang_codes = [lang["language_code"] for lang in languages]
    assert "en" in lang_codes
    assert "te" in lang_codes

def test_telugu_character_data_verification():
    response = client.get("/api/languages/te/characters")
    assert response.status_code == 200
    chars = response.json()
    assert isinstance(chars, list)
    assert len(chars) > 0
    
    first_char = chars[0]
    assert first_char["character"] == "అ"
    assert first_char["unicode"] == "U+0C05"
    assert first_char["letter_id"] == "te_U+0C05"

    template_resp = client.get(f"/api/templates/{first_char['letter_id']}")
    assert template_resp.status_code == 200
    template_data = template_resp.json()
    assert template_data["character"] == "అ"
    assert template_data["unicode"] == "U+0C05"
    assert template_data["language"] == "telugu"
    assert template_data["is_verified"] is True
    
    strokes = template_data["strokes"]
    assert len(strokes) > 0
    for stroke in strokes:
        assert "stroke_number" in stroke
        assert "start" in stroke
        assert "end" in stroke
        assert "points" in stroke
        assert isinstance(stroke["points"], list)

def test_writing_next_letter_cycling():
    # Test that writing mode loads characters list and can fetch templates for next letter in sequence
    response = client.get("/api/languages/te/characters")
    assert response.status_code == 200
    chars = response.json()
    assert len(chars) > 1
    
    first_char_id = chars[0]["letter_id"]
    second_char_id = chars[1]["letter_id"]

    t1 = client.get(f"/api/templates/{first_char_id}").json()
    t2 = client.get(f"/api/templates/{second_char_id}").json()

    assert t1["character"] == "అ"
    assert t2["character"] == "ఆ"

def test_english_a_compatibility():
    response = client.get("/api/templates/en_A")
    assert response.status_code == 200
    data = response.json()
    assert data["letter_id"] == "en_A"
    assert data["character"] == "A"
    assert data["unicode"] == "U+0041"
    assert data["is_verified"] is True
    assert len(data["strokes"]) == 3

def test_evaluate_correct_english_strokes():
    user_strokes = [
        {"points": [{"x": 150, "y": 45}, {"x": 105, "y": 150}, {"x": 60, "y": 255}]},
        {"points": [{"x": 150, "y": 45}, {"x": 195, "y": 150}, {"x": 240, "y": 255}]},
        {"points": [{"x": 90, "y": 165}, {"x": 150, "y": 165}, {"x": 210, "y": 165}]}
    ]
    payload = {
        "letter_id": "en_A",
        "user_strokes": user_strokes,
        "canvas_width": 300,
        "canvas_height": 300
    }
    response = client.post("/api/evaluate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["score"] >= 70.0
