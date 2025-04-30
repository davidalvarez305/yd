import { Recording } from "./Recording.js";

export class AudioHandler {
    constructor() {
        this.recording = new Recording();
        this.mediaRecorder = null;
        this.stream = null;
    }

    async init() {
        try {
            this.stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            this._createMediaRecorder();
        } catch (error) {
            console.error("Error accessing audio stream:", error);
        }
    }

    _createMediaRecorder() {
        this.mediaRecorder = new MediaRecorder(this.stream);
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

        const blob = this.recording.pause();
        callback(blob);
    }

    handleResumeRecording() {
        if (this.mediaRecorder.state === "paused") {
            this.mediaRecorder.resume();
        }
    }

    handleStopRecording(callback) {
        if (!this.mediaRecorder) throw new Error("No MediaRecorder instance available.");

        this.mediaRecorder.onstop = () => {
            const file = this.recording.stop();
            callback(file);
            this.recording.reset();
            this._createMediaRecorder();
        };

        this.mediaRecorder.stop();
    }

    handleDeleteRecording() {
        this.recording.reset();
        this._createMediaRecorder();
    }

    getRecorderState() {
        return this.mediaRecorder?.state || 'inactive';
    }
}