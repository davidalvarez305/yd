import { createServiceFactory } from "./Service.js";

const FORM_MAPPER = {
    unit: {
        html: 'unit',
        model: 'units',
    },
    price: {
        html: 'price',
        model: 'price_per_unit',
    },
    service: {
        html: 'service',
        model: 'service',
    }
};

export default class Quote {
    constructor() {
        this.services = [];
        this.state = new Map();

        

        this._variableFormFields = new Map();
        ['unit', 'price'].forEach(id => {
            const el = document.getElementById(id);
            if (el) this._variableFormFields.set(id, el);
        });
    }

    _scanWebPage() {
        ['hours', 'guests'].forEach(key => {
            const el = document.getElementById(key);
            if (el) {
                this.state.set(key, el);
                el.addEventListener('change', () => this._handleFieldChange(key, el.value));
            }
        });

        const service = document.getElementById('service');
        if (service) {
            service.addEventListener('change', event => this._handleChangeService(event.target));
        }
    }

    _handleFieldChange(key, value) {
        this.state.set(key, value);

        this.services.forEach(service => {
            service.calculate(
                this.state.get('guests')?.value,
                this.state.get('hours')?.value
            );
            this._adjustVariableInputs(service);
        });
    }

    _handleChangeService(input) {
        const index = input.selectedIndex;
        if (!index) return;

        const option = input.options[index];
        const service = createServiceFactory({ ...option.dataset });

        this.services.push(service);
        this._adjustVariableInputs(service);
    }

    _adjustVariableInputs(service) {
        for (const [key, field] of this._variableFormFields.entries()) {
            const value = service[key];
            if (value) field.value = String(value);
        }
    }

    _serializeService(service) {
        const obj = {};

        for (const [key, mapping] of Object.entries(FORM_MAPPER)) {
            const field = mapping.model;
            const value = service[key];

            if (value) obj[field] = value;
        }

        return obj;
    }

    getData() {
        const data = new FormData();

        for (const [key, input] of this.state.entries()) {
            if (input.value) data.set(key, input.value);
        }

        const serializedServices = this.services.map(service => this._serializeService(service));
        data.set('quote_services', JSON.stringify(serializedServices));

        return data;
    }
}

document.addEventListener('DOMContentLoaded', function () {
    const quote = new Quote();
    quote._scanWebPage();
});
