import { AudioControl } from "./AudioControl.js";

const HIGHLIGHT_CLASS = 'text-red-700';

export class AudioControlButton extends AudioControl {
    constructor(element) {
        super(element);
        this.svg = this.element.querySelector("svg");
        if (!this.svg) throw new Error("SVG icon not found in audio control button.");
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