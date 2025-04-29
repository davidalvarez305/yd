import { AudioHandler } from "./AudioHandler.js";

/**
 * @param {AudioHandler} audioHandler
 */
export class AudioControls {
    constructor(audioHandler) {
        this.audioHandler = audioHandler;

        this.beginBtn = document.querySelector(".beginRecording");
        this.pauseBtn = document.querySelector(".pauseRecording");
        this.resumeBtn = document.querySelector(".resumeRecording");
        this.stopBtn = document.querySelector(".stopRecording");
    }

    toggleRecordingControls(show) {
        [this.pauseBtn, this.resumeBtn, this.stopBtn].forEach(btn => {
            if (!btn) return;
            btn.classList.toggle("hidden", !show);
        });
    }

    handlePlayAudio(btn) {
        const src = btn.dataset.src;
        if (!src) throw new Error('Message missing "data-src" attribute.');
        this.audioHandler.playMessage(src);
    }

    handlePauseAudio(btn) {
        const src = btn.dataset.src;
        if (!src) throw new Error('Message missing "data-src" attribute.');
        this.audioHandler.handlePauseAudio(src);
    }

    handleStopAudio(btn) {
        const src = btn.dataset.src;
        if (!src) throw new Error('Message missing "data-src" attribute.');
        this.audioHandler.handleStopAudio(src);
    }

    handleAdjustAudioRate(btn) {
        const src = btn.dataset.src;
        const rate = parseFloat(btn.dataset.rate || "1.0");
        if (!src) throw new Error('Message missing "data-src" attribute.');
        if (isNaN(rate)) throw new Error('Invalid or missing "data-rate" attribute.');
        this.audioHandler.handleAdjustAudioRate(src, rate);
    }

    handleBeginRecording() {
        this.audioHandler.handleBeginRecording();
        this.toggleRecordingControls(true);
        this._handleShowIsRecording(true);
    }

    handlePauseRecording() {
        this.audioHandler.handlePauseRecording();
        this._handleShowIsRecording(false);
    }

    handleResumeRecording() {
        this.audioHandler.handleResumeRecording();
        this._handleShowIsRecording(true);
    }

    handleStopRecording() {
        this.audioHandler.handleStopRecording(file => {
            const dataTransfer = new DataTransfer();
            dataTransfer.items.add(file);

            const messageMedia = document.getElementById("messageMedia");
            if (messageMedia) {
                messageMedia.files = dataTransfer.files;
            }
        });

        this.toggleRecordingControls(false);
        this._handleShowIsRecording(false);
    }

    scanAudioControlButtons() {
        const buttonBindings = [
            ['.playAudio',       btn => this.handlePlayAudio(btn)],
            ['.pauseAudio',      btn => this.handlePauseAudio(btn)],
            ['.stopAudio',       btn => this.handleStopAudio(btn)],
            ['.adjustAudioRate', btn => this.handleAdjustAudioRate(btn)],
        ];

        buttonBindings.forEach(([selector, handler]) => {
            document.querySelectorAll(selector).forEach(button => {
                button.addEventListener("click", event => {
                    handler(event.currentTarget);
                });
            });
        });

        if (this.beginBtn) {
            this.beginBtn.addEventListener("click", () => this.handleBeginRecording());
        }
        if (this.pauseBtn) {
            this.pauseBtn.addEventListener("click", () => this.handlePauseRecording());
        }
        if (this.resumeBtn) {
            this.resumeBtn.addEventListener("click", () => this.handleResumeRecording());
        }
        if (this.stopBtn) {
            this.stopBtn.addEventListener("click", () => this.handleStopRecording());
        }
    }

    _handleShowIsRecording(show) {
        if (!this.beginBtn) return;
        const svg = this.beginBtn.querySelector("svg");
        if (svg) {
            svg.classList.toggle("text-primary", show);
        }
    }
}