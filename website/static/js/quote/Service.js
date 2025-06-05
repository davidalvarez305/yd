// service type = hourly, general, food, rental, alcohol, etc...
// unit type = per person, ratio, hourly, etc...
const BASELINE_HOURS = 4;

function assert(value, name) {
    if (value === null || value === undefined) {
        throw new Error(`${name} cannot be null or undefined.`);
    }
}

export function createServiceFactory({
    type,
    unit,
    id,
    price = null,
    ratio = null
}) {
    assert(type, 'Service type');
    assert(unit, 'Unit type');
    assert(id, 'Service ID');

    return new Service(type, unit, id, price, ratio);
}

export class Service {
    constructor(type, unit, id, price, ratio) {
        this.type = type;
        this.unit = unit;
        this.id = id;
        this.price = price;
        this.ratio = ratio;
    }

    calculate(guests, hours) {
        switch (this.unit) {
            case 'PER_PERSON':
                return this.price * guests * (hours / BASELINE_HOURS);
            case 'HOURLY':
                let rate = this.price * hours;
                if (this.ratio) rate *= Math.ceil(guests / this.ratio);
                return rate;
            case 'HOURLY':
                let price = this.price * hours;
                let ratioAdjustment = Math.ceil(guests / this.ratio);
                return price * ratioAdjustment;
            case 'FIXED':
                return this.price;
            case 'AD_HOC':
                return this.price;
        }
    }
}