# Tender Award Report Module

## Overview

The Tender Award Report module for Odoo 18 generates formal tender award reports for Purchase Orders that are part of a tender process (purchase alternatives). This module is specifically designed to meet government procurement requirements and follows the Rwanda Green Fund tender award format.

## Features

- **Tender Award Report Generation**: Generate professional PDF reports before PO validation
- **Vendor Comparison**: Automatically list all participating vendors with their quoted prices
- **Qualification Tracking**: Track vendor qualifications (CV, degrees, etc.)
- **Formal Recommendation**: Include formal recommendation and justification
- **Approval Chain**: Support for multi-level approval workflow
- **Government Format**: Follows official government tender award format

## Requirements

- Odoo 18.0
- Purchase module
- Purchase Requisition module (for purchase alternatives)

## Installation

1. Copy the module to your Odoo addons directory
2. Update the module list
3. Install the "Tender Award Report" module

## Usage

### Setting up a Tender Process

1. Create multiple RFQs (Purchase Orders) for the same products/services
2. Use the "Create Alternative" feature to link them as tender alternatives
3. Send RFQs to different vendors
4. Collect vendor responses and pricing

### Generating Tender Award Report

1. Open the Purchase Order you want to award
2. Go to the "Tender Award" tab
3. Fill in the required information:
   - Tender Description
   - Legal Reference
   - Recommendation text
   - Approval chain (Prepared by, First Approval, Final Approval)
4. Click "Generate Tender Award Report"
5. Review and download the PDF report
6. Proceed with PO validation

### Report Structure

The generated report includes:

- **Header**: Company information and tender title
- **Introduction**: Legal reference and context
- **Bidder Table**: All participating vendors with:
  - Serial number
  - Vendor name
  - Qualifications and supporting documents
  - Quoted price
- **Recommendation**: Formal recommendation with amount in words
- **Approval Chain**: Signature fields for approval workflow

## Configuration

### Vendor Qualifications

To track vendor qualifications, you can extend the `res.partner` model with custom fields:

```python
x_cv_submitted = fields.Boolean('CV Submitted')
x_degree_submitted = fields.Boolean('Degree Submitted')
```

### Legal References

The default legal reference can be customized in the Purchase Order form or set as a default value in the model.

## Technical Details

### Models Extended

- `purchase.order`: Added tender award functionality

### New Fields

- `tender_award_recommendation`: Text field for formal recommendation
- `tender_award_generated`: Boolean to track report generation
- `tender_award_date`: Timestamp of report generation
- `tender_description`: Description of the tender project
- `legal_reference`: Legal reference for the tender process
- `prepared_by`, `first_approval`, `final_approval`: Approval chain users

### Computed Fields

- `tender_participants`: All POs in the same tender group
- `tender_participants_data`: Structured data for report generation
- `tender_participants_count`: Number of participants

### Workflow Integration

The module integrates with the purchase order validation workflow by:
- Requiring tender award report generation before validation for tender POs
- Adding validation checks in the `button_confirm()` method
- Providing clear error messages when validation is attempted without report generation

## Security

- Standard user access to view and edit tender award information
- Purchase manager access to all tender award functions
- Report generation restricted to authorized users

## Customization

### Styling

The report styling can be customized by modifying:
- `static/src/css/tender_award.css`

### Template

The report template can be customized by modifying:
- `reports/tender_award_report.xml`

### Legal References

Update the default legal reference in the model or through the UI.

## Troubleshooting

### Common Issues

1. **"No tender participants found"**: Ensure POs are properly linked via purchase alternatives
2. **"Tender Award Report must be generated"**: Generate the report before validating the PO
3. **Missing qualifications**: Add custom fields to track vendor qualifications

### Debug Mode

Enable debug mode to see detailed error messages and trace issues.

## Support

For support and customization requests, contact the RGF development team.

## License

LGPL-3
