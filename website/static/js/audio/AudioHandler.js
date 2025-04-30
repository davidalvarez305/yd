export class AudioHandler {
    audioMessages = [];

    constructor(mediaRecorder, recording) {
        this.mediaRecorder = mediaRecorder;
        this.recording = recording;
        this.playbackRate = 1.0;

        this._initRecorder();
    }

    _handleOnDataAvailable = (event) => {
        this.recording.addChunk(event.data);
    };

    _initRecorder() {
        this.mediaRecorder.ondataavailable = this._handleOnDataAvailable;
    }

    handleBeginRecording() {
        this.mediaRecorder.start();
    }

    handleDeleteRecording() {
        this.recording.reset();

        this.mediaRecorder = new MediaRecorder(this.mediaRecorder.stream);
        this._initRecorder();
    }

    handlePauseRecording(callback) {
        if (this.mediaRecorder.state === "recording") {
            this.mediaRecorder.pause();
        }
    
        this.mediaRecorder.addEventListener("dataavailable", event => {
            if (!event.data || event.data.size === 0) return;

            this.recording.audioChunks.push(event.data);
            this.recording.generateBlobAndFile();
            const previewUrl = this.recording.generatePreview();

            callback(previewUrl);
        },
        { once: true });

        this.mediaRecorder.requestData();
    }

    handleResumeRecording() {
        if (this.mediaRecorder.state === "paused") this.mediaRecorder.resume();
    }

    handleStopRecording(callback) {
        if (typeof callback !== "function") throw new Error("Callback must be of type function.");

        if (!this.mediaRecorder) throw new Error("No MediaRecorder instance found.");

        this.mediaRecorder.onstop = () => {
            this.recording.generateBlobAndFile();
            callback(this.recording.file);
        };

        this.recording.reset();
        this.mediaRecorder.stop();
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

    getRecorderState() {
        return this.mediaRecorder?.state || 'inactive';
    }
}