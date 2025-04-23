import { AudioHandler } from "./AudioHandler.js";

/**
* @param {AudioHandler} audioHandler
*/
export class AudioControls {
    constructor(audioHandler) {
        this.audioHandler = audioHandler;
        this._scanAudioControlButtons();
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
    }

    handlePauseRecording() {
        this.audioHandler.handlePauseRecording();
    }

    handleStopRecording() {
        this.audioHandler.handleStopRecording();
    }

    handleResumeRecording() {
        this.audioHandler.handleResumeRecording();
    }

    _scanAudioControlButtons() {
        const buttonBindings = [
            ['.playAudio',       btn => this.handlePlayAudio(btn)],
            ['.pauseAudio',      btn => this.handlePauseAudio(btn)],
            ['.stopAudio',       btn => this.handleStopAudio(btn)],
            ['.adjustAudioRate', btn => this.handleAdjustAudioRate(btn)],
            ['.beginRecording',  () => this.handleBeginRecording()],
            ['.pauseRecording',  () => this.handlePauseRecording()],
            ['.stopRecording',   () => this.handleStopRecording()],
            ['.resumeRecording', () => this.handleResumeRecording()],
        ];

        buttonBindings.forEach(([selector, handler]) => {
            const buttons = document.querySelectorAll(selector);
            buttons.forEach(button =>
                button.addEventListener("click", (e) => handler(e?.currentTarget ?? e))
            );
        });
    }
}