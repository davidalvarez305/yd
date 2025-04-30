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

    handleBeginRecording() {
        this.mediaRecorder.start(1000);
    }

    handlePauseRecording(callback) {
        if (this.mediaRecorder.state === "recording") {
            this.mediaRecorder.pause();
        }
    
        let blob = this.recording.pause();
        callback(blob);
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
            let file = this.recording.stop();
            callback(file);
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