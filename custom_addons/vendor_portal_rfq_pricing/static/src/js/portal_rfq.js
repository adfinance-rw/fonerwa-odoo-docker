/** @odoo-module **/

import { Component, onMounted, onWillUnmount, useState } from "@odoo/owl";
import publicWidget from 'web.public.widget';

/**
 * Vendor Portal RFQ Pricing Widget
 * Handles real-time price updates, validation, and user experience enhancements
 */
publicWidget.registry.VendorRFQPricing = publicWidget.Widget.extend({
    selector: '.o_portal_rfq_pricing_form',
    events: {
        'input .supplier-price-input': '_onPriceInput',
        'change .supplier-price-input': '_onPriceChange',
        'blur .supplier-price-input': '_onPriceBlur',
        'focus .supplier-price-input': '_onPriceFocus',
        'submit': '_onFormSubmit',
    },

    /**
     * Initialize the widget
     */
    start: function () {
        this._super.apply(this, arguments);
        this.currency_symbol = this.$el.find('[data-currency-symbol]').data('currency-symbol') || '$';
        this._initializePricing();
        this._setupProgressTracker();
        this._bindAutoSave();
        return Promise.resolve();
    },

    /**
     * Initialize pricing functionality
     */
    _initializePricing: function () {
        this.priceInputs = this.$el.find('.supplier-price-input');
        this.submitButton = this.$el.find('button[type="submit"]');
        this.totalDisplay = this.$el.find('#total_amount');
        
        // Set initial state
        this._updateTotalAmount();
        this._updateSubmitButton();
        this._restoreFromLocalStorage();
    },

    /**
     * Setup progress tracking
     */
    _setupProgressTracker: function () {
        const totalLines = this.priceInputs.length;
        const completedLines = this.priceInputs.filter(function () {
            return parseFloat($(this).val() || 0) > 0;
        }).length;
        
        const progress = totalLines > 0 ? (completedLines / totalLines) * 100 : 0;
        
        if (this.$el.find('.pricing-progress').length === 0) {
            const progressHtml = `
                <div class="pricing-progress mt-3">
                    <div class="d-flex justify-content-between">
                        <span>Pricing Progress</span>
                        <span class="progress-text">${completedLines}/${totalLines} lines</span>
                    </div>
                    <div class="progress mt-1">
                        <div class="progress-bar bg-success" role="progressbar" 
                             style="width: ${progress}%" aria-valuenow="${progress}" 
                             aria-valuemin="0" aria-valuemax="100"></div>
                    </div>
                </div>
            `;
            this.$el.find('.card-body').first().append(progressHtml);
        }
    },

    /**
     * Handle price input events (real-time)
     */
    _onPriceInput: function (ev) {
        const $input = $(ev.currentTarget);
        const value = parseFloat($input.val() || 0);
        const lineId = $input.data('line-id');
        const quantity = parseFloat($input.data('quantity') || 1);
        
        // Validate input
        this._validatePriceInput($input, value);
        
        // Update subtotal
        this._updateSubtotal(lineId, value, quantity);
        
        // Update total
        this._updateTotalAmount();
        
        // Update progress
        this._updateProgress();
        
        // Auto-save to localStorage
        this._saveToLocalStorage();
    },

    /**
     * Handle price change events
     */
    _onPriceChange: function (ev) {
        const $input = $(ev.currentTarget);
        const value = parseFloat($input.val() || 0);
        
        // Add visual feedback
        $input.addClass('price-updated');
        setTimeout(() => $input.removeClass('price-updated'), 1000);
        
        this._updateSubmitButton();
    },

    /**
     * Handle price blur events
     */
    _onPriceBlur: function (ev) {
        const $input = $(ev.currentTarget);
        const value = parseFloat($input.val() || 0);
        
        // Format the value
        if (value > 0) {
            $input.val(value.toFixed(2));
            $input.addClass('has-value');
        } else {
            $input.removeClass('has-value');
        }
    },

    /**
     * Handle price focus events
     */
    _onPriceFocus: function (ev) {
        const $input = $(ev.currentTarget);
        $input.select(); // Select all text for easy editing
    },

    /**
     * Validate price input
     */
    _validatePriceInput: function ($input, value) {
        $input.removeClass('is-invalid is-valid error');
        
        if (isNaN(value) || value < 0) {
            $input.addClass('is-invalid error');
            this._showInputError($input, 'Please enter a valid positive number');
        } else if (value > 0) {
            $input.addClass('is-valid has-value');
            this._clearInputError($input);
        } else {
            this._clearInputError($input);
        }
    },

    /**
     * Update subtotal for a specific line
     */
    _updateSubtotal: function (lineId, price, quantity) {
        const subtotal = price * quantity;
        const $subtotalElement = this.$el.find(`#subtotal_${lineId}`);
        
        if ($subtotalElement.length) {
            const formattedSubtotal = subtotal.toLocaleString('en-US', {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2
            });
            $subtotalElement.html(`${formattedSubtotal} ${this.currency_symbol}`);
        }
    },

    /**
     * Update total amount
     */
    _updateTotalAmount: function () {
        let total = 0;
        
        this.priceInputs.each((index, input) => {
            const $input = $(input);
            const price = parseFloat($input.val() || 0);
            const quantity = parseFloat($input.data('quantity') || 1);
            total += price * quantity;
        });
        
        if (this.totalDisplay.length) {
            const formattedTotal = total.toLocaleString('en-US', {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2
            });
            this.totalDisplay.html(formattedTotal);
        }
    },

    /**
     * Update progress tracker
     */
    _updateProgress: function () {
        const totalLines = this.priceInputs.length;
        const completedLines = this.priceInputs.filter(function () {
            return parseFloat($(this).val() || 0) > 0;
        }).length;
        
        const progress = totalLines > 0 ? (completedLines / totalLines) * 100 : 0;
        
        this.$el.find('.progress-bar').css('width', `${progress}%`).attr('aria-valuenow', progress);
        this.$el.find('.progress-text').text(`${completedLines}/${totalLines} lines`);
    },

    /**
     * Update submit button state
     */
    _updateSubmitButton: function () {
        const hasAnyPrice = this.priceInputs.filter(function () {
            return parseFloat($(this).val() || 0) > 0;
        }).length > 0;
        
        this.submitButton.prop('disabled', !hasAnyPrice);
        
        if (hasAnyPrice) {
            this.submitButton.removeClass('btn-secondary').addClass('btn-success');
            this.submitButton.html('<i class="fa fa-paper-plane"></i> Submit Pricing');
        } else {
            this.submitButton.removeClass('btn-success').addClass('btn-secondary');
            this.submitButton.html('<i class="fa fa-paper-plane"></i> Submit Pricing');
        }
    },

    /**
     * Show input error
     */
    _showInputError: function ($input, message) {
        let $errorDiv = $input.siblings('.invalid-feedback');
        if ($errorDiv.length === 0) {
            $errorDiv = $('<div class="invalid-feedback"></div>');
            $input.after($errorDiv);
        }
        $errorDiv.text(message);
    },

    /**
     * Clear input error
     */
    _clearInputError: function ($input) {
        $input.siblings('.invalid-feedback').remove();
    },

    /**
     * Handle form submission
     */
    _onFormSubmit: function (ev) {
        // Validate all inputs before submission
        let hasErrors = false;
        
        this.priceInputs.each((index, input) => {
            const $input = $(input);
            const value = parseFloat($input.val() || 0);
            
            if ($input.val() !== '' && (isNaN(value) || value < 0)) {
                this._validatePriceInput($input, value);
                hasErrors = true;
            }
        });
        
        if (hasErrors) {
            ev.preventDefault();
            this._showFormError('Please correct the highlighted errors before submitting.');
            return false;
        }
        
        // Show loading state
        this._showLoadingState();
        
        // Clear localStorage on successful submission
        this._clearLocalStorage();
    },

    /**
     * Show form error
     */
    _showFormError: function (message) {
        const alertHtml = `
            <div class="alert alert-danger alert-dismissible fade show" role="alert">
                <strong>Error:</strong> ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
            </div>
        `;
        this.$el.prepend(alertHtml);
        
        // Auto-dismiss after 5 seconds
        setTimeout(() => {
            this.$el.find('.alert').fadeOut();
        }, 5000);
    },

    /**
     * Show loading state
     */
    _showLoadingState: function () {
        this.submitButton.prop('disabled', true);
        this.submitButton.html('<i class="fa fa-spinner fa-spin"></i> Submitting...');
        this.$el.addClass('loading-overlay loading');
        
        const spinnerHtml = '<div class="loading-spinner"><i class="fa fa-spinner fa-spin fa-2x"></i></div>';
        this.$el.append(spinnerHtml);
    },

    /**
     * Auto-save functionality
     */
    _bindAutoSave: function () {
        // Save every 30 seconds
        this.autoSaveInterval = setInterval(() => {
            this._saveToLocalStorage();
        }, 30000);
    },

    /**
     * Save current state to localStorage
     */
    _saveToLocalStorage: function () {
        const orderId = this.$el.data('order-id');
        if (!orderId) return;
        
        const data = {};
        this.priceInputs.each((index, input) => {
            const $input = $(input);
            const lineId = $input.data('line-id');
            const value = $input.val();
            if (value) {
                data[lineId] = value;
            }
        });
        
        localStorage.setItem(`vendor_pricing_${orderId}`, JSON.stringify(data));
    },

    /**
     * Restore state from localStorage
     */
    _restoreFromLocalStorage: function () {
        const orderId = this.$el.data('order-id');
        if (!orderId) return;
        
        const savedData = localStorage.getItem(`vendor_pricing_${orderId}`);
        if (!savedData) return;
        
        try {
            const data = JSON.parse(savedData);
            Object.keys(data).forEach(lineId => {
                const $input = this.$el.find(`[data-line-id="${lineId}"]`);
                if ($input.length && !$input.val()) {
                    $input.val(data[lineId]);
                    $input.trigger('input');
                }
            });
        } catch (e) {
            console.warn('Failed to restore saved pricing data:', e);
        }
    },

    /**
     * Clear localStorage
     */
    _clearLocalStorage: function () {
        const orderId = this.$el.data('order-id');
        if (orderId) {
            localStorage.removeItem(`vendor_pricing_${orderId}`);
        }
    },

    /**
     * Cleanup when widget is destroyed
     */
    destroy: function () {
        if (this.autoSaveInterval) {
            clearInterval(this.autoSaveInterval);
        }
        this._super.apply(this, arguments);
    },
});

/**
 * Initialize tooltips and other UI enhancements
 */
$(document).ready(function () {
    // Initialize tooltips
    $('[data-bs-toggle="tooltip"]').tooltip();
    
    // Add smooth scrolling for anchor links
    $('a[href^="#"]').on('click', function (e) {
        e.preventDefault();
        const target = $(this.getAttribute('href'));
        if (target.length) {
            $('html, body').animate({
                scrollTop: target.offset().top - 100
            }, 500);
        }
    });
    
    // Add keyboard shortcuts
    $(document).on('keydown', function (e) {
        // Ctrl+S to save (prevent default browser save)
        if (e.ctrlKey && e.key === 's') {
            e.preventDefault();
            $('.o_portal_rfq_pricing_form').trigger('submit');
        }
    });
    
    // Add print functionality
    $('.print-rfq').on('click', function () {
        window.print();
    });
}); 