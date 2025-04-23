import Modal from "./Modal.js";

class ModalHelper {
    constructor({ modalTrigger = '.modalTrigger', modalSelector = '.modalContainer', closeButtonSelector = '.closeModal', displayStyle = '', onClose = null } = {}) {
        this.modalSelector = modalSelector;
        this.closeButtonSelector = closeButtonSelector;
        this.displayStyle = displayStyle;
        this.globalOnClose = onClose;
        this.modalTrigger = modalTrigger;
        this.modals = new Map();
    }

    register({ modalId, closeButtonSelector, displayStyle, onClose }) {
        if (!modalId) {
            console.warn("Attempted to register a modal without a modal id.");
            return null;
        }

        const element = document.getElementById(modalId);
        if (!element) {
            console.warn(`Modal element with ID ${modalId} not found in the DOM.`);
            return null;
        }

        const modal = new Modal({
            element,
            closeButtonSelector: closeButtonSelector ?? this.closeButtonSelector,
            displayStyle: displayStyle ?? this.displayStyle,
            onClose: onClose ?? this.globalOnClose
        });

        this.modals.set(modalId, modal);
    }

    get(modalId) {
        return this.modals.get(modalId);
    }

    _scanForTriggers() {
        const triggers = document.querySelectorAll(this.modalTrigger);

        triggers.forEach(element, function() {
            const modalId = element.dataset.modalId;
            if (!modalId) return;

            element.addEventListener('click', () => _handleOpenModal(modalId));
        });
    }

    _handleOpenModal(modalId) {
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
    }

    _handleCloseModal(modalId) {
        const modal = this.get(modalId);

        if (!modal) {
            console.error(`Modal with ID '${modalId}' not found.`);
            return;
        }

        try {
            modal.close();
        } catch (error) {
            console.error(`Failed to open modal with ID '${modalId}':`, error);
        }
    }

    closeActiveModals() {
        this.modals.forEach(modal => modal.close());
    }
}

document.addEventListener("DOMContentLoaded", function() {
    window.modalHelper = new ModalHelper();

    modalHelper._scanForTriggers();
});

// Re-bind modal methods after HTMX swaps elements
document.body.addEventListener('htmx:afterSwap', (e) => {
    modalHelper._scanForTriggers();
});