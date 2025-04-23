export default class Modal {
    constructor({ element, onClose = null }) {
        if (!element) {
            throw new Error("Modal initialization failed: 'element' is required.");
        }

        this.modal = element;
        this.onClose = onClose;
    }

    open() {
        this.modal.style.display = '';
    }

    close(event = null) {
        this.modal.style.display = 'none';

        if (typeof this.onClose === 'function') {
            this.onClose(event);
        }
    }

    setOnClose(callback) {
        if (typeof callback !== 'function') {
            throw new Error("setOnClose requires a function as an argument.");
        }

        this.onClose = callback;
    }
}