export class Chat {
    constructor(audioControlPanel, mediaControlPanel) {
        this.audioControlPanel = audioControlPanel;
        this.mediaControlPanel = mediaControlPanel;
        this.attachments = [];
    }

    clearAttachments() {
        this.attachments = [];
    }

    deleteAttachments(id) {
        const index = this.attachments.findIndex(attachment => attachment.id === id);
        if (index !== -1) {
            this.attachments.splice(index, 1);
        }
    }

    placeAttachment({ id, file }) {
        this.attachments.push({ id, file });
    }
}