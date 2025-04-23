import Modal from "./Modal.js";

const MODAL_SELECTOR = '.modalContainer';
const OPEN_SELECTOR = '.openModal';
const CLOSE_SELECTOR = '.closeModal';

class ModalHelper {
    constructor({ onClose = null } = {}) {
        this.globalOnClose = onClose;
        this.modals = new Map();
        this._autoRegister();
        this._scanForTriggers();
    }

    _autoRegister() {
        const modals = document.querySelectorAll(MODAL_SELECTOR);

        modals.forEach((element) => {
            if (!element.dataset.modalId) {
                console.warn("Skipping modal registration: missing data-modal-id");
                return;
            }

            const modal = new Modal({
                element,
                onClose: this.globalOnClose,
            });

            this.modals.set(element.dataset.modalId, modal);
        });
    }

    _scanForTriggers() {
        const triggers = document.querySelectorAll(OPEN_SELECTOR);

        triggers.forEach(function(trigger) {
            if (!trigger.dataset.modalId) return;

            trigger.addEventListener('click', () => this._handleOpenModal(trigger.dataset.modalId));
        });

        const closeButtons = document.querySelectorAll(CLOSE_SELECTOR);

        closeButtons.forEach((button) => {
            if (!button.dataset.modalId) return;

            button.addEventListener('click', function(e) {
                this._handleCloseModal(button.dataset.modalId, e);
            });
        });

        document.addEventListener('click', (event) => {
            this.modals.forEach((modal, modalId) => {
                if (!modal.modal.contains(event.target)) {
                    if (modal.modal.style.display !== 'none') {
                        this._handleCloseModal(modalId, event);
                    }
                }
            });
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
            console.error(`Failed to open modal '${modalId}':`, error);
        }
    }

    _handleCloseModal(modalId, event = null) {
        const modal = this.get(modalId);
        if (!modal) {
            console.error(`Modal with ID '${modalId}' not found.`);
            return;
        }

        try {
            modal.close(event);
        } catch (error) {
            console.error(`Failed to close modal '${modalId}':`, error);
        }
    }

    get(modalId) {
        return this.modals.get(modalId);
    }
}

document.addEventListener("DOMContentLoaded", () => {
    window.modalHelper = new ModalHelper();
});

document.body.addEventListener('htmx:afterSwap', () => {
    window.modalHelper._scanForTriggers();
});