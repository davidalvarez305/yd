import { createServiceFactory } from "./Service.js";

export default class Quote {
    constructor() {
        this.services = [];
        this.state = new Map();

        this._inputFields = ['hours', 'guests'];
        this._editableFields = ['unit', 'price'];
        this.formMapper = {
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
            this._updateFormFields(service);
        });
    }

    _handleChangeService(input) {
        const index = input.selectedIndex;
        if (!index) return;

        const option = input.options[index];
        const service = createServiceFactory({ ...option.dataset });

        this.services.push(service);
        this._updateFormFields(service);
    }

    _updateFormFields(service) {
        for (const [key, field] of this._cachedFields.entries()) {
            const value = service[key];
            if (value != null) field.value = String(value);
        }
    }

    _serializeService(service) {
        const obj = {};

        for (const [key, mapping] of Object.entries(this.formMapper)) {
            const modelField = mapping.model;
            const value = service[key];

            if (value != null) {
                obj[modelField] = value;
            }
        }

        return obj;
    }

    getData() {
        const data = new FormData();

        for (const [key, input] of this.state.entries()) {
            if (input?.value != null) {
                data.set(key, input.value);
            }
        }

        const serialized = this.services.map(service => this._serializeService(service));
        data.set('quote_services', JSON.stringify(serialized));

        return data;
    }
}

document.addEventListener('DOMContentLoaded', function () {
    const quote = new Quote();
    quote._scanWebPage();
});
