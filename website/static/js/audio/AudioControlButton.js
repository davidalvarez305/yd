const HIGHLIGHT_CLASS = 'text-red-700';
const HIDDEN_CLASS = 'hidden';

export class AudioControlButton {
    constructor(element) {
        if (!element) throw new Error("AudioControlButton received an invalid or missing element.");
        this.element = element;

        this.svg = this.element.querySelector("svg");
        if (!this.svg) throw new Error("SVG icon not found in audio control button.");
    }

    show() {
        this.element.classList.remove(HIDDEN_CLASS);
    }

    hide() {
        this.element.classList.add(HIDDEN_CLASS);
    }

    highlight() {
        this.svg.classList.add(HIGHLIGHT_CLASS);
    }

    removeHighlight() {
        this.svg.classList.remove(HIGHLIGHT_CLASS);
    }

    onClick(callback) {
        this.element.addEventListener("click", callback);
    }
}