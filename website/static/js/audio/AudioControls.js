
import { AudioHandler } from "./AudioHandler.js";

/**
 * @param {AudioHandler} audioHandler
 */
export class AudioControls {
    constructor(audioHandler) {
        this.audioHandler = audioHandler;

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
    }

    handlePauseRecording() {
        this.audioHandler.handlePauseRecording();
    }

    handleResumeRecording() {
        this.audioHandler.handleResumeRecording();
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
    }

    scanAudioControlButtons() {
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
            buttons.forEach(button => {
                button.addEventListener("click", event => {
                    handler(event.currentTarget ?? event);
                });
            });
        });
    }
}