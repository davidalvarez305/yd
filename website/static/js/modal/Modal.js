export default class Modal {
    constructor({
        element,
        closeButtonSelector = '.closeModal',
        displayStyle = 'block',
        onClose = null,
        closeOnOutsideClick = true,
    }) {
        if (!element) {
            throw new Error("Modal initialization failed: 'element' is required.");
        }

        this.modal = element;
        this.closeButtonSelector = closeButtonSelector;
        this.displayStyle = displayStyle;
        this.onClose = onClose;
        this.closeOnOutsideClick = closeOnOutsideClick;

        this.boundOutsideClickListener = (e) => this._handleOutsideClick(e);

        this.closeButtons = this.modal.querySelectorAll(this.closeButtonSelector);
        this._addEventListeners();
    }

    _addEventListeners() {
        this.closeButtons.forEach(button => {
            button.addEventListener('click', (e) => this.close(e));
        });

        if (this.closeOnOutsideClick) {
            document.addEventListener('click', this.boundOutsideClickListener);
        }
    }

    _removeEventListeners() {
        if (this.closeOnOutsideClick) {
            document.removeEventListener('click', this.boundOutsideClickListener);
        }
    }

    _handleOutsideClick(event) {
        if (!this.modal.contains(event.target)) {
            this.close(event);
        }
    }

    open() {
        this.modal.style.display = this.displayStyle;
    }

    close(event = null) {
        this.modal.style.display = 'none';
        this._removeEventListeners();

        if (typeof this.onClose === 'function') {
            this.onClose(event);
        }
    }

    setOnClose(callback) {
        if (typeof callback === 'function') {
            this.onClose = callback;
        } else {
            throw new Error("setOnClose requires a function as an argument.");
        }
    }
}