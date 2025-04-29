const HIDDEN_CLASS = 'hidden';

export class AudioControl {
    constructor(element) {
        if (!element) throw new Error("Audio Control received an invalid or missing element.");
        this.element = element;
    }

    show() {
        this.element.classList.remove(HIDDEN_CLASS);
    }

    hide() {
        this.element.classList.add(HIDDEN_CLASS);
    }
}