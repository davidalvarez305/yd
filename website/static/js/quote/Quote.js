import { createServiceOptionFactory } from "./Service.js";

export default class Quote {
    constructor() {
        this.state = new Map();
        this._variableFormFields = new Map();

        this._initFormFields();
    }

    _initFormFields() {
        ['units', 'price'].forEach(id => {
            const el = document.getElementById(id);
            if (el) this._variableFormFields.set(id, el);
        });
    }

    _scanWebPage() {
        ['hours', 'guests'].forEach(key => {
            const el = document.getElementById(key);
            
            if (!el) throw new Error(`Could not find ${key} element.`);

            this.state.set(key, el);
        });

        const service = document.getElementById('service');
        
        if (!service) throw new Error('Could not find service input.');

        service.addEventListener('change', event => this._handleChangeService(event.target));
    }

    _handleChangeService(input) {
        const option = input.options[input.selectedIndex];
        if (!option.dataset.id) throw new Error('Could not find selected option.');

        const guests = this.state.get('guests').value;
        const hours = this.state.get('hours').value;

        const service = createServiceOptionFactory({ ...option.dataset });

        const { units, price } = service.calculate(guests, hours);

        this._fillFormFields({ units, price });
    }

    _fillFormFields(data) {
        for (const [key, field] of this._variableFormFields.entries()) {
            if (data[key]) field.value = String(data[key]);
        }
    }
}

document.addEventListener('DOMContentLoaded', function () {
    const quote = new Quote();
    quote._scanWebPage();
});
