export class AudioHandler {
    audioMessages = [];
    playbackRate = 1.0;

    constructor(mediaRecorder, recording) {
        this.originalStream = mediaRecorder.stream;
        this.recording = recording;
        this._createNewMediaRecorder();
    }

    _createNewMediaRecorder() {
        this.mediaRecorder = new MediaRecorder(this.originalStream);
        this.mediaRecorder.ondataavailable = (event) => {
            if (event.data && event.data.size > 0) {
                this.recording.addChunk(event.data);
            }
        };
    }

    // === Recording Controls ===

    handleBeginRecording() {
        this.mediaRecorder.start();
    }

    handlePauseRecording(callback) {
        if (this.mediaRecorder.state === "recording") {
            this.mediaRecorder.pause();
        }

        this.mediaRecorder.addEventListener("dataavailable", (event) => {
            if (!event.data || event.data.size === 0) return;

            this.recording.addChunk(event.data);
            this.recording.generateBlobAndFile();
            const previewUrl = this.recording.generatePreview();
            callback(previewUrl);
        }, { once: true });

        this.mediaRecorder.requestData();
    }

    handleResumeRecording() {
        if (this.mediaRecorder.state === "paused") {
            this.mediaRecorder.resume();
        }
    }

    handleStopRecording(callback) {
        if (typeof callback !== "function") throw new Error("Callback must be a function.");
        if (!this.mediaRecorder) throw new Error("No MediaRecorder instance available.");

        this.mediaRecorder.onstop = () => {
            this.recording.generateBlobAndFile();
            callback(this.recording.file);
            this.recording.reset();
            this._createNewMediaRecorder();
        };

        this.mediaRecorder.stop();
    }

    handleDeleteRecording() {
        this.recording.reset();
        this._createNewMediaRecorder();
    }

    getRecorderState() {
        return this.mediaRecorder?.state || 'inactive';
    }

    // === Audio Message Playback ===

    playMessage(index) {
        const message = this.audioMessages.at(index);
        if (!message) return;

        message.adjustRate(this.playbackRate);
        message.play();
    }

    handlePauseAudio(index) {
        this.audioMessages.at(index)?.pause();
    }

    handleStopAudio(index) {
        this.audioMessages.at(index)?.stop();
    }

    handleAdjustAudioRate(index, rate) {
        if (rate < 0) return;

        const message = this.audioMessages.at(index);
        if (!message) return;

        this.playbackRate = rate;
        message.adjustRate(rate);
    }

    registerAudioMessage(audioMessage) {
        this.audioMessages.push(audioMessage);
    }
}