import pytest
import os
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

# --- WRITING MODE REGRESSION TESTS ---

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


# --- COMPLETE READING MODE TESTS ---

def test_reading_languages():
    response = client.get("/api/reading/languages")
    assert response.status_code == 200
    langs = response.json()
    codes = [l["language_code"] for l in langs]
    assert "en" in codes
    assert "te" in codes
    assert "hi" in codes
    assert "ml" in codes

def test_reading_content_all_languages_and_levels():
    for lang_code in ["en", "te", "hi", "ml"]:
        for level in ["basic", "word_sentence", "passage", "free"]:
            response = client.get(f"/api/reading/content/{lang_code}?level={level}")
            assert response.status_code == 200, f"Failed for {lang_code} {level}"
            data = response.json()
            assert data["language_code"] == lang_code
            assert len(data["items"]) > 0

def test_sravaani_asr_layer():
    # Test valid audio input with expected hint
    audio_sample = "UklGRiQAAABXQVZFZm10IBAAAAABAAEARKwAAIhYAQACABAAZGF0YQAAAAA="  # sample base64 audio
    payload = {
        "language_code": "te",
        "audio_b64": audio_sample
    }
    response = client.post("/api/reading/recognize?expected_hint=అమ్మ", json=payload)
    assert response.status_code == 200
    res = response.json()
    assert "success" in res

def test_sravaani_asr_empty_audio_handling():
    payload = {
        "language_code": "hi",
        "audio_b64": ""
    }
    response = client.post("/api/reading/recognize", json=payload)
    assert response.status_code == 200
    res = response.json()
    assert res["success"] is False
    assert "No audio data received" in res["error"]

def test_sravaani_asr_fallback_mode(monkeypatch):
    # Test ASR response when HF API fails or token is invalid
    monkeypatch.setenv("HF_TOKEN", "invalid_token_trigger_fallback")
    audio_sample = "UklGRiQAAABXQVZFZm10IBAAAAABAAEARKwAAIhYAQACABAAZGF0YQAAAAA="
    payload = {
        "language_code": "te",
        "audio_b64": audio_sample
    }
    response = client.post("/api/reading/recognize?expected_hint=అమ్మ", json=payload)
    assert response.status_code == 200
    res = response.json()
    assert "success" in res

def test_reading_assessment_accuracy():
    # Accurate match
    payload = {
        "language_code": "en",
        "level": "word_sentence",
        "expected_text": "The cat sat on the mat",
        "recognized_transcript": "The cat sat on the mat"
    }
    response = client.post("/api/reading/assess", json=payload)
    assert response.status_code == 200
    res = response.json()
    assert res["is_correct"] is True
    assert res["accuracy_score"] == 100.0
    assert len(res["errors"]) == 0
    assert "screening tool" in res["disclaimer"]

def test_reading_assessment_mispronunciation_detection():
    # Mispronunciation / error detection
    payload = {
        "language_code": "en",
        "level": "word_sentence",
        "expected_text": "The cat sat on the mat",
        "recognized_transcript": "The dog sat on the mat"
    }
    response = client.post("/api/reading/assess", json=payload)
    assert response.status_code == 200
    res = response.json()
    assert res["is_correct"] is False
    assert res["accuracy_score"] < 100.0
    assert len(res["errors"]) > 0

def test_reading_assessment_telugu_mispronunciation_detection():
    # Telugu mispronunciation / wrong word detection
    payload = {
        "language_code": "te",
        "level": "word_sentence",
        "expected_text": "అమ్మ పాలు ఇచ్చింది.",
        "recognized_transcript": "అమ్మ నీళ్ళు ఇచ్చింది."
    }
    response = client.post("/api/reading/assess", json=payload)
    assert response.status_code == 200
    res = response.json()
    assert res["is_correct"] is False
    assert res["accuracy_score"] < 100.0
    assert "pronunciation_score" in res
    assert len(res["errors"]) > 0

def test_phoneme_gop_pronunciation_scoring():
    # Test Goodness of Pronunciation (GOP) phoneme assessment model integration
    payload = {
        "language_code": "en",
        "level": "word_sentence",
        "expected_text": "Apple",
        "recognized_transcript": "Apple"
    }
    response = client.post("/api/reading/assess", json=payload)
    assert response.status_code == 200
    res = response.json()
    assert res["is_correct"] is True
    assert res["accuracy_score"] == 100.0
    assert res["pronunciation_score"] >= 80.0

def test_conversational_tutor_feedback():
    assessment_data = {
        "is_correct": False,
        "accuracy_score": 65.0,
        "recognized_transcript": "The dog sat",
        "expected_text": "The cat sat",
        "errors": [
            {
                "token": "cat",
                "error_type": "mispronounced",
                "expected": "cat",
                "got": "dog",
                "tip": "Pay attention to 'cat'. You pronounced it as 'dog'."
            }
        ]
    }
    payload = {
        "language_code": "en",
        "level": "word_sentence",
        "expected_text": "The cat sat",
        "recognized_transcript": "The dog sat",
        "assessment": assessment_data
    }
    response = client.post("/api/reading/tutor", json=payload)
    assert response.status_code == 200
    res = response.json()
    assert "Good effort" in res["message"] or "cat" in res["message"]
    assert res["action_suggested"] == "retry"

def test_process_full_reading_pipeline():
    audio_sample = "UklGRiQAAABXQVZFZm10IBAAAAABAAEARKwAAIhYAQACABAAZGF0YQAAAAA="
    payload = {
        "language_code": "te",
        "level": "word_sentence",
        "expected_text": "అమ్మ పాలు ఇచ్చింది.",
        "audio_b64": audio_sample
    }
    response = client.post("/api/reading/process-full", json=payload)
    assert response.status_code == 200
    res = response.json()
    assert "success" in res
    assert "asr" in res
    assert "assessment" in res
    assert "tutor" in res

def test_websocket_stream_reading_mode():
    with client.websocket_connect("/ws/reading/stream") as websocket:
        websocket.send_json({
            "language_code": "hi",
            "level": "passage",
            "expected_text": "भारत हमारा देश है।",
            "audio_b64": "UklGRiQAAABXQVZFZm10IBAAAAABAAEARKwAAIhYAQACABAAZGF0YQAAAAA="
        })
        data = websocket.receive_json()
        assert "event" in data
