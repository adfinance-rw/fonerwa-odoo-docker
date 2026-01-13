/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ApprovalCategoryKanbanController } from "@approvals/views/kanban/approvals_category_kanban_controller";
import { useService } from "@web/core/utils/hooks";

patch(ApprovalCategoryKanbanController.prototype, {
    setup() {
        super.setup();
        this.orm = useService("orm");
    },

    async OpenNewApprovalRequest() {
        // Get the current company's default approval category
        const company_id = this.env.services.company.currentCompany.id;
        
        try {
            const companies = await this.orm.read(
                "res.company",
                [company_id],
                ["default_approval_category_id"]
            );
            
            const default_category_id = companies[0]?.default_approval_category_id?.[0];
            
            if (default_category_id) {
                // Open new request form with default category pre-selected
                this.action.doAction({
                    type: "ir.actions.act_window",
                    res_model: "approval.request",
                    views: [[false, "form"]],
                    target: "current",
                    context: {
                        default_category_id: default_category_id,
                    },
                });
            } else {
                // No default category configured, use standard behavior
                super.OpenNewApprovalRequest();
            }
        } catch (error) {
            console.error("Error fetching default approval category:", error);
            // Fallback to standard behavior on error
            super.OpenNewApprovalRequest();
        }
    },
});

