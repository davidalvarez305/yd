const HIDDEN_CLASS = 'hidden';
const HIGHLIGHT_CLASS = 'text-red-700';

export function withAudioControl(element) {
    if (!element) throw new Error("Invalid element passed to withAudioControl.");

    return {
        show() {
            element.classList.remove(HIDDEN_CLASS);
        },
        hide() {
            element.classList.add(HIDDEN_CLASS);
        },
        highlight() {
            const svg = element.querySelector("svg");
            if (svg) svg.classList.add(HIGHLIGHT_CLASS);
        },
        removeHighlight() {
            const svg = element.querySelector("svg");
            if (svg) svg.classList.remove(HIGHLIGHT_CLASS);
        },
        onClick(callback) {
            element.addEventListener("click", callback);
        },
        element
    };
}
