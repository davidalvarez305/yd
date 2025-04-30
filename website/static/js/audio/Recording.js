import { AudioMessage } from './AudioMessage.js';

export class Recording extends AudioMessage {
    constructor(audioPlayer) {
        super(null, audioPlayer);
        this.audioChunks = [];
        this.audioBlob = null;
        this.file = null;
    }

    addChunk(chunk) {
        this.audioChunks.push(chunk);
    }

    reset() {
        this.audioChunks = [];
        this.audioBlob = null;
        this.file = null;
    }

    generateBlobAndFile() {
        this.audioBlob = new Blob(this.audioChunks, { type: 'audio/webm' });
        this.file = new File(
            [this.audioBlob],
            `recording-${Date.now()}.webm`,
            { type: 'audio/webm' }
        );
    }

    generatePreview() {
        if (!this.audioBlob) this.generateBlobAndFile();

        return URL.createObjectURL(this.audioBlob);
    }

    getFile() {
        if (!this.file) this.generateBlobAndFile();

        return this.file;
    }
}