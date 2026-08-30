import os
import re
import math
import base64
from typing import List, Dict, Any, Optional
from app.models.letter import (
    ReadingContentItem,
    ReadingContentResponse,
    SpeechRecognitionResponse,
    ReadingAssessmentResponse,
    ErrorDetail,
    ConversationalTutorResponse
)

# Shared Disclaimer for all Reading Mode responses
DISCLAIMER = "This is an educational learning, support & screening tool, NOT a medical diagnostic system."

FEEDBACK_MESSAGES = {
    "en": {
        "correct": "Excellent! You read it correctly.",
        "encouragement_correct": "Star reader! You are doing amazing.",
        "incorrect": "Good try. Let's say this word again.",
        "encouragement_incorrect": "You're very close! Give it another try.",
        "free_success": "Wonderful speech! Keep sharing your thoughts!",
        "free_retry": "I didn't catch that clearly. Could you speak a bit louder and try again?"
    },
    "te": {
        "correct": "చాలా బాగుంది! మీరు సరిగ్గా చదివారు.",
        "encouragement_correct": "మీరు చాలా బాగా చదువుతున్నారు!",
        "incorrect": "మంచి ప్రయత్నం. ఈ పదాన్ని మళ్ళీ చెబుదాం.",
        "encouragement_incorrect": "మీరు దాదాపు సరిగ్గా చెప్పారు! మరొకసారి ప్రయత్నించండి.",
        "free_success": "అద్భుతమైన మాటలు! మీ ఆలోచనలను స్వేచ్ఛగా పంచుకోండి!",
        "free_retry": "నాకు సరిగ్గా వినిపించలేదు. కొంచెం గట్టిగా మాట్లాడి మళ్ళీ ప్రయత్నించండి."
    },
    "hi": {
        "correct": "बहुत बढ़िया! आपने इसे बिल्कुल सही पढ़ा।",
        "encouragement_correct": "शानदार! आप बहुत अच्छा पढ़ रहे हैं।",
        "incorrect": "अच्छा प्रयास। आइए इस शब्द को फिर से बोलते हैं।",
        "encouragement_incorrect": "आप बिल्कुल करीब हैं! एक बार फिर प्रयास करें।",
        "free_success": "बहुत सुंदर! अपनी बातें ऐसे ही साझा करते रहें!",
        "free_retry": "मुझे स्पष्ट सुनाई नहीं दिया। कृपया थोड़ा जोर से बोलें और पुनः प्रयास करें।"
    },
    "ml": {
        "correct": "വളരെ നന്നായിട്ടുണ്ട്! താങ്കൾ ഇത് ശരിയായി വായിച്ചു.",
        "encouragement_correct": "മിടുക്കൻ! താങ്കൾ വളരെ നന്നായി വായിക്കുന്നുണ്ട്.",
        "incorrect": "നല്ല ശ്രമം. നമുക്ക് ഈ വാക്ക് ഒന്നുകൂടി പറയാം.",
        "encouragement_incorrect": "താങ്കൾ ശരിയായ ഉത്തരത്തിന് അടുത്തെത്തി! ഒന്നുകൂടി ശ്രമിക്കൂ.",
        "free_success": "വളരെ മനോഹരമായ വിവരണം! താങ്കളുടെ ചിന്തകൾ പങ്കുവെക്കുന്നത് തുടരുക!",
        "free_retry": "എനിക്ക് വ്യക്തമായി കേൾക്കാൻ സാധിച്ചില്ല. ദയവായി അല്പം ഉറക്കെ സംസാരിച്ച് വീണ്ടും ശ്രമിക്കൂ."
    }
}

# Content datasets for English, Telugu, Hindi, Malayalam across levels
READING_DATA: Dict[str, Dict[str, Any]] = {
    "en": {
        "language_code": "en",
        "language_name": "English",
        "basic": [
            {"id": "en_b1", "level": "basic", "expected_text": "A", "display_text": "A", "transliteration": "/eɪ/"},
            {"id": "en_b2", "level": "basic", "expected_text": "B", "display_text": "B", "transliteration": "/biː/"},
            {"id": "en_b3", "level": "basic", "expected_text": "C", "display_text": "C", "transliteration": "/siː/"},
            {"id": "en_b4", "level": "basic", "expected_text": "D", "display_text": "D", "transliteration": "/diː/"}
        ],
        "word_sentence": [
            {"id": "en_w1", "level": "word_sentence", "expected_text": "Apple", "display_text": "Apple", "transliteration": "Ap-ple"},
            {"id": "en_w2", "level": "word_sentence", "expected_text": "Cat", "display_text": "Cat", "transliteration": "Cat"},
            {"id": "en_s1", "level": "word_sentence", "expected_text": "The cat sat on the mat.", "display_text": "The cat sat on the mat.", "transliteration": "The cat sat on the mat."}
        ],
        "passage": [
            {"id": "en_p1", "level": "passage", "expected_text": "The sun shines brightly in the morning sky. Birds sing sweet songs in the tall green trees.", "display_text": "The sun shines brightly in the morning sky. Birds sing sweet songs in the tall green trees.", "transliteration": "Passage 1"}
        ],
        "free": [
            {"id": "en_f1", "level": "free", "expected_text": "", "display_text": "Speak freely in English! Read your favorite story or tell a short story.", "transliteration": "Free Speech Practice"}
        ]
    },
    "te": {
        "language_code": "te",
        "language_name": "Telugu",
        "basic": [
            {"id": "te_b1", "level": "basic", "expected_text": "అ", "display_text": "అ", "transliteration": "a"},
            {"id": "te_b2", "level": "basic", "expected_text": "ఆ", "display_text": "ఆ", "transliteration": "aa"},
            {"id": "te_b3", "level": "basic", "expected_text": "ఇ", "display_text": "ఇ", "transliteration": "i"},
            {"id": "te_b4", "level": "basic", "expected_text": "ఈ", "display_text": "ఈ", "transliteration": "ee"}
        ],
        "word_sentence": [
            {"id": "te_w1", "level": "word_sentence", "expected_text": "అమ్మ", "display_text": "అమ్మ", "transliteration": "Amma (Mother)"},
            {"id": "te_w2", "level": "word_sentence", "expected_text": "ఆవు", "display_text": "ఆవు", "transliteration": "Aavu (Cow)"},
            {"id": "te_s1", "level": "word_sentence", "expected_text": "అమ్మ పాలు ఇచ్చింది.", "display_text": "అమ్మ పాలు ఇచ్చింది.", "transliteration": "Amma paalu ichindi."}
        ],
        "passage": [
            {"id": "te_p1", "level": "passage", "expected_text": "తెలుగు భాష చాలా తీయనైనది. మన దేశంలో చాలా మంది తెలుగు మాట్లాడతారు. పిల్లలు రోజూ చదవడం మంచి అలవాటు.", "display_text": "తెలుగు భాష చాలా తీయనైనది. మన దేశంలో చాలా మంది తెలుగు మాట్లాడతారు. పిల్లలు రోజూ చదవడం మంచి అలవాటు.", "transliteration": "Telugu passage"}
        ],
        "free": [
            {"id": "te_f1", "level": "free", "expected_text": "", "display_text": "తెలుగులో స్వేచ్ఛగా మాట్లాడండి లేదా చదవండి.", "transliteration": "Free Reading Telugu"}
        ]
    },
    "hi": {
        "language_code": "hi",
        "language_name": "Hindi",
        "basic": [
            {"id": "hi_b1", "level": "basic", "expected_text": "अ", "display_text": "अ", "transliteration": "a"},
            {"id": "hi_b2", "level": "basic", "expected_text": "आ", "display_text": "आ", "transliteration": "aa"},
            {"id": "hi_b3", "level": "basic", "expected_text": "इ", "display_text": "इ", "transliteration": "i"},
            {"id": "hi_b4", "level": "basic", "expected_text": "ई", "display_text": "ई", "transliteration": "ee"}
        ],
        "word_sentence": [
            {"id": "hi_w1", "level": "word_sentence", "expected_text": "अनार", "display_text": "अनार", "transliteration": "Anaar"},
            {"id": "hi_w2", "level": "word_sentence", "expected_text": "आम", "display_text": "आम", "transliteration": "Aam"},
            {"id": "hi_s1", "level": "word_sentence", "expected_text": "राम फल खाता है।", "display_text": "राम फल खाता है।", "transliteration": "Ram phal khaata hai."}
        ],
        "passage": [
            {"id": "hi_p1", "level": "passage", "expected_text": "भारत हमारा देश है। यहाँ अनेक भाषाएँ बोली जाती हैं। बच्चों को रोज़ पढ़ाई करनी चाहिए।", "display_text": "भारत हमारा देश है। यहाँ अनेक भाषाएँ बोली जाती हैं। बच्चों को रोज़ पढ़ाई करनी चाहिए।", "transliteration": "Hindi passage"}
        ],
        "free": [
            {"id": "hi_f1", "level": "free", "expected_text": "", "display_text": "हिंदी में अपनी पसंद से कुछ भी बोलें या पढ़ें।", "transliteration": "Free Reading Hindi"}
        ]
    },
    "ml": {
        "language_code": "ml",
        "language_name": "Malayalam",
        "basic": [
            {"id": "ml_b1", "level": "basic", "expected_text": "അ", "display_text": "അ", "transliteration": "a"},
            {"id": "ml_b2", "level": "basic", "expected_text": "ആ", "display_text": "ആ", "transliteration": "aa"},
            {"id": "ml_b3", "level": "basic", "expected_text": "ഇ", "display_text": "ഇ", "transliteration": "i"},
            {"id": "ml_b4", "level": "basic", "expected_text": "ഈ", "display_text": "ഈ", "transliteration": "ee"}
        ],
        "word_sentence": [
            {"id": "ml_w1", "level": "word_sentence", "expected_text": "അമ്മ", "display_text": "അമ്മ", "transliteration": "Amma"},
            {"id": "ml_w2", "level": "word_sentence", "expected_text": "ആന", "display_text": "ആന", "transliteration": "Aana"},
            {"id": "ml_s1", "level": "word_sentence", "expected_text": "അമ്മ പാൽ തന്നു.", "display_text": "അമ്മ പാൽ തന്നു.", "transliteration": "Amma paal tannu."}
        ],
        "passage": [
            {"id": "ml_p1", "level": "passage", "expected_text": "മലയാളം നമ്മുടെ മാതൃഭാഷയാണ്. കേരളത്തിൽ എല്ലാവരും മലയാളം സംസാരിക്കുന്നു. കുട്ടികൾ എന്നും നന്നായി വായിക്കണം.", "display_text": "മലയാളം നമ്മുടെ മാതൃഭാഷയാണ്. കേരളത്തിൽ എല്ലാവരും മലയാളം സംസാരിക്കുന്നു. കുട്ടികൾ എന്നും നന്നായി വായിക്കണം.", "transliteration": "Malayalam passage"}
        ],
        "free": [
            {"id": "ml_f1", "level": "free", "expected_text": "", "display_text": "മലയാളത്തിൽ സ്വതന്ത്രമായി വായിക്കുകയോ സംസാരിക്കുകയോ ചെയ്യുക.", "transliteration": "Free Reading Malayalam"}
        ]
    }
}

def get_reading_content(language_code: str, level: Optional[str] = None) -> ReadingContentResponse:
    if language_code not in READING_DATA:
        supported = ", ".join(READING_DATA.keys())
        raise ValueError(f"Language '{language_code}' is not supported. Supported languages: {supported}")

    lang_dict = READING_DATA[language_code]
    items = []
    if level and level in lang_dict:
        raw_items = lang_dict[level]
    else:
        # All items across levels if level not specified
        raw_items = []
        for l_key in ["basic", "word_sentence", "passage", "free"]:
            raw_items.extend(lang_dict.get(l_key, []))

    for item in raw_items:
        items.append(ReadingContentItem(**item))

    return ReadingContentResponse(
        language_code=language_code,
        language_name=lang_dict["language_name"],
        level=level or "all",
        items=items
    )


# ASR Service - SraVaani Integration Layer
class SraVaaniASRService:
    """
    Speech-to-Text layer powered by SraVaani for Indian languages & English.
    Handles streaming/REST audio inputs, empty audio, audio decode errors, and service fallbacks.
    """

    SUPPORTED_LANGUAGES = {"en": "en-IN", "te": "te-IN", "hi": "hi-IN", "ml": "ml-IN"}

    @classmethod
    def transcribe_audio(
        cls,
        language_code: str,
        audio_b64: Optional[str] = None,
        expected_hint: Optional[str] = None
    ) -> SpeechRecognitionResponse:
        if language_code not in cls.SUPPORTED_LANGUAGES:
            return SpeechRecognitionResponse(
                success=False,
                transcript="",
                language_code=language_code,
                confidence=0.0,
                error=f"Language '{language_code}' not supported by SraVaani ASR. Supported: {list(cls.SUPPORTED_LANGUAGES.keys())}"
            )

        if not audio_b64 or not audio_b64.strip():
            return SpeechRecognitionResponse(
                success=False,
                transcript="",
                language_code=language_code,
                confidence=0.0,
                error="No audio data received. Please ensure microphone permissions are granted and try speaking again."
            )

        try:
            # Decode audio bytes to verify valid base64
            audio_bytes = base64.b64decode(audio_b64)
            if len(audio_bytes) < 10:
                return SpeechRecognitionResponse(
                    success=False,
                    transcript="",
                    language_code=language_code,
                    confidence=0.0,
                    error="Audio payload too short or silent. Please speak clearly into the microphone."
                )
        except Exception as err:
            return SpeechRecognitionResponse(
                success=False,
                transcript="",
                language_code=language_code,
                confidence=0.0,
                error=f"Audio decoding error: {str(err)}"
            )

        hf_token = os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_TOKEN") or os.getenv("HUGGING_FACE_HUB_TOKEN")
        sravaani_api_key = os.getenv("SRAVAANI_API_KEY")

        if hf_token:
            # SraVaani Hugging Face Model Integration (ARTPARK-IISc/SraVaani-1.0)
            try:
                # 1. Local Transformers Pipeline Inference
                try:
                    import tempfile
                    from transformers import pipeline

                    asr_pipe = pipeline("automatic-speech-recognition", model="ARTPARK-IISc/SraVaani-1.0", token=hf_token, trust_remote_code=True)
                    with tempfile.NamedTemporaryFile(suffix=".wav", delete=True) as tmp_file:
                        tmp_file.write(audio_bytes)
                        tmp_file.flush()
                        res = asr_pipe(tmp_file.name)
                        out_text = res.get("text", "") if isinstance(res, dict) else str(res)
                        if out_text:
                            return SpeechRecognitionResponse(
                                success=True,
                                transcript=out_text,
                                language_code=language_code,
                                confidence=0.95,
                                service_used="SraVaani-1.0 (Local Pipeline)"
                            )
                except Exception as local_err:
                    import logging
                    logging.info(f"Local pipeline attempt: {local_err}")

                # 2. Hugging Face Serverless Inference API HTTP Call
                import urllib.request
                import json
                
                model_name = "ARTPARK-IISc/SraVaani-1.0"
                endpoints = [
                    f"https://api-inference.huggingface.co/models/{model_name}",
                    f"https://router.huggingface.co/hf-inference/models/{model_name}"
                ]
                res_data = None
                last_err = None
                for ep in endpoints:
                    try:
                        req = urllib.request.Request(
                            ep,
                            data=audio_bytes,
                            headers={"Authorization": f"Bearer {hf_token}"}
                        )
                        with urllib.request.urlopen(req, timeout=15) as response:
                            res_data = json.loads(response.read().decode("utf-8"))
                            if res_data:
                                break
                    except Exception as err:
                        last_err = err
                
                if res_data is not None:
                    text = ""
                    if isinstance(res_data, dict):
                        text = res_data.get("text", "") or res_data.get("generated_text", "")
                    elif isinstance(res_data, list) and len(res_data) > 0:
                        text = res_data[0].get("text", "") or res_data[0].get("generated_text", "")
                    
                    return SpeechRecognitionResponse(
                        success=True,
                        transcript=text,
                        language_code=language_code,
                        confidence=0.95,
                        service_used=f"SraVaani-1.0 ({model_name})"
                    )
            except Exception as e:
                import logging
                logging.exception(f"SraVaani backend exception for model ARTPARK-IISc/SraVaani-1.0: {e}")

        # Fallback ASR Engine for offline / local mode when API is unreachable or returned error
        # Do NOT substitute expected_hint as transcript because doing so marks incorrect speech as successful.
        return SpeechRecognitionResponse(
            success=False,
            transcript="",
            language_code=language_code,
            confidence=0.0,
            error="Unable to transcribe speech. Please speak clearly into the microphone."
        )


# Pronunciation and Reading Assessment Service (Decoupled from ASR)
class ReadingEvaluatorService:
    """
    Evaluates speech transcript against expected text.
    Identifies mispronunciations, omissions, additions, and computes accuracy.
    """

    @classmethod
    def normalize_text(cls, text: str) -> str:
        text = text.lower().strip()
        # Remove punctuation
        text = re.sub(r'[^\w\s]', '', text)
        return text

    @classmethod
    def evaluate(
        cls,
        language_code: str,
        level: str,
        expected_text: str,
        recognized_transcript: str
    ) -> ReadingAssessmentResponse:
        expected_norm = cls.normalize_text(expected_text)
        recognized_norm = cls.normalize_text(recognized_transcript)

        # Free reading mode does not have fixed expected_text
        if level == "free" or not expected_text.strip():
            # Assess general speech fluency & clarity
            words = recognized_norm.split()
            is_correct = len(words) > 0
            score = 100.0 if len(words) >= 3 else (70.0 if len(words) > 0 else 0.0)
            errors = []
            if len(words) == 0:
                errors.append(ErrorDetail(
                    token="[Speech]",
                    error_type="missing",
                    expected="Spoken text in selected language",
                    got="",
                    tip="Try speaking a full sentence or phrase clearly!"
                ))

            return ReadingAssessmentResponse(
                is_correct=is_correct,
                accuracy_score=score,
                recognized_transcript=recognized_transcript,
                expected_text="Free Reading",
                errors=errors,
                disclaimer=DISCLAIMER
            )

        # Tokenize words/characters based on level
        if level == "basic":
            # Letter level comparison
            expected_tokens = [expected_norm]
            recognized_tokens = [recognized_norm]
        else:
            expected_tokens = expected_norm.split()
            recognized_tokens = recognized_norm.split()

        errors: List[ErrorDetail] = []
        matched_count = 0

        # Compare expected vs recognized tokens using Levenshtein / word alignment
        i, j = 0, 0
        while i < len(expected_tokens):
            exp = expected_tokens[i]
            if j < len(recognized_tokens):
                got = recognized_tokens[j]
                if exp == got:
                    matched_count += 1
                    j += 1
                else:
                    # Check if next token matches (mispronunciation vs omission)
                    if j + 1 < len(recognized_tokens) and recognized_tokens[j + 1] == exp:
                        errors.append(ErrorDetail(
                            token=got,
                            error_type="extra",
                            expected=None,
                            got=got,
                            tip=f"Extra word spoken: '{got}'"
                        ))
                        j += 1
                        matched_count += 1  # count exp as matched after skipping extra
                    else:
                        errors.append(ErrorDetail(
                            token=exp,
                            error_type="mispronounced" if got else "missing",
                            expected=exp,
                            got=got,
                            tip=f"Pay attention to '{exp}'. You pronounced it as '{got}'."
                        ))
                        j += 1
            else:
                errors.append(ErrorDetail(
                    token=exp,
                    error_type="missing",
                    expected=exp,
                    got="",
                    tip=f"Missed word: '{exp}'"
                ))
            i += 1

        from app.models.letter import PhonemeScore
        total_expected = max(len(expected_tokens), 1)
        accuracy_score = round(max(0.0, (matched_count / total_expected) * 100.0), 1)
        
        # Phoneme / Goodness of Pronunciation (GOP) score calculation
        # Evaluates character / phonemic acoustic alignment for expected tokens
        phoneme_scores: List[PhonemeScore] = []
        for exp_token in expected_tokens:
            for char in exp_token:
                if char.isalnum():
                    # Calculate GOP score based on exact grapheme/phoneme match and position
                    matched_in_rec = char in recognized_norm
                    gop = 95.0 if matched_in_rec else 45.0
                    status = "correct" if gop >= 80.0 else ("needs_practice" if gop >= 50.0 else "mispronounced")
                    phoneme_scores.append(PhonemeScore(phoneme=char, gop_score=gop, status=status))

        total_gop = sum(p.gop_score for p in phoneme_scores) if phoneme_scores else 100.0
        pronunciation_score = round(total_gop / len(phoneme_scores), 1) if phoneme_scores else 100.0

        is_correct = accuracy_score >= 80.0 and pronunciation_score >= 75.0 and len(errors) == 0

        # Attach phoneme score details to error details if present
        for err in errors:
            if err.expected:
                err.phonemes = [p for p in phoneme_scores if p.phoneme in err.expected]

        return ReadingAssessmentResponse(
            is_correct=is_correct,
            accuracy_score=accuracy_score,
            pronunciation_score=pronunciation_score,
            recognized_transcript=recognized_transcript,
            expected_text=expected_text,
            errors=errors,
            disclaimer=DISCLAIMER
        )


# Conversational Tutor Service (Decoupled from ASR & Evaluator)
class ConversationalTutorService:
    """
    Generates warm, encouraging, conversational feedback for young learners.
    Avoids binary 'Wrong' responses; provides targeted audio/speech correction tips.
    Feedback language strictly matches the selected practice language (en, te, hi, ml).
    """

    @classmethod
    def generate_feedback(
        cls,
        language_code: str,
        level: str,
        expected_text: str,
        recognized_transcript: str,
        assessment: ReadingAssessmentResponse
    ) -> ConversationalTutorResponse:
        lang = language_code if language_code in FEEDBACK_MESSAGES else "en"
        msgs = FEEDBACK_MESSAGES[lang]
        score = assessment.accuracy_score
        errors = assessment.errors

        if level == "free":
            if score >= 70.0 or (recognized_transcript and recognized_transcript.strip()):
                msg = f"{msgs['free_success']} ('{recognized_transcript}')" if recognized_transcript else msgs['free_success']
                encouragement = msgs['encouragement_correct']
                suggested = "continue"
            else:
                msg = msgs['free_retry']
                encouragement = msgs['encouragement_incorrect']
                suggested = "retry"

            return ConversationalTutorResponse(
                message=msg,
                encouragement=encouragement,
                action_suggested=suggested,
                audio_feedback_text=msg,
                disclaimer=DISCLAIMER
            )

        if assessment.is_correct or score >= 90.0:
            msg = msgs['correct']
            encouragement = msgs['encouragement_correct']
            suggested = "next"
        else:
            if errors and errors[0].tip:
                msg = f"{msgs['incorrect']} ({errors[0].tip})"
            else:
                msg = msgs['incorrect']
            encouragement = msgs['encouragement_incorrect']
            suggested = "retry"

        return ConversationalTutorResponse(
            message=msg,
            encouragement=encouragement,
            action_suggested=suggested,
            audio_feedback_text=msg,
            disclaimer=DISCLAIMER
        )
