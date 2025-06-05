import { createServiceFactory } from "./Service.js";

export default class Quote {
    constructor() {
        this.services = [];
        this.state = new Map();

        this._inputFields = ['hours', 'guests'];
        this._editableFields = ['unit', 'price'];
        this._cachedFields = new Map();

        this._editableFields.forEach(id => {
            const el = document.getElementById(id);
            if (el) this._cachedFields.set(id, el);
        });
    }

    _scanWebPage() {
        this._inputFields.forEach(key => {
            const el = document.getElementById(key);
            if (el) {
                this.state.set(key, el);
                el.addEventListener('change', () => this._handleFieldChange(key, el.value));
            }
        });

        const service = document.getElementById('service');
        if (service) {
            service.addEventListener('change', event => this.handleChangeService(event.target));
        }
    }

    _handleFieldChange(key, value) {
        this.state.set(key, value);

        this.services.forEach(service => {
            service.calculate(this.state.guests.value, this.state.hours.value);
            this._handleAppendFormValues(service);
        });
    }

    handleChangeService(input) {
        const index = input.selectedIndex;
        if (!index) return;

        const option = input.options[index];
        const service = createServiceFactory({ ...option.dataset });

        this.services.push(service);
        this._handleAppendFormValues(service);
    }

    _handleAppendFormValues(service) {
        for (const [key, field] of this._cachedFields.entries()) {
            const value = service[key];
            if (value != null) field.value = String(value);
        }
    }
}

document.addEventListener('DOMContentLoaded', function () {
    const quote = new Quote();
    quote._scanWebPage();
});