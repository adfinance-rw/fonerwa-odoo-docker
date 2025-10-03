# Requisition Form Report Module

## Overview
This module provides a comprehensive requisition form report for Internal Transfer operations in Odoo Inventory.

## Features
- Generate professional requisition forms from Internal Transfer records
- Government-standard layout matching Rwanda requirements
- Detailed item listing with quantities requested and received
- Signature fields for approval and receipt tracking
- Print directly from Internal Transfer views

## Installation
1. Place the module in your custom_addons directory
2. Update the module list in Odoo
3. Install the "Requisition Form Report" module

## Usage
1. Navigate to Inventory > Operations > Internal Transfers
2. Open any Internal Transfer record
3. Click the "Requisition Form" button in the header
4. The report will be generated in PDF format

## Report Structure
The report includes:
- **Header**: "REQUISITIONING FORM" title
- **Table**: Item details with columns for:
  - NO (sequential number)
  - ITEM (DESCRIPTION)
  - QUANTITY REQUESTED
  - QUANTITY RECEIVED
  - OBSERVATION
- **Signature Section**: Fields for:
  - REQUESTED BY
  - FOR APPROVAL
  - RECEIVED BY
  - ISSUED OUT BY
- **Footer**: Government reference information

## Dependencies
- base
- stock
- purchase
- hr

## Author
RGF Team

## License
LGPL-3
