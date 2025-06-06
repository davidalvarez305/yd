// service type = hourly, general, food, rental, alcohol, etc...
// unit type = per person, ratio, hourly, etc...
const BASELINE_HOURS = 4;

function assert(value, name) {
    if (value === null || value === undefined) {
        throw new Error(`${name} cannot be null or undefined.`);
    }
}

export function createServiceOptionFactory({
    serviceType,
    unitType,
    id,
    price = null,
    ratio = null,
}) {
    assert(serviceType, 'Service type');
    assert(unitType, 'Unit type');
    assert(id, 'Service ID');

    return new ServiceOption(serviceType, unitType, id, price, ratio);
}

export class ServiceOption {
    constructor(serviceType, unitType, id, price, ratio) {
        this.serviceType = serviceType;
        this.unitType = unitType;
        this.id = id;
        this.price = price;
        this.ratio = ratio;
    }

    calculate(guests, hours) {
        let form = new QuoteServiceForm();

        switch (this.unitType) {
            case 'PER_PERSON':
                return this.price * guests * (hours / BASELINE_HOURS);
            case 'HOURLY':
                let price = this.price * hours;
                let units = Math.ceil(guests / this.ratio);
                if (this.ratio) price *= Math.ceil(guests / this.ratio);
                return { units, price };
            case 'HOURLY':
                this.price = this.price * hours;
                this.units = Math.ceil(guests / this.ratio);
                return price * ratioAdjustment;
            case 'FIXED':
                return this.price;
            case 'AD_HOC':
                return this.price;
        }
    }
}