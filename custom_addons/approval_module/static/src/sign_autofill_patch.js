/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { SignablePDFIframe } from "@sign/components/sign_request/signable_PDF_iframe";

/**
 * Auto-fill all sign items for the current role that have auto-values
 * (saved signature, name, date, etc.) so the signer doesn't have to
 * navigate through each field one by one.
 *
 * Fields are auto-filled immediately after the PDF renders. If all fields
 * are filled, the "Validate & Send" banner shows right away.
 */
patch(SignablePDFIframe.prototype, {
    async autoFillAllFields() {
        this.refreshSignItems();
        const promises = [];

        for (const page in this.signItems) {
            for (const signItem of Object.values(this.signItems[page])) {
                if (signItem.data.responsible !== this.currentRole) {
                    continue;
                }
                // Skip items that already have a value from server
                if (signItem.data.value) {
                    continue;
                }

                const el = signItem.el;
                const type = this.signItemTypesById[signItem.data.type_id];
                if (!type) {
                    continue;
                }

                const { item_type: itemType, auto_value: autoValue, frame_value: frameValue, name } = type;

                // Skip already filled elements
                if (el.dataset.signature) {
                    continue;
                }
                if (el.value && el.value.trim() && itemType !== "signature" && itemType !== "initial") {
                    continue;
                }

                // Date fields
                if (name === _t("Date")) {
                    this.fillTextSignItem(el, this.signInfo.get("todayFormattedDate"));
                    continue;
                }

                // Text/textarea with auto-value (Name, Email, Company, etc.)
                if (autoValue && ["text", "textarea"].includes(itemType)) {
                    this.fillTextSignItem(el, autoValue);
                    continue;
                }

                // Signature/initial with saved auto-value
                if ((itemType === "signature" || itemType === "initial") && autoValue) {
                    promises.push(
                        Promise.all([
                            this.adjustSignatureSize(autoValue, el),
                            this.adjustSignatureSize(frameValue, el),
                        ]).then(([data, frameData]) => {
                            this.fillItemWithSignature(el, data, {
                                frame: frameData,
                                hash: "0",
                            });
                        })
                    );
                    continue;
                }

                // Initial with nextInitial fallback
                if (itemType === "initial" && this.nextInitial) {
                    promises.push(
                        this.adjustSignatureSize(this.nextInitial, el).then((data) => {
                            this.fillItemWithSignature(el, data);
                        })
                    );
                }
            }
        }

        if (promises.length > 0) {
            await Promise.all(promises);
        }

        this.checkSignItemsCompletion();
    },

    postRender() {
        super.postRender();

        if (this.readonly) {
            return;
        }

        // Auto-fill all fields with auto-values immediately after render.
        // Use setTimeout to ensure the PDF sign items are fully rendered.
        setTimeout(() => {
            this.autoFillAllFields();
        }, 500);
    },
});
