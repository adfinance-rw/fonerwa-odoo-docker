odoo.define('your_module.custom_datepicker_limit', function (require) {
    'use strict';

    var FieldDate = require('web.basic_fields').FieldDate;
    var field_registry = require('web.field_registry');

    var LimitedDatePicker = FieldDate.extend({
        _renderEdit: function () {
            this._super.apply(this, arguments);

            var today = moment().endOf('day');
            if (this.$input) {
                this.$input.attr('max', today.format('YYYY-MM-DD'));
            }
        },
    });

    field_registry.add('limited_date', LimitedDatePicker);
});