/** @odoo-module **/

import { registry } from "@web/core/registry";

const fieldRegistry = registry.category("fields");
// In Odoo 18 the registry entry is an object, e.g. { component: DateField, ... }
const { component: BaseDateField } = fieldRegistry.get("date");

/**
 * LimitedDateField
 *
 * Backend date widget that prevents selecting a date in the future by
 * configuring the underlying datepicker `maxDate` option.
 */
export class LimitedDateField extends BaseDateField {
    /**
     * Extend the base datepicker options to set a `maxDate` equal to today.
     * This is the modern equivalent of adding `max="YYYY-MM-DD"` on the input.
     */
    get datepickerOptions() {
        const options = { ...super.datepickerOptions };

        // Compute today's date (no time component) in the local timezone
        const today = new Date();
        today.setHours(0, 0, 0, 0);

        // Flatpickr (used by Odoo) accepts a JS Date instance for maxDate
        options.maxDate = today;

        return options;
    }
}

// Register the widget so it can be used with widget="limited_date"
// In Odoo 18 the registry expects a config object: { component, props, ... }
fieldRegistry.add("limited_date", { component: LimitedDateField });
