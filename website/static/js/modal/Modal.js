export default class Modal {
    constructor({ element, onClose = null, onOpen = null }) {
        if (!element) {
            throw new Error("Modal initialization failed: 'element' is required.");
        }

        this.modal = element;
        this.onClose = onClose;
        this.onOpen = onOpen;
    }

    open(event = null) {
        this.modal.style.display = '';

        if (typeof this.onOpen === 'function') {
            this.onOpen(event);
        }
    }

    close(event = null) {
        this.modal.style.display = 'none';

        if (typeof this.onClose === 'function') {
            this.onClose(event);
        }
    }

    setOnOpen(callback) {
        if (typeof callback !== 'function') {
            throw new Error("setOnOpen requires a function as an argument.");
        }

        this.onOpen = callback;
    }

    setOnClose(callback) {
        if (typeof callback !== 'function') {
            throw new Error("setOnClose requires a function as an argument.");
        }

        this.onClose = callback;
    }
}