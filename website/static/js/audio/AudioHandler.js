export class AudioHandler {
    audioMessages = [];

    constructor(mediaRecorder) {
        this.mediaRecorder = mediaRecorder;
        this.recording = null;
        this.playbackRate = 1.0;
    }

    handleBeginRecording() {
        this.mediaRecorder.ondataavailable = (event) => this.recording.addChunk(event.data);

        this.mediaRecorder.start();
    }

    handlePauseRecording() {
        if (this.mediaRecorder.state === "recording") this.mediaRecorder.pause();
    }

    handleResumeRecording() {
        if (this.mediaRecorder.state === "paused") this.mediaRecorder.resume();
    }

    handleStopRecording(cb) {
        if (typeof cb !== "function") throw new Error("Callback must be of type function.");

        if (!this.mediaRecorder || !this.recording) throw new Error("No MediaRecorder or Recording instance found.");

        this.mediaRecorder.onstop = () => {
            this.recording.generateBlobAndFile();
            cb(this.recording.file);
        };

        this.mediaRecorder.stop();
    }

    handlePreviewRecording() {
        if (!this.recording) return;

        const audioMessage = this.recording.generatePreview();
        this.registerAudioMessage(audioMessage);
    }

    playMessage(index) {
        const message = this.audioMessages.at(index);

        if (!message) return;

        message.adjustRate(this.playbackRate);
        message.play();
    }

    handlePauseAudio(index) {
        const message = this.audioMessages.at(index);
        if (message) message.pause();
    }

    handleStopAudio(index) {
        const message = this.audioMessages.at(index);
        if (message) message.stop();
    }

    handleAdjustAudioRate(index, rate) {
        const message = this.audioMessages.at(index);

        if (!message || rate < 0) return;

        this.playbackRate = rate;
        message.adjustRate(rate);
    }

    registerAudioMessage(audioMessage) {
        this.audioMessages.push(audioMessage);
    }
}