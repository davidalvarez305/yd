class ModalHelper {
    constructor() {
        this.modals = document.querySelectorAll('.modalContainer');
        this.closeButtons = document.querySelectorAll('.closeModal');
        
        this.addEventListeners();
    }

    addEventListeners() {
        this.closeButtons.forEach(button => {
            button.addEventListener('click', (e) => this.closeModal(e));
        });
    }

    openModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) modal.style.display = '';
    }

    closeModal(event) {
        const modal = event.target.closest('.modalContainer');
        if (modal)  modal.style.display = 'none';
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const modalHelper = new ModalHelper();
});