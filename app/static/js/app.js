class WritingTutor {
  constructor() {
    this.currentStep = 'mode-select';
    this.selectedLanguage = null;
    this.letterTemplate = null;
    this.userStrokes = [];
    this.currentStroke = [];
    this.isDrawing = false;
    this.animating = false;

    this.initDOM();
    this.initEvents();
  }

  initDOM() {
    this.steps = {
      mode: document.getElementById('step-mode'),
      language: document.getElementById('step-language'),
      practice: document.getElementById('step-practice')
    };

    this.languageGrid = document.getElementById('languageGrid');
    this.currentCharDisplay = document.getElementById('currentCharDisplay');

    this.demoCanvas = document.getElementById('demoCanvas');
    this.userCanvas = document.getElementById('userCanvas');

    this.demoCtx = this.demoCanvas.getContext('2d');
    this.userCtx = this.userCanvas.getContext('2d');

    this.feedbackBanner = document.getElementById('feedbackBanner');
    this.demoBtn = document.getElementById('demoBtn');
    this.submitBtn = document.getElementById('submitBtn');
    this.clearBtn = document.getElementById('clearBtn');
  }

  initEvents() {
    // Mode Selection
    document.getElementById('btn-mode-write').addEventListener('click', () => {
      this.loadLanguagesAndShow();
    });

    document.getElementById('btn-back-mode').addEventListener('click', () => {
      this.goToStep('mode');
    });

    document.getElementById('btn-back-lang').addEventListener('click', () => {
      this.goToStep('language');
    });

    // Practice controls
    this.demoBtn.addEventListener('click', () => this.playDemonstration());
    this.clearBtn.addEventListener('click', () => this.clearUserCanvas());
    this.submitBtn.addEventListener('click', () => this.evaluateWriting());

    // User Canvas Drawing Events
    this.setupDrawingEvents();
  }

  goToStep(stepName) {
    Object.values(this.steps).forEach(step => step.classList.remove('active'));
    if (stepName === 'mode') this.steps.mode.classList.add('active');
    if (stepName === 'language') this.steps.language.classList.add('active');
    if (stepName === 'practice') this.steps.practice.classList.add('active');
  }

  async loadLanguagesAndShow() {
    try {
      this.goToStep('language');
      this.languageGrid.innerHTML = '<p>Loading languages...</p>';

      const response = await fetch('/api/languages');
      if (!response.ok) throw new Error('Failed to load supported languages');

      const languages = await response.json();
      this.renderLanguageGrid(languages);
    } catch (err) {
      this.languageGrid.innerHTML = `<p style="color: var(--error-color)">${err.message}</p>`;
    }
  }

  renderLanguageGrid(languages) {
    this.languageGrid.innerHTML = '';
    
    const icons = {
      en: '🔤',
      te: 'తె',
      ml: 'മ',
      hi: 'अ'
    };

    languages.forEach(lang => {
      const btn = document.createElement('button');
      btn.className = 'option-btn';
      btn.innerHTML = `
        <span class="icon">${icons[lang.language_code] || '🌐'}</span>
        <span>${lang.language_name}</span>
      `;
      btn.addEventListener('click', () => {
        this.selectedLanguage = lang.language_code;
        this.selectLanguageAndStart(lang.language_code);
      });
      this.languageGrid.appendChild(btn);
    });
  }

  async selectLanguageAndStart(langCode) {
    try {
      this.showFeedback('Loading character data...', 'info');
      const response = await fetch(`/api/languages/${langCode}/characters`);
      if (!response.ok) throw new Error('Failed to load language character data');

      const characters = await response.json();
      if (characters.length === 0) throw new Error('No character definitions found for this language');

      const firstChar = characters[0];
      await this.loadLetterAndStart(firstChar.letter_id);
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

      // UI display uses exact character glyph from backend character data
      this.currentCharDisplay.textContent = this.letterTemplate.character;

      this.goToStep('practice');
      this.resizeCanvases();
      this.clearUserCanvas();

      setTimeout(() => this.playDemonstration(), 300);
    } catch (err) {
      this.showFeedback(err.message, 'error');
    }
  }

  resizeCanvases() {
    const rect = this.userCanvas.getBoundingClientRect();
    this.demoCanvas.width = rect.width;
    this.demoCanvas.height = rect.height;
    this.userCanvas.width = rect.width;
    this.userCanvas.height = rect.height;
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
    this.userCtx.strokeStyle = '#e2e8f0';
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
    if (this.animating || !this.letterTemplate) return;
    this.animating = true;
    this.clearDemoCanvas();

    if (this.letterTemplate.is_verified === false) {
      this.showFeedback(`Note: Stroke template for '${this.letterTemplate.character}' (${this.letterTemplate.unicode}) is awaiting verified coordinates.`, 'info');
    } else {
      this.showFeedback(`Demonstrating '${this.letterTemplate.character}' stroke sequence...`, 'info');
    }

    const w = this.demoCanvas.width;
    const h = this.demoCanvas.height;
    const strokes = this.letterTemplate.strokes;

    const completedStrokes = [];

    for (let i = 0; i < strokes.length; i++) {
      const stroke = strokes[i];
      await this.animateStroke(stroke, w, h, completedStrokes);
      completedStrokes.push(stroke);
      await this.sleep(400);
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
      const totalSteps = 80;

      const animate = () => {
        if (currentStep <= totalSteps) {
          const progress = currentStep / totalSteps;

          this.clearDemoCanvas();

          // 1. Draw previously completed strokes
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

          // 2. Draw current stroke in progress
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

          // Highlight active start point and direction indicator
          this.drawPoint(this.demoCtx, start.x, start.y, '#2ecc71', 8);
          this.drawArrow(this.demoCtx, start.x, start.y, currentPoint.x, currentPoint.y);

          this.demoCtx.restore();

          currentStep++;
          requestAnimationFrame(animate);
        } else {
          // Draw full path, start point, and end point when animation completes
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
      const clientX = e.touches ? e.touches[0].clientX : e.clientX;
      const clientY = e.touches ? e.touches[0].clientY : e.clientY;
      return {
        x: clientX - rect.left,
        y: clientY - rect.top,
        t: Date.now()
      };
    };

    const startDrawing = (e) => {
      if (this.animating) return;
      e.preventDefault();
      this.isDrawing = true;
      const point = getCoords(e);
      this.currentStroke = [point];

      this.userCtx.save();
      this.userCtx.strokeStyle = '#2c3e50';
      this.userCtx.lineWidth = 8;
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

  sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
}

window.addEventListener('DOMContentLoaded', () => {
  window.app = new WritingTutor();
});
