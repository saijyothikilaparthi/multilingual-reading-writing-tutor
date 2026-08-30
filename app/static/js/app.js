class MultilingualTutorApp {
  constructor() {
    this.mode = 'writing'; // 'writing' or 'reading'
    this.selectedLanguage = 'en';

    // Writing mode state
    this.letterTemplate = null;
    this.userStrokes = [];
    this.currentStroke = [];
    this.isDrawing = false;
    this.animating = false;

    // Reading mode state
    this.readingLevel = 'basic';
    this.readingItems = [];
    this.readingIndex = 0;
    this.isListening = false;
    this.mediaRecorder = null;
    this.audioChunks = [];
    this.websocket = null;

    this.initDOM();
    this.initEvents();
  }

  initDOM() {
    this.steps = {
      mode: document.getElementById('step-mode'),
      language: document.getElementById('step-language'),
      practice: document.getElementById('step-practice'),
      reading: document.getElementById('step-reading')
    };

    this.languageGrid = document.getElementById('languageGrid');
    this.languageSelectTitle = document.getElementById('languageSelectTitle');

    // Writing DOM
    this.currentCharDisplay = document.getElementById('currentCharDisplay');
    this.demoCanvas = document.getElementById('demoCanvas');
    this.userCanvas = document.getElementById('userCanvas');
    this.demoCtx = this.demoCanvas.getContext('2d');
    this.userCtx = this.userCanvas.getContext('2d');
    this.feedbackBanner = document.getElementById('feedbackBanner');
    this.demoBtn = document.getElementById('demoBtn');
    this.submitBtn = document.getElementById('submitBtn');
    this.clearBtn = document.getElementById('clearBtn');

    // Reading DOM
    this.readingLangDisplay = document.getElementById('readingLangDisplay');
    this.readingLevelBadge = document.getElementById('readingLevelBadge');
    this.readingItemCounter = document.getElementById('readingItemCounter');
    this.readingTargetText = document.getElementById('readingTargetText');
    this.readingTransliteration = document.getElementById('readingTransliteration');
    this.btnReadingDemo = document.getElementById('btnReadingDemo');
    this.btnMicStart = document.getElementById('btnMicStart');
    this.btnMicStop = document.getElementById('btnMicStop');
    this.micBtnText = document.getElementById('micBtnText');
    this.readingStatusBanner = document.getElementById('readingStatusBanner');
    this.asrTranscriptText = document.getElementById('asrTranscriptText');
    this.tutorResponseCard = document.getElementById('tutorResponseCard');
    this.tutorMessageText = document.getElementById('tutorMessageText');
    this.tutorEncouragementText = document.getElementById('tutorEncouragementText');
    this.btnPlayTutorVoice = document.getElementById('btnPlayTutorVoice');
    this.btnPrevReadingItem = document.getElementById('btnPrevReadingItem');
    this.btnNextReadingItem = document.getElementById('btnNextReadingItem');
  }

  initEvents() {
    // Mode Selection Buttons
    document.getElementById('btn-mode-write').addEventListener('click', () => {
      this.mode = 'writing';
      this.loadLanguagesAndShow();
    });

    document.getElementById('btn-mode-read').addEventListener('click', () => {
      this.mode = 'reading';
      this.loadLanguagesAndShow();
    });

    document.getElementById('btn-back-mode').addEventListener('click', () => {
      this.goToStep('mode');
    });

    document.getElementById('btn-back-lang').addEventListener('click', () => {
      this.goToStep('language');
    });

    document.getElementById('btn-back-reading-lang').addEventListener('click', () => {
      this.goToStep('language');
    });

    this.nextLetterBtn = document.getElementById('nextLetterBtn');
    if (this.nextLetterBtn) {
      this.nextLetterBtn.addEventListener('click', () => this.goToNextLetter());
    }

    // Writing Controls
    if (this.demoBtn) this.demoBtn.addEventListener('click', () => this.playDemonstration());
    if (this.clearBtn) this.clearBtn.addEventListener('click', () => this.clearUserCanvas());
    if (this.submitBtn) this.submitBtn.addEventListener('click', () => this.evaluateWriting());
    this.setupDrawingEvents();

    // Reading Level Tabs
    const levelTabs = document.querySelectorAll('.level-tab');
    levelTabs.forEach(tab => {
      tab.addEventListener('click', (e) => {
        levelTabs.forEach(t => t.classList.remove('active'));
        e.currentTarget.classList.add('active');
        this.readingLevel = e.currentTarget.dataset.level;
        this.loadReadingContent();
      });
    });

    // Reading Demo & Mic Controls
    if (this.btnReadingDemo) {
      this.btnReadingDemo.addEventListener('click', () => this.playReadingDemo());
    }
    this.btnMicStart.addEventListener('click', () => this.startListening());
    this.btnMicStop.addEventListener('click', () => this.stopListening());
    if (this.btnPlayTutorVoice) {
      this.btnPlayTutorVoice.addEventListener('click', () => this.speakTutorFeedback());
    }

    // Reading Item Navigation
    if (this.btnPrevReadingItem) {
      this.btnPrevReadingItem.addEventListener('click', () => {
        if (this.readingIndex > 0) {
          this.readingIndex--;
          this.renderCurrentReadingItem();
        }
      });
    }

    if (this.btnNextReadingItem) {
      this.btnNextReadingItem.addEventListener('click', () => {
        if (this.readingIndex < this.readingItems.length - 1) {
          this.readingIndex++;
          this.renderCurrentReadingItem();
        }
      });
    }
  }

  goToStep(stepName) {
    Object.values(this.steps).forEach(step => step.classList.remove('active'));
    if (stepName === 'mode') this.steps.mode.classList.add('active');
    if (stepName === 'language') this.steps.language.classList.add('active');
    if (stepName === 'practice') this.steps.practice.classList.add('active');
    if (stepName === 'reading') this.steps.reading.classList.add('active');
  }

  async loadLanguagesAndShow() {
    try {
      this.goToStep('language');
      this.languageSelectTitle.textContent = this.mode === 'writing' ? 'Select Writing Language' : 'Select Reading Language';
      this.languageGrid.innerHTML = '<p>Loading languages...</p>';

      const url = this.mode === 'writing' ? '/api/languages' : '/api/reading/languages';
      const response = await fetch(url);
      if (!response.ok) throw new Error('Failed to load supported languages');

      const languages = await response.json();
      this.renderLanguageGrid(languages);
    } catch (err) {
      this.languageGrid.innerHTML = `<p style="color: var(--error-color)">${err.message}</p>`;
    }
  }

  renderLanguageGrid(languages) {
    this.languageGrid.innerHTML = '';
    const icons = { en: '🔤', te: 'తె', ml: 'മ', hi: 'अ' };

    languages.forEach(lang => {
      const btn = document.createElement('button');
      btn.className = 'option-btn';
      btn.innerHTML = `
        <span class="icon">${icons[lang.language_code] || '🌐'}</span>
        <span>${lang.language_name}</span>
      `;
      btn.addEventListener('click', () => {
        this.selectedLanguage = lang.language_code;
        if (this.mode === 'writing') {
          this.selectLanguageAndStartWriting(lang.language_code);
        } else {
          this.selectLanguageAndStartReading(lang.language_code, lang.language_name);
        }
      });
      this.languageGrid.appendChild(btn);
    });
  }

  // --- WRITING MODE (Preserved Exact Logic) ---
  async selectLanguageAndStartWriting(langCode) {
    try {
      this.showFeedback('Loading character data...', 'info');
      const response = await fetch(`/api/languages/${langCode}/characters`);
      if (!response.ok) throw new Error('Failed to load language character data');

      this.characters = await response.json();
      if (!this.characters || this.characters.length === 0) throw new Error('No character definitions found for this language');

      this.currentCharIndex = 0;
      this.selectedCharacter = this.characters[this.currentCharIndex];
      await this.loadLetterAndStart(this.selectedCharacter.letter_id);
    } catch (err) {
      this.showFeedback(err.message, 'error');
    }
  }

  async loadLetterAndStart(letterId) {
    try {
      this.showFeedback('Loading template...', 'info');
      const response = await fetch(`/api/templates/${letterId}`);
      if (!response.ok) throw new Error('Failed to load character template');

      this.letterTemplate = await response.json();
      this.currentCharDisplay.textContent = this.letterTemplate.character;

      this.goToStep('practice');
      this.resizeCanvases();
      this.clearUserCanvas();

      setTimeout(() => this.playDemonstration(), 300);
    } catch (err) {
      this.showFeedback(err.message, 'error');
    }
  }

  goToNextLetter() {
    if (!this.characters || this.characters.length === 0) return;
    this.currentCharIndex = (this.currentCharIndex + 1) % this.characters.length;
    this.selectedCharacter = this.characters[this.currentCharIndex];
    this.clearUserCanvas();
    this.loadLetterAndStart(this.selectedCharacter.letter_id);
  }

  resizeCanvases() {
    this.demoCanvas.width = 320;
    this.demoCanvas.height = 320;
    this.userCanvas.width = 320;
    this.userCanvas.height = 320;
  }

  clearDemoCanvas() {
    this.demoCtx.clearRect(0, 0, this.demoCanvas.width, this.demoCanvas.height);
  }

  clearUserCanvas() {
    this.userCtx.clearRect(0, 0, this.userCanvas.width, this.userCanvas.height);
    this.userStrokes = [];
    this.hideFeedback();
    this.drawBackgroundGuide();
  }

  drawBackgroundGuide() {
    const w = this.userCanvas.width;
    const h = this.userCanvas.height;

    this.userCtx.save();
    this.userCtx.strokeStyle = '#cbd5e1';
    this.userCtx.lineWidth = 1;
    this.userCtx.setLineDash([5, 5]);

    [0.2, 0.5, 0.8].forEach(yRatio => {
      this.userCtx.beginPath();
      this.userCtx.moveTo(0, h * yRatio);
      this.userCtx.lineTo(w, h * yRatio);
      this.userCtx.stroke();
    });

    this.userCtx.restore();
  }

  async playDemonstration() {
    if (!this.letterTemplate) return;
    this.animating = true;
    this.demoCtx.clearRect(0, 0, this.demoCanvas.width, this.demoCanvas.height);

    if (this.letterTemplate.is_verified === false) {
      this.showFeedback(`Note: Stroke template for '${this.letterTemplate.character}' (${this.letterTemplate.unicode}) is awaiting verified coordinates.`, 'info');
    } else {
      this.showFeedback(`Demonstrating '${this.letterTemplate.character}' stroke sequence...`, 'info');
    }

    const w = this.demoCanvas.width || 320;
    const h = this.demoCanvas.height || 320;
    const strokes = this.letterTemplate.strokes || [];
    const completedStrokes = [];

    for (let i = 0; i < strokes.length; i++) {
      const stroke = strokes[i];
      await this.animateStroke(stroke, w, h, completedStrokes);
      completedStrokes.push(stroke);
      await this.sleep(200);
    }

    this.showFeedback(`Now your turn! Draw '${this.letterTemplate.character}' on the canvas.`, 'info');
    this.animating = false;
  }

  animateStroke(refStroke, w, h, completedStrokes = []) {
    return new Promise(resolve => {
      const start = { x: refStroke.start.x * w, y: refStroke.start.y * h };
      const end = { x: refStroke.end.x * w, y: refStroke.end.y * h };
      const waypoints = refStroke.points.map(p => ({ x: p.x * w, y: p.y * h }));

      let currentStep = 0;
      const totalSteps = 40;

      const animate = () => {
        if (currentStep <= totalSteps) {
          const progress = currentStep / totalSteps;
          this.demoCtx.clearRect(0, 0, this.demoCanvas.width, this.demoCanvas.height);

          completedStrokes.forEach(prevStroke => {
            const pStart = { x: prevStroke.start.x * w, y: prevStroke.start.y * h };
            const pEnd = { x: prevStroke.end.x * w, y: prevStroke.end.y * h };
            const pWaypoints = prevStroke.points.map(p => ({ x: p.x * w, y: p.y * h }));

            this.demoCtx.save();
            this.demoCtx.strokeStyle = '#4a90e2';
            this.demoCtx.lineWidth = 6;
            this.demoCtx.lineCap = 'round';
            this.demoCtx.lineJoin = 'round';
            this.demoCtx.beginPath();
            this.demoCtx.moveTo(pStart.x, pStart.y);
            pWaypoints.forEach(pt => this.demoCtx.lineTo(pt.x, pt.y));
            this.demoCtx.stroke();
            this.demoCtx.restore();

            this.drawPoint(this.demoCtx, pStart.x, pStart.y, '#2ecc71', 6);
            this.drawPoint(this.demoCtx, pEnd.x, pEnd.y, '#e74c3c', 6);
          });

          const currentPoint = this.interpolatePath(waypoints, progress);
          this.demoCtx.save();
          this.demoCtx.strokeStyle = '#357abd';
          this.demoCtx.lineWidth = 7;
          this.demoCtx.lineCap = 'round';
          this.demoCtx.lineJoin = 'round';
          this.demoCtx.beginPath();
          this.demoCtx.moveTo(start.x, start.y);

          const pathSubLength = (waypoints.length - 1) * progress;
          const segmentIndex = Math.floor(pathSubLength);
          for (let i = 1; i <= segmentIndex && i < waypoints.length; i++) {
            this.demoCtx.lineTo(waypoints[i].x, waypoints[i].y);
          }
          this.demoCtx.lineTo(currentPoint.x, currentPoint.y);
          this.demoCtx.stroke();

          this.drawPoint(this.demoCtx, start.x, start.y, '#2ecc71', 8);
          this.drawArrow(this.demoCtx, start.x, start.y, currentPoint.x, currentPoint.y);
          this.demoCtx.restore();

          currentStep++;
          requestAnimationFrame(animate);
        } else {
          this.demoCtx.save();
          this.demoCtx.strokeStyle = '#4a90e2';
          this.demoCtx.lineWidth = 6;
          this.demoCtx.lineCap = 'round';
          this.demoCtx.lineJoin = 'round';
          this.demoCtx.beginPath();
          this.demoCtx.moveTo(start.x, start.y);
          waypoints.forEach(pt => this.demoCtx.lineTo(pt.x, pt.y));
          this.demoCtx.stroke();
          this.demoCtx.restore();

          this.drawPoint(this.demoCtx, start.x, start.y, '#2ecc71', 8);
          this.drawPoint(this.demoCtx, end.x, end.y, '#e74c3c', 8);
          resolve();
        }
      };
      animate();
    });
  }

  interpolatePath(waypoints, progress) {
    if (waypoints.length === 0) return { x: 0, y: 0 };
    if (waypoints.length === 1 || progress <= 0) return waypoints[0];
    if (progress >= 1) return waypoints[waypoints.length - 1];

    const totalSegments = waypoints.length - 1;
    const scaledProgress = progress * totalSegments;
    const index = Math.floor(scaledProgress);
    const segmentProgress = scaledProgress - index;

    const p1 = waypoints[index];
    const p2 = waypoints[Math.min(index + 1, waypoints.length - 1)];

    return {
      x: p1.x + (p2.x - p1.x) * segmentProgress,
      y: p1.y + (p2.y - p1.y) * segmentProgress
    };
  }

  drawPoint(ctx, x, y, color, radius) {
    ctx.save();
    ctx.fillStyle = color;
    ctx.beginPath();
    ctx.arc(x, y, radius, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();
  }

  drawArrow(ctx, fromX, fromY, toX, toY) {
    ctx.save();
    ctx.fillStyle = '#f5a623';
    ctx.beginPath();
    ctx.arc(toX, toY, 6, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();
  }

  setupDrawingEvents() {
    const getCoords = (e) => {
      const rect = this.userCanvas.getBoundingClientRect();
      const clientX = e.touches && e.touches.length > 0 ? e.touches[0].clientX : e.clientX;
      const clientY = e.touches && e.touches.length > 0 ? e.touches[0].clientY : e.clientY;
      const scaleX = this.userCanvas.width / (rect.width || 320);
      const scaleY = this.userCanvas.height / (rect.height || 320);
      return {
        x: (clientX - rect.left) * scaleX,
        y: (clientY - rect.top) * scaleY,
        t: Date.now()
      };
    };

    const startDrawing = (e) => {
      e.preventDefault();
      this.isDrawing = true;
      const point = getCoords(e);
      this.currentStroke = [point];

      this.userCtx.save();
      this.userCtx.strokeStyle = '#000000';
      this.userCtx.lineWidth = 12;
      this.userCtx.lineCap = 'round';
      this.userCtx.lineJoin = 'round';
      this.userCtx.beginPath();
      this.userCtx.moveTo(point.x, point.y);
    };

    const draw = (e) => {
      if (!this.isDrawing) return;
      e.preventDefault();
      const point = getCoords(e);
      this.currentStroke.push(point);
      this.userCtx.lineTo(point.x, point.y);
      this.userCtx.stroke();
    };

    const stopDrawing = (e) => {
      if (!this.isDrawing) return;
      this.isDrawing = false;
      this.userCtx.restore();

      if (this.currentStroke.length > 0) {
        this.userStrokes.push({ points: this.currentStroke });
        this.currentStroke = [];
      }
    };

    this.userCanvas.addEventListener('pointerdown', startDrawing);
    this.userCanvas.addEventListener('pointermove', draw);
    this.userCanvas.addEventListener('pointerup', stopDrawing);
    this.userCanvas.addEventListener('pointerleave', stopDrawing);

    this.userCanvas.addEventListener('mousedown', startDrawing);
    this.userCanvas.addEventListener('mousemove', draw);
    this.userCanvas.addEventListener('mouseup', stopDrawing);
    this.userCanvas.addEventListener('mouseleave', stopDrawing);

    this.userCanvas.addEventListener('touchstart', startDrawing);
    this.userCanvas.addEventListener('touchmove', draw);
    this.userCanvas.addEventListener('touchend', stopDrawing);
  }

  async evaluateWriting() {
    if (this.userStrokes.length === 0) {
      this.showFeedback(`Please write '${this.letterTemplate?.character || ''}' before submitting.`, 'error');
      return;
    }

    try {
      this.showFeedback('Evaluating your writing...', 'info');
      const payload = {
        letter_id: this.letterTemplate.letter_id,
        user_strokes: this.userStrokes,
        canvas_width: this.userCanvas.width,
        canvas_height: this.userCanvas.height
      };

      const response = await fetch('/api/evaluate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (!response.ok) throw new Error('Evaluation failed.');
      const result = await response.json();

      if (result.success) {
        this.showFeedback(`🎉 ${result.message} (Accuracy: ${result.score}%)`, 'success');
      } else {
        this.showFeedback(`❌ ${result.message}`, 'error');
      }
    } catch (err) {
      this.showFeedback(err.message, 'error');
    }
  }

  showFeedback(msg, type) {
    this.feedbackBanner.textContent = msg;
    this.feedbackBanner.className = `feedback-banner show ${type}`;
  }

  hideFeedback() {
    this.feedbackBanner.className = 'feedback-banner';
    this.feedbackBanner.textContent = '';
  }


  // --- READING MODE IMPLEMENTATION ---

  async selectLanguageAndStartReading(langCode, langName) {
    this.selectedLanguage = langCode;
    this.readingLangDisplay.textContent = langName || langCode.toUpperCase();
    this.goToStep('reading');
    this.loadReadingContent();
  }

  async loadReadingContent() {
    try {
      this.readingTargetText.textContent = 'Loading content...';
      const url = `/api/reading/content/${this.selectedLanguage}?level=${this.readingLevel}`;
      const response = await fetch(url);
      if (!response.ok) throw new Error('Failed to load reading materials');

      const data = await response.json();
      this.readingItems = data.items || [];
      this.readingIndex = 0;
      this.renderCurrentReadingItem();
    } catch (err) {
      this.readingTargetText.textContent = 'Error loading content';
      this.readingTransliteration.textContent = err.message;
    }
  }

  renderCurrentReadingItem() {
    if (!this.readingItems || this.readingItems.length === 0) {
      this.readingTargetText.textContent = 'No materials available';
      this.readingTransliteration.textContent = '';
      return;
    }

    const item = this.readingItems[this.readingIndex];
    this.readingLevelBadge.textContent = this.formatLevelName(this.readingLevel);
    this.readingItemCounter.textContent = `Item ${this.readingIndex + 1} / ${this.readingItems.length}`;
    
    // Free Reading Mode: hide target text and demo button, show conversational prompt
    if (this.readingLevel === 'free') {
      this.readingTargetText.textContent = '🗣️ Free Reading & Conversational Tutor';
      this.readingTransliteration.textContent = item.display_text || 'Talk or read anything freely! The voice tutor will listen and respond to you.';
      if (this.btnReadingDemo) this.btnReadingDemo.style.display = 'none';
    } else {
      this.readingTargetText.textContent = item.display_text;
      this.readingTransliteration.textContent = item.transliteration || '';
      if (this.btnReadingDemo) {
        this.btnReadingDemo.style.display = 'inline-block';
        this.btnReadingDemo.disabled = false;
      }
    }

    // Reset feedback display & status
    this.asrTranscriptText.textContent = 'Click mic and speak clearly...';
    this.tutorResponseCard.style.display = 'none';
    if (this.readingStatusBanner) {
      this.readingStatusBanner.style.display = 'none';
      this.readingStatusBanner.textContent = '';
      this.readingStatusBanner.className = 'feedback-banner';
    }

    // Button states - cycle Next Item button across all characters/items
    if (this.btnNextReadingItem) {
      this.btnNextReadingItem.disabled = false;
    }
  }

  playReadingDemo() {
    if (this.readingLevel === 'free') return;
    const item = this.readingItems[this.readingIndex];
    if (!item) return;

    const textToSpeak = item.display_text || item.expected_text;
    if (!textToSpeak) return;

    this.speakText(textToSpeak, this.selectedLanguage);
  }

  speakText(text, langCode = 'en') {
    if (!('speechSynthesis' in window)) return;

    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    
    // Ensure voices are loaded (handling Chrome's async voice loading)
    let voices = window.speechSynthesis.getVoices();
    if (!voices || voices.length === 0) {
      window.speechSynthesis.onvoiceschanged = () => {
        this.speakText(text, langCode);
      };
      return;
    }

    const langMap = {
      en: ['en-IN', 'en-GB', 'en-US'],
      te: ['te-IN', 'te'],
      hi: ['hi-IN', 'hi'],
      ml: ['ml-IN', 'ml']
    };
    const preferredLangs = langMap[langCode] || ['en-IN', 'en-US'];

    let matchedVoice = null;
    for (const targetLang of preferredLangs) {
      matchedVoice = voices.find(v => v.lang === targetLang || v.lang.startsWith(targetLang) || v.lang.replace('_', '-').startsWith(targetLang));
      if (matchedVoice) break;
    }

    if (!matchedVoice) {
      // Fallback: search by language prefix
      matchedVoice = voices.find(v => v.lang.startsWith(langCode));
    }

    if (matchedVoice) {
      utterance.voice = matchedVoice;
      utterance.lang = matchedVoice.lang;
    } else {
      utterance.lang = preferredLangs[0];
    }

    // Natural child-friendly speech rate (0.85 - 0.9x speed)
    utterance.rate = 0.88;
    utterance.pitch = 1.05;

    window.speechSynthesis.speak(utterance);
  }

  speakTutorFeedback() {
    if (this.currentTutorVoiceText) {
      this.speakText(this.currentTutorVoiceText, this.selectedLanguage);
    }
  }

  formatLevelName(level) {
    const names = {
      basic: 'Basic (Letter/Character)',
      word_sentence: 'Word / Sentence Level',
      passage: 'Textbook Passage',
      free: 'Free Reading Mode'
    };
    return names[level] || level;
  }

  async startListening() {
    if (this.isListening) return;

    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      alert('Microphone access is not supported on this browser or origin.');
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      this.isListening = true;
      this.btnMicStart.style.display = 'none';
      this.btnMicStop.style.display = 'inline-block';
      this.micBtnText.textContent = 'Listening... Speak now!';
      this.asrTranscriptText.textContent = '🎙️ Listening to your voice...';

      this.audioChunks = [];
      this.mediaRecorder = new MediaRecorder(stream);
      this.mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          this.audioChunks.push(event.data);
        }
      };

      this.mediaRecorder.onstop = () => {
        const audioBlob = new Blob(this.audioChunks, { type: 'audio/webm' });
        this.processRecordedAudio(audioBlob);
      };

      this.mediaRecorder.start();

      // Open WebSocket connection for real-time streaming updates if in passage/word level
      this.connectWebSocket();
    } catch (err) {
      alert(`Microphone permission error or connection failure: ${err.message}`);
      this.stopListening();
    }
  }

  stopListening() {
    this.isListening = false;
    this.btnMicStart.style.display = 'inline-block';
    this.btnMicStop.style.display = 'none';
    this.micBtnText.textContent = 'Click to Read Aloud';

    if (this.mediaRecorder && this.mediaRecorder.state !== 'inactive') {
      this.mediaRecorder.stop();
    }
    if (this.websocket) {
      this.websocket.close();
      this.websocket = null;
    }
  }

  connectWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/reading/stream`;
    
    try {
      this.websocket = new WebSocket(wsUrl);
      this.websocket.onerror = (err) => {
        console.warn('WebSocket streaming unavailable, using REST audio processing fallback.');
        if (this.websocket) {
          try { this.websocket.close(); } catch (_) {}
          this.websocket = null;
        }
      };
      this.websocket.onopen = () => {
        const item = this.readingItems[this.readingIndex] || {};
        this.websocket.send(JSON.stringify({
          language_code: this.selectedLanguage,
          level: this.readingLevel,
          expected_text: item.expected_text || '',
          audio_b64: "c3RyZWFtX2F1ZGlvX2RhdGE=" // sample chunk
        }));
      };

      this.websocket.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.event === 'transcription_update') {
          this.renderTutorFeedback(data.asr, data.assessment, data.tutor);
        }
      };
    } catch (e) {
      console.warn('WebSocket stream error fallback to REST:', e);
    }
  }

  async processRecordedAudio(audioBlob) {
    // 1. Try browser Web Speech API (SpeechRecognition) for instant client-side ASR if available
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognition) {
      try {
        const currentItem = this.readingItems[this.readingIndex] || {};
        const langMap = { en: 'en-US', te: 'te-IN', hi: 'hi-IN', ml: 'ml-IN' };
        
        const recognition = new SpeechRecognition();
        recognition.lang = langMap[this.selectedLanguage] || 'en-US';
        recognition.interimResults = false;
        recognition.maxAlternatives = 1;

        this.asrTranscriptText.textContent = 'Processing speech with Web Speech ASR...';

        let recognizedText = '';
        recognition.onresult = (event) => {
          if (event.results && event.results[0] && event.results[0][0]) {
            recognizedText = event.results[0][0].transcript;
          }
        };

        recognition.onend = async () => {
          if (recognizedText) {
            // Evaluate speech via backend assessment service
            await this.evaluateRecognizedTranscript(recognizedText, currentItem);
            return;
          }
          // Fallback to backend ASR if WebSpeech did not return transcript
          this.processRecordedAudioBackend(audioBlob);
        };

        recognition.onerror = () => {
          this.processRecordedAudioBackend(audioBlob);
        };

        recognition.start();
        return;
      } catch (e) {
        console.warn('Web Speech API start error, falling back to backend ASR:', e);
      }
    }

    // 2. Fallback to Backend SraVaani ASR if Web Speech API is unavailable
    this.processRecordedAudioBackend(audioBlob);
  }

  async evaluateRecognizedTranscript(recognizedText, currentItem) {
    try {
      const assessRes = await fetch('/api/reading/assess', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          language_code: this.selectedLanguage,
          level: this.readingLevel,
          expected_text: currentItem.expected_text || '',
          recognized_transcript: recognizedText
        })
      });

      const assessment = await assessRes.json();

      const tutorRes = await fetch('/api/reading/tutor', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          language_code: this.selectedLanguage,
          level: this.readingLevel,
          expected_text: currentItem.expected_text || '',
          recognized_transcript: recognizedText,
          assessment: assessment
        })
      });

      const tutor = await tutorRes.json();

      const asr = {
        transcript: recognizedText,
        service_used: 'Browser Web Speech ASR'
      };

      this.renderTutorFeedback(asr, assessment, tutor);
    } catch (err) {
      console.error('Evaluation error:', err);
    }
  }

  async processRecordedAudioBackend(audioBlob) {
    const reader = new FileReader();
    reader.readAsDataURL(audioBlob);
    reader.onloadend = async () => {
      const base64Audio = reader.result.split(',')[1];
      const currentItem = this.readingItems[this.readingIndex] || {};

      try {
        this.asrTranscriptText.textContent = 'Processing speech with SraVaani ASR...';
        
        const response = await fetch('/api/reading/process-full', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            language_code: this.selectedLanguage,
            level: this.readingLevel,
            expected_text: currentItem.expected_text || '',
            audio_b64: base64Audio
          })
        });

        if (!response.ok) throw new Error('Speech recognition server error');
        const resData = await response.json();

        if (resData.success) {
          this.renderTutorFeedback(resData.asr, resData.assessment, resData.tutor);
        } else {
          // System/ASR technical failure - clearly distinguish technical error from reading error
          this.asrTranscriptText.textContent = `⚠️ System/ASR Technical Error: ${resData.error || 'Audio processing failed.'}`;
          if (this.readingStatusBanner) {
            this.readingStatusBanner.textContent = `⚙️ Technical Error: ${resData.error || 'Speech recognition engine unreachable'}`;
            this.readingStatusBanner.className = 'feedback-banner show error';
            this.readingStatusBanner.style.display = 'block';
          }
        }
      } catch (err) {
        this.asrTranscriptText.textContent = `⚠️ Error: ${err.message}`;
      }
    };
  }

  renderTutorFeedback(asr, assessment, tutor) {
    this.asrTranscriptText.textContent = `"${asr.transcript}" (Service: ${asr.service_used})`;
    this.tutorMessageText.textContent = tutor.message;
    this.tutorEncouragementText.textContent = tutor.encouragement;
    this.tutorResponseCard.style.display = 'block';

    // Status Banner for SUCCESS / ERROR
    if (this.readingStatusBanner) {
      if (assessment.is_correct) {
        this.readingStatusBanner.textContent = `🎉 SUCCESS! Word Accuracy: ${assessment.accuracy_score}% | Pronunciation Score (GOP): ${assessment.pronunciation_score || 100}%`;
        this.readingStatusBanner.className = 'feedback-banner show success';
      } else {
        this.readingStatusBanner.textContent = `💡 Practice Needed! Word Accuracy: ${assessment.accuracy_score}% | Pronunciation Score: ${assessment.pronunciation_score || 0}%`;
        this.readingStatusBanner.className = 'feedback-banner show error';
      }
      this.readingStatusBanner.style.display = 'block';
    }

    // Play Voice Feedback from Tutor
    this.currentTutorVoiceText = tutor.audio_feedback_text || `${tutor.message} ${tutor.encouragement}`;
    this.speakTutorFeedback();
  }

  sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
}

window.addEventListener('DOMContentLoaded', () => {
  window.app = new MultilingualTutorApp();
});
