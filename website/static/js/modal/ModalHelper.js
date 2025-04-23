import Modal from "./Modal.js";

const MODAL_SELECTOR = '[data-modal]';
const OPEN_SELECTOR = '.openModal';
const CLOSE_SELECTOR = '.closeModal';

class ModalHelper {
    constructor() {
        this.modals = new Map();
        this._handleScanModals();
    }

    _handleScanModals() {
        // Scan Modals
        const modals = document.querySelectorAll(MODAL_SELECTOR);

        modals.forEach((element) => {
            if (!element.dataset.modalId) {
                console.warn("Skipping modal registration: missing data-modal-id");
                return;
            }

            const modal = new Modal({ element });

            this.modals.set(element.dataset.modalId, modal);
        });

        // Scan Triggers
        const triggers = document.querySelectorAll(OPEN_SELECTOR);

        triggers.forEach((trigger) => {
            if (!trigger.dataset.modalId) return;

            trigger.addEventListener('click', () => this._handleOpenModal(trigger.dataset.modalId));
        });

        // Scan Close Buttons
        const closeButtons = document.querySelectorAll(CLOSE_SELECTOR);

        closeButtons.forEach((button) => {
            if (!button.dataset.modalId) return;

            button.addEventListener('click', (event) => {
                this._handleCloseModal(button.dataset.modalId, event);
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