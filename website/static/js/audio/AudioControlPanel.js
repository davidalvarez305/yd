import { withAudioControl } from "./withAudioControl.js";

export class AudioControlPanel {
    constructor(audioHandler) {
        this.audioHandler = audioHandler;
        this.preview = null;
        this.audioTrackList = [];

        this.beginRecordingButton = withAudioControl(document.querySelector(".beginRecording"));
        this.pauseRecordingButton = withAudioControl(document.querySelector(".pauseRecording"));
        this.stopRecordingButton = withAudioControl(document.querySelector(".stopRecording"));
        this.deleteRecordingButton = withAudioControl(document.querySelector(".deleteRecording"));
        this.audioPreviewContainer = withAudioControl(document.querySelector(".audioPreviewContainer"));
    }

    _toggleRecordingControls(show) {
        [this.pauseRecordingButton, this.stopRecordingButton].forEach(btn => {
            if (!btn?.element) return;
            show ? btn.show() : btn.hide();
        });
    }

    _resetControlPanel() {
        if (this.preview) {
            URL.revokeObjectURL(this.preview);
            this.preview = null;
        }

        this.audioPreviewContainer.hide();
        this._toggleRecordingControls(false);
        this._applyHighlight(null);
    }

    handleBeginRecording() {
        this.audioHandler.handleBeginRecording();
        this._toggleRecordingControls(true);
        this._applyHighlight(this.beginRecordingButton);
    }

    handlePauseRecording() {
        this.audioHandler.handlePauseRecording(blob => {
            if (this.preview) URL.revokeObjectURL(this.preview);
            this.preview = URL.createObjectURL(blob);

            const previewEl = document.querySelector(".audioRecordingPreview");
            if (previewEl) previewEl.src = this.preview;
        });

        this.audioPreviewContainer.show();
        this._applyHighlight(this.pauseRecordingButton);
    }
    
    handleResumeRecording() {
        this.audioHandler.handleResumeRecording();

        if (this.preview) {
            URL.revokeObjectURL(this.preview);
            this.preview = null;
        }

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
                messageMedia.dispatchEvent(new Event("change", { bubbles: true }));
            }
        });

        this._resetControlPanel();
    }

    handleDeleteRecording() {
        this.audioHandler.handleDeleteRecording();
        this._resetControlPanel();
    }

    scanAudioElements() {
        const messages = document.querySelectorAll('.audioMessage');
        messages.forEach(message => {
            if (!message || !(message instanceof HTMLAudioElement)) return;

            this.audioTrackList.push(message);
        });

        this._setupTrackAutoplay();

        this.beginRecordingButton.onClick(() => this._handleStartOrResumeRecording());
        this.pauseRecordingButton.onClick(() => this.handlePauseRecording());
        this.stopRecordingButton.onClick(() => this.handleStopRecording());
        this.deleteRecordingButton.onClick(() => this.handleDeleteRecording());
    }

    _setupTrackAutoplay() {
        this.audioTrackList.forEach((audio, index) => {
            audio.addEventListener("ended", () => {
                const next = this.audioTrackList[index + 1];
                if (next) next.play();
            });
        });
    }

    _applyHighlight(activeButton) {
        [this.beginRecordingButton, this.pauseRecordingButton].forEach(btn => {
            if (!btn?.element) return;
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