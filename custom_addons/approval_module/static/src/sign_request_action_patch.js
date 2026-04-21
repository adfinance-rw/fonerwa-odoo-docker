/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { rpc } from "@web/core/network/rpc";
import { SignRequest } from "@sign/backend_components/sign_request/sign_request_action";
import { SignRequestControlPanel } from "@sign/backend_components/sign_request/sign_request_control_panel";
import { SignableRequestControlPanel } from "@sign/backend_components/sign_request/signable_sign_request_control_panel";
import { useEffect } from "@odoo/owl";

// Override fetchDocument to extract reference doc info from the HTML response.
// The server-side get_document_qweb_context override injects reference doc data
// into the QWeb context, which gets rendered as a hidden div in the HTML.
patch(SignRequest.prototype, {
    async fetchDocument() {
        console.log("[RGF-SIGN] === fetchDocument START ===");

        if (!this.signInfo.get("documentId")) {
            console.log("[RGF-SIGN] No documentId, going back to kanban");
            return this.goBackToKanban();
        }

        const documentId = this.signInfo.get("documentId");
        const token = this.signInfo.get("signRequestToken");
        console.log("[RGF-SIGN] documentId:", documentId, "token:", token?.substring(0, 8));

        const url = `/sign/get_document/${documentId}/${token}`;
        console.log("[RGF-SIGN] Fetching URL:", url);

        let response;
        try {
            response = await rpc(url);
        } catch (e) {
            console.error("[RGF-SIGN] RPC failed:", e);
            throw e;
        }

        const { html, context } = response;
        console.log("[RGF-SIGN] Response received — html length:", html?.length, "context keys:", Object.keys(context || {}));

        this.html = html.trim();
        if (Object.keys(context).length > 0) {
            this.signInfo.set({
                refusalAllowed: context.refusal_allowed,
                signRequestItemToken: this.signInfo.get("signRequestToken"),
                signRequestToken: context.sign_request_token,
            });
        }

        // Parse the HTML to extract reference doc info from the hidden div
        // injected by our QWeb template extension (sign_doc_reference_doc)
        const parser = new DOMParser();
        const doc = parser.parseFromString(this.html, "text/html");

        console.log("[RGF-SIGN] Parsed HTML document. Looking for .o_sign_reference_doc_data ...");
        const refDocEl = doc.querySelector(".o_sign_reference_doc_data");
        console.log("[RGF-SIGN] refDocEl found:", !!refDocEl);

        if (refDocEl) {
            console.log("[RGF-SIGN] refDocEl dataset:", JSON.stringify(refDocEl.dataset));
            this.signInfo.set({
                referenceDocModel: refDocEl.dataset.model,
                referenceDocId: parseInt(refDocEl.dataset.id, 10),
                referenceDocName: refDocEl.dataset.name || "",
            });
            console.log("[RGF-SIGN] signInfo updated with reference doc");
        } else {
            // Debug: log all hidden inputs and divs in the parsed HTML to see what's there
            const allHiddenInputs = doc.querySelectorAll("input[type='hidden']");
            console.log("[RGF-SIGN] Hidden inputs in HTML:", allHiddenInputs.length);
            allHiddenInputs.forEach((el) => {
                console.log("[RGF-SIGN]   input#" + el.id, "=", el.value?.substring(0, 50));
            });
            const allDivs = doc.querySelectorAll("div[class*='d-none'], div[class*='reference']");
            console.log("[RGF-SIGN] Hidden/reference divs:", allDivs.length);
            allDivs.forEach((el) => {
                console.log("[RGF-SIGN]   div class='" + el.className + "'", "data:", JSON.stringify(el.dataset));
            });
            // Also log a snippet of the raw HTML to see if the div is there but with different markup
            console.log("[RGF-SIGN] HTML snippet (first 2000 chars):", this.html.substring(0, 2000));
        }

        console.log("[RGF-SIGN] signInfo referenceDocId:", this.signInfo.get("referenceDocId"));
        console.log("[RGF-SIGN] signInfo referenceDocModel:", this.signInfo.get("referenceDocModel"));

        this.signerStatus = doc.querySelector(".o_sign_cp_pager");
        console.log("[RGF-SIGN] === fetchDocument END ===");
    },
});

/**
 * Find the breadcrumb title and wrap it in a link that opens the
 * linked approval request in a new tab.
 */
function makeBreadcrumbClickable(signInfo) {
    const model = signInfo.get("referenceDocModel");
    const id = signInfo.get("referenceDocId");

    console.log("[RGF-SIGN] makeBreadcrumbClickable — model:", model, "id:", id);

    if (!model || !id) {
        console.log("[RGF-SIGN] No reference doc data, skipping breadcrumb link");
        return false;
    }

    let breadcrumbItem = document.querySelector(".o_last_breadcrumb_item span.text-truncate");
    console.log("[RGF-SIGN] .o_last_breadcrumb_item span.text-truncate:", !!breadcrumbItem);
    if (!breadcrumbItem) {
        breadcrumbItem = document.querySelector(".o_last_breadcrumb_item");
        console.log("[RGF-SIGN] .o_last_breadcrumb_item:", !!breadcrumbItem);
    }
    if (!breadcrumbItem) {
        // Debug: log all breadcrumb-related elements
        const allBreadcrumbs = document.querySelectorAll("[class*='breadcrumb']");
        console.log("[RGF-SIGN] No breadcrumb found. All breadcrumb elements:", allBreadcrumbs.length);
        allBreadcrumbs.forEach((el, i) => {
            console.log(`[RGF-SIGN]   [${i}] <${el.tagName}> class="${el.className}" text="${el.textContent.trim().substring(0, 80)}"`);
        });
        return false;
    }

    // Already converted to a link
    if (breadcrumbItem.querySelector(".o_sign_reference_doc_link")) {
        console.log("[RGF-SIGN] Link already injected, done");
        return true;
    }

    const originalText = breadcrumbItem.textContent;
    console.log("[RGF-SIGN] Breadcrumb text:", originalText);
    if (!originalText) {
        return false;
    }

    // Use web client hash URL to open the specific record in form view
    const linkUrl = `/web#id=${id}&model=${model}&view_type=form`;
    const link = document.createElement("a");
    link.href = linkUrl;
    link.target = "_blank";
    link.className = "o_sign_reference_doc_link text-primary";
    link.title = "Open linked approval request in new tab";
    link.style.cursor = "pointer";
    link.textContent = originalText;
    // Force new window — prevent Odoo's SPA router from intercepting the click
    link.addEventListener("click", (e) => {
        e.preventDefault();
        e.stopPropagation();
        window.open(linkUrl, "_blank");
    });

    breadcrumbItem.textContent = "";
    breadcrumbItem.appendChild(link);
    console.log("[RGF-SIGN] Link injected! text:", originalText, "→", linkUrl);
    return true;
}

/**
 * Shared setup hook: retry injecting the link until DOM is ready.
 */
function useReferenceDocLink(signInfo) {
    useEffect(() => {
        console.log("[RGF-SIGN] useReferenceDocLink effect fired");
        let retries = 0;
        const maxRetries = 15;

        const tryInjectLink = () => {
            console.log("[RGF-SIGN] tryInjectLink attempt", retries + 1, "of", maxRetries);
            if (makeBreadcrumbClickable(signInfo)) {
                console.log("[RGF-SIGN] Link injection succeeded on attempt", retries + 1);
                return;
            }
            if (retries < maxRetries) {
                retries++;
                setTimeout(tryInjectLink, 500);
            } else {
                console.warn("[RGF-SIGN] Gave up after", maxRetries, "attempts");
                console.log("[RGF-SIGN] Final signInfo state — referenceDocId:", signInfo.get("referenceDocId"), "referenceDocModel:", signInfo.get("referenceDocModel"));
            }
        };

        tryInjectLink();
    });
}

// Patch SignRequestControlPanel (view mode)
patch(SignRequestControlPanel.prototype, {
    setup() {
        console.log("[RGF-SIGN] SignRequestControlPanel.setup() — patched version");
        super.setup?.(...arguments);
        console.log("[RGF-SIGN] signInfo available in SignRequestControlPanel:", !!this.signInfo);
        useReferenceDocLink(this.signInfo);
    },
});

// Patch SignableRequestControlPanel (signing mode) — this is a separate class
// that does NOT extend SignRequestControlPanel, so it needs its own patch.
patch(SignableRequestControlPanel.prototype, {
    setup() {
        console.log("[RGF-SIGN] SignableRequestControlPanel.setup() — patched version");
        super.setup?.(...arguments);
        console.log("[RGF-SIGN] signInfo available in SignableRequestControlPanel:", !!this.signInfo);
        useReferenceDocLink(this.signInfo);
    },
});
