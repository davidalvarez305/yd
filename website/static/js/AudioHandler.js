class Recording {
    constructor() {
        this.audioChunks = [];
        this.audioBlob = null;
        this.audioFile = null;
    }

    reset() {
        this.audioChunks = [];
        this.audioBlob = null;
        this.audioFile = null;
    }

    generateFromChunks() {
        this.audioBlob = new Blob(this.audioChunks, { type: 'audio/webm' });
        this.audioFile = new File([this.audioBlob], `recording-${Date.now()}.webm`, { type: 'audio/webm' });
    }
}

/**
 * @param {MediaRecorder} mediaRecorder
 * @param {Recording} recording
 */
export class AudioHandler {
    audioMessages = [];

    constructor(mediaRecorder, recording) {
        this.mediaRecorder = mediaRecorder;
        this.recording = recording;
        this.playbackRate = 1.0;
    }

    handleBeginRecording() {
        this.mediaRecorder.ondataavailable = (event) => {
            this.recording.audioChunks.push(event.data);
        };

        this.mediaRecorder.start();
    }

    handlePauseRecording() {
        if (this.mediaRecorder.state === "recording") this.mediaRecorder.pause();
    }

    handleStopRecording() {
        return new Promise((resolve, reject) => {
            if (!this.mediaRecorder) return reject("No MediaRecorder");

            this.mediaRecorder.onstop = () => {
                this.recording.generateFromChunks();
                resolve(this.recording.audioFile);
            };

            this.mediaRecorder.stop();
            this.recording.reset();
        });
    }

    handleBeginPlayback(audioElement) {
        if (audioElement && this.recording.audioBlob) {
            const url = URL.createObjectURL(this.recording.audioBlob);
            audioElement.src = url;
            audioElement.playbackRate = this.playbackRate;
            audioElement.play();
        }
    }

    handlePausePlayback(audioElement) {
        audioElement?.pause();
    }

    handleStopPlayback(audioElement) {
        if (audioElement) {
            audioElement.pause();
            audioElement.currentTime = 0;
        }
    }

    handleAdjustPlaybackRate(audioElement, speed) {
        if (audioElement && speed > 0) {
            this.playbackRate = speed;
            audioElement.playbackRate = speed;
        }
    }

    addAudioMessage(message) {
        this.addAudioMessage.push(message);
    }
}