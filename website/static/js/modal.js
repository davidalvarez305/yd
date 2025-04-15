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

export class ModalHelper {
    constructor({ modalTrigger = '.modalTrigger', modalSelector = '.modalContainer', closeButtonSelector = '.closeModal', displayStyle = '', onClose = null } = {}) {
        this.modalSelector = modalSelector;
        this.closeButtonSelector = closeButtonSelector;
        this.displayStyle = displayStyle;
        this.globalOnClose = onClose;
        this.modals = [];
        
        this.scanForTriggers(modalTrigger);
    }

    register({ modalId, closeButtonSelector, displayStyle, onClose }) {
        if (!modalId) {
            console.warn("Attempted to register a modal without a modal id.");
            return null;
        }
    
        if (this.get(modalId)) {
            console.warn(`Modal with ID ${modalId} is already registered.`);
            return null;
        }

        const modalElement = document.getElementById(modalId);

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

    scanForTriggers(modalTrigger) {
        const triggers = document.querySelectorAll(modalTrigger);
        
        triggers.forEach(element => {
            const modalId = element.dataset.modalId;

            if (!modalId) return;

            element.addEventListener('click', () => {
                const modal = this.get(modalId);

                if (!modal) {
                    console.error(`Modal with ID '${modalId}' not found.`);
                    return;
                }

                try {
                    modal.open();
                } catch (error) {
                    console.error(`Failed to open modal with ID '${modalId}':`, error);
                }
            });
        });
    }

    closeActiveModals() {
        this.modals.forEach(modal => modal.close());
    }
}

window.ModalHelper = ModalHelper;