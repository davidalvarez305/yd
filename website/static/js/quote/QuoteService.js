export function createQuoteServiceFactory({ service = null, quote = null, units = 0, price = 0.00, id = null }) {
    return new QuoteService({
        service_id: service,
        quote_id: quote,
        units: units,
        price_per_unit: price,
        quote_service_id: id,
    });
};

export class QuoteService {
    constructor({ service_id = null, quote_id = null, units = 0, price_per_unit = 0.00, quote_service_id = null }) {
        this.service_id = service_id;
        this.quote_id = quote_id;
        this.units = units;
        this.price_per_unit = price_per_unit;
        this.quote_service_id = quote_service_id;
    }
}