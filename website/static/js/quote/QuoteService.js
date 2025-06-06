export function createQuoteServiceFactory({ service = null, quote = null, units = 0, price = 0.00 }) {
    return new QuoteService({
        service: service,
        quote: quote,
        units: units,
        price_per_unit: price,
    });
};

export class QuoteService {
    constructor({ service = null, quote = null, units = 0, price_per_unit = 0.00 }) {
        this.service = service;
        this.quote = quote;
        this.units = units;
        this.price_per_unit = price_per_unit;

        this._formFields = ['service', 'quote', 'units', 'price_per_unit'];
    }

    generate() {
        let data = {};

        for (const [key, value] of Object.entries(this)) {
            data[key] = value;
        }

        return data;
    }

    set(key, value) {
        if (!this._formFields.includes(key)) throw new Error(`Invalid property: ${key}.`);

        this[key] = value;
    }
}