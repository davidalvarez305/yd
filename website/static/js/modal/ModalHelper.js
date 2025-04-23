import Modal from "./Modal.js";

class ModalHelper {
    constructor({
        modalTrigger = '.modalTrigger',
        modalSelector = '.modalContainer',
        closeButtonSelector = '.closeModal',
        displayStyle = '',
        onClose = null
    } = {}) {
        this.modalTrigger = modalTrigger;
        this.modalSelector = modalSelector;
        this.defaultCloseButtonSelector = closeButtonSelector;
        this.defaultDisplayStyle = displayStyle;
        this.globalOnClose = onClose;

        this.modals = new Map();   // modalId → Modal instance
        this.configs = new Map();  // modalId → modal config object
    }

    autoRegisterModals() {
        const modalElements = document.querySelectorAll(this.modalSelector);

        modalElements.forEach((element) => {
            const modalId = element.id;
            if (!modalId) {
                console.warn("Modal element is missing an ID:", element);
                return;
            }

            const config = {
                modalId,
                closeButtonSelector: element.dataset.closeButtonSelector || this.defaultCloseButtonSelector,
                displayStyle: element.dataset.displayStyle || this.defaultDisplayStyle,
                closeOnOutsideClick: element.dataset.closeOnOutsideClick !== 'false',
                onClose: this.globalOnClose
            };

            this.register(config);
        });
    }

    register({ modalId, closeButtonSelector, displayStyle, onClose, closeOnOutsideClick = true }) {
        const element = document.getElementById(modalId);
        if (!element) {
            console.warn(`Modal element with ID ${modalId} not found.`);
            return;
        }

        const modal = new Modal({
            element,
            onClose: onClose ?? this.globalOnClose
        });

        this.modals.set(modalId, modal);

        this.configs.set(modalId, {
            closeButtonSelector,
            displayStyle,
            closeOnOutsideClick
        });
    }

    _addEventListeners(modalId) {
        const modal = this.get(modalId);
        const config = this.configs.get(modalId);
        if (!modal || !config) return;

        const closeButtons = modal.modal.querySelectorAll(config.closeButtonSelector);
        closeButtons.forEach(button => {
            button.addEventListener('click', (e) => {
                this._removeEventListeners(modalId);
                modal.close(e);
            });
        });

        if (config.closeOnOutsideClick) {
            modal.boundOutsideClickListener = (e) => this._handleOutsideClick(modalId, e);
            document.addEventListener('click', modal.boundOutsideClickListener);
        }
    }

    _removeEventListeners(modalId) {
        const modal = this.get(modalId);
        if (modal?.boundOutsideClickListener) {
            document.removeEventListener('click', modal.boundOutsideClickListener);
            modal.boundOutsideClickListener = null;
        }
    }

    _handleOutsideClick(modalId, event) {
        const modal = this.get(modalId);
        if (!modal) return;

        if (!modal.modal.contains(event.target)) {
            this._removeEventListeners(modalId);
            modal.close(event);
        }
    }

    get(modalId) {
        return this.modals.get(modalId);
    }

    _scanForTriggers() {
        const triggers = document.querySelectorAll(this.modalTrigger);

        triggers.forEach((element) => {
            const modalId = element.dataset.modalId;
            if (!modalId) return;

            element.addEventListener('click', () => this._handleOpenModal(modalId));
        });
    }

    _handleOpenModal(modalId) {
        const modal = this.get(modalId);
        const config = this.configs.get(modalId);

        if (!modal || !config) {
            console.error(`Modal with ID '${modalId}' not found.`);
            return;
        }

        modal.modal.style.display = config.displayStyle ?? '';
        this._addEventListeners(modalId);
        modal.open();
    }

    _handleCloseModal(modalId) {
        const modal = this.get(modalId);
        if (!modal) {
            console.error(`Modal with ID '${modalId}' not found.`);
            return;
        }

        this._removeEventListeners(modalId);
        modal.close();
    }

    closeActiveModals() {
        this.modals.forEach((_, modalId) => {
            this._removeEventListeners(modalId);
            this.modals.get(modalId).close();
        });
    }
}

document.addEventListener("DOMContentLoaded", function () {
    window.modalHelper = new ModalHelper();
    modalHelper.autoRegisterModals();
    modalHelper._scanForTriggers();
});

document.body.addEventListener('htmx:afterSwap', function () {
    modalHelper.autoRegisterModals();
    modalHelper._scanForTriggers();
});