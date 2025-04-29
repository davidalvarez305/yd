import { AudioMessage } from "./AudioMessage";

export class RecordingPreview extends AudioMessage {
    constructor(container) {
        this.container = container;
    }

    showContainer(show) {
        this.container.classList.toggle('hidden', show);
    }
}