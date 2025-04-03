class Modal {
    constructor({ modalElement, closeButtonSelector = '.closeModal', displayStyle = '', onClose = null }) {
        if (!modalElement) {
            throw new Error("Modal initialization failed: 'modalElement' is required.");
        }

        this.modal = modalElement;
        this.closeButtonSelector = closeButtonSelector;
        this.displayStyle = displayStyle;
        this.onClose = onClose;

        this.closeButtons = this.modal.querySelectorAll(this.closeButtonSelector);
        this.addEventListeners();
    }

    addEventListeners() {
        this.closeButtons.forEach(button => {
            button.addEventListener('click', (e) => this.close(e));
        });
    }

    open() {
        this.modal.style.display = this.displayStyle;
    }

    close(event) {
        this.modal.style.display = 'none';

        if (typeof this.onClose === 'function') this.onClose(event);
    }

    setOnClose(callback) {
        if (typeof callback === 'function') {
            this.onClose = callback;
        } else {
            throw new Error("setOnClose requires a function as an argument.");
        }
    }
}

class ModalHelper {
    constructor({ modalSelector = '.modalContainer', closeButtonSelector = '.closeModal', displayStyle = '', onClose = null } = {}) {
        this.modalSelector = modalSelector;
        this.closeButtonSelector = closeButtonSelector;
        this.displayStyle = displayStyle;
        this.globalOnClose = onClose;
        this.modals = [];
    }

    register({ modalElement, closeButtonSelector, displayStyle, onClose }) {
        if (!modalElement) {
            console.warn("Attempted to register a modal without a modalElement.");
            return null;
        }
    
        if (this.getModalById(modalElement.id)) {
            console.warn(`Modal with ID ${modalElement.id} is already registered.`);
            return null;
        }
    
        const modal = new Modal({
            modalElement,
            closeButtonSelector: closeButtonSelector ?? this.closeButtonSelector,
            displayStyle: displayStyle ?? this.displayStyle,
            onClose: onClose ?? this.globalOnClose
        });
    
        this.modals.push(modal);
        return modal;
    }

    get(modalId) {
        return this.modals.find(m => m.modal?.id === modalId);
    }
}