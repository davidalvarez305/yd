export class Recording {
    constructor() {
        this.audioChunks = [];
    }

    addChunk(chunk) {
        this.audioChunks.push(chunk);
    }

    pause() {
        const blob = new Blob(this.audioChunks, { type: 'audio/webm' });

        return blob;
    }

    stop() {
        const blob = new Blob(this.audioChunks, { type: 'audio/webm' });
        const file = new File(
            [blob],
            `recording-${Date.now()}.webm`,
            { type: 'audio/webm' }
        );

        this.audioChunks = [];

        return file;
    }

    reset() {
        this.audioChunks = [];
    }
}