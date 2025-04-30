import { AudioControlButton } from "./AudioControlButton.js";
import { AudioControlContainer } from "./AudioControlContainer.js";

export class AudioControlPanel {
    constructor(audioHandler) {
        this.audioHandler = audioHandler;

        this.beginRecordingButton = new AudioControlButton(document.querySelector(".beginRecording"));
        this.pauseRecordingButton = new AudioControlButton(document.querySelector(".pauseRecording"));
        this.stopRecordingButton = new AudioControlButton(document.querySelector(".stopRecording"));

        this.audioPreviewContainer = new AudioControlContainer(document.querySelector(".audioPreviewContainer"));
    }

    _toggleRecordingControls(show) {
        [this.pauseRecordingButton, this.stopRecordingButton].forEach(btn => {
            if (!btn.element) return;
            show ? btn.show() : btn.hide();
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
        this._toggleRecordingControls(true);
        this._applyHighlight(this.beginRecordingButton);
    }

    handlePauseRecording() {
        this.audioHandler.handlePauseRecording(function onPauseRecording(src) {
            let audioRecordingPreview = document.querySelector(".audioRecordingPreview");
            if (audioRecordingPreview) audioRecordingPreview.src = src;
        });
        this.audioPreviewContainer.show();
        this._applyHighlight(this.pauseRecordingButton);
    }

    handleResumeRecording() {
        this.audioHandler.handleResumeRecording();
        this.audioPreviewContainer.hide();
        this._applyHighlight(this.beginRecordingButton);
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

        this.audioHandler.recording.reset();
        this.audioPreviewContainer.hide();
        this._toggleRecordingControls(false);
        this._applyHighlight(null);
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

        this.beginRecordingButton.onClick(() => this._handleStartOrResumeRecording());
        this.pauseRecordingButton.onClick(() => this.handlePauseRecording());
        this.stopRecordingButton.onClick(() => this.handleStopRecording());
    }

    _applyHighlight(activeButton) {
        [this.beginRecordingButton, this.pauseRecordingButton].forEach(btn => {
            if (!btn) return;
            btn === activeButton ? btn.highlight() : btn.removeHighlight();
        });
    }

    _handleStartOrResumeRecording() {
        const state = this.audioHandler.getRecorderState();
    
        if (state === "paused") {
            this.handleResumeRecording();
        } else if (state === "inactive") {
            this.handleBeginRecording();
        } else {
            throw new Error(`Unexpected media recorder state: ${state}`);
        }
    }
    
}