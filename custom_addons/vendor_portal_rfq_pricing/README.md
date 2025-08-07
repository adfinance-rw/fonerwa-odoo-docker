# Vendor Portal RFQ Pricing

A comprehensive Odoo 18 module that allows vendors to input prices for RFQ (Request for Quotation) lines through the vendor portal.

## 🚀 Features

### For Vendors (Portal Users)
- **Easy Price Input**: Submit pricing directly through the vendor portal with an intuitive interface
- **Real-time Validation**: Instant feedback on price inputs with validation
- **Progress Tracking**: Visual progress indicator showing completion status
- **Auto-save**: Automatic saving of work in progress using localStorage
- **Mobile Responsive**: Fully responsive design that works on all devices
- **Email Notifications**: Automatic notifications to purchasing team when prices are submitted

### For Internal Users (Purchase Team)
- **Vendor Pricing Dashboard**: Dedicated dashboard to track RFQs pending vendor pricing
- **Price Comparison**: Compare vendor prices with current prices including difference calculations
- **Bulk Price Transfer**: Transfer vendor prices to official prices with a powerful wizard
- **Individual Line Management**: Accept or reject individual line prices
- **Advanced Filtering**: Filter purchase orders by vendor pricing status
- **Detailed Audit Trail**: Complete tracking of price submissions and transfers

### Technical Features
- **Modern Odoo 18 Syntax**: Built using the latest Odoo 18 development patterns
- **Secure Access Control**: Comprehensive security rules ensure vendors only access their own RFQs
- **Custom Fields**: Separate `x_supplier_price` field maintains data integrity
- **Email Templates**: Professional email templates for notifications
- **JavaScript Enhancement**: Interactive frontend with real-time updates

## 📋 Requirements

- Odoo 18.0+
- Python 3.8+
- Purchase module (automatically installed)
- Portal module (automatically installed)
- Mail module (automatically installed)
- Website module (automatically installed)

## 🔧 Installation

1. **Download the Module**
   ```bash
   cd /path/to/odoo/addons
   git clone <repository-url> vendor_portal_rfq_pricing
   ```

2. **Update Apps List**
   - Go to Apps menu in Odoo
   - Click "Update Apps List"
   - Wait for the update to complete

3. **Install the Module**
   - Search for "Vendor Portal RFQ Pricing"
   - Click "Install"

4. **Configure Email Settings** (Optional but recommended)
   - Go to Settings > Technical > Email > Outgoing Mail Servers
   - Configure your SMTP settings for email notifications

## ⚙️ Configuration

### 1. Set up Vendor Portal Access

1. **Create Portal Users for Vendors**:
   - Go to Contacts
   - Select your vendor
   - Click "Grant Portal Access"
   - The vendor will receive an email with login credentials

2. **Configure RFQ Email Template** (Optional):
   - Go to Settings > Technical > Email > Templates
   - Find "RFQ - Request for Quotation with Pricing Portal"
   - Customize the template as needed

### 2. Configure Permissions

The module automatically sets up the necessary permissions, but you can customize them:

- **Purchase Users**: Can view and transfer vendor prices
- **Purchase Managers**: Full access to all features
- **Portal Users**: Can only access their own RFQs and submit prices

## 📖 User Guide

### For Vendors

1. **Accessing RFQs**:
   - Log in to the vendor portal
   - Navigate to "RFQ Pricing" from the main menu
   - Or click the link in the RFQ email notification

2. **Submitting Prices**:
   - Open an RFQ that requires pricing
   - Click "Submit Your Pricing"
   - Enter your unit prices for each product line
   - Click "Submit Pricing" when complete

3. **Features Available**:
   - Real-time total calculation
   - Progress tracking
   - Auto-save (work is saved automatically)
   - Input validation
   - Mobile-friendly interface

### For Purchase Team

1. **Monitoring Vendor Pricing**:
   - Use the "Vendor Pricing Dashboard" menu item
   - Filter RFQs by pricing status
   - View which vendors have submitted prices

2. **Reviewing Vendor Prices**:
   - Open any RFQ with vendor prices
   - Review the `Supplier Price` column
   - Check price differences and percentages
   - Use color coding to identify savings/increases

3. **Transferring Prices**:
   - Click "Transfer Vendor Prices" button
   - Review prices in the wizard
   - Select which prices to transfer
   - Add notes and confirm transfer

4. **Individual Line Management**:
   - Accept individual line prices using "Accept" button
   - Reject prices using "Reject" button
   - Add notes for specific lines

## 🔐 Security Features

- **Row-Level Security**: Vendors can only access their own RFQs
- **Field-Level Restrictions**: Vendors can only modify the `x_supplier_price` field
- **State-Based Access**: Price input only allowed for draft/sent RFQs
- **Audit Trail**: All price changes are logged
- **Portal Integration**: Secure access through Odoo's portal framework

## 🎨 Customization

### Adding Custom Fields

To add more fields that vendors can edit:

1. Extend the `purchase.order.line` model:
```python
class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'
    
    x_vendor_notes = fields.Text(string='Vendor Notes')
```

2. Add fields to the portal template:
```xml
<field name="x_vendor_notes" placeholder="Add your notes..."/>
```

3. Update security rules to allow portal users to edit the new field.

### Custom Email Templates

You can create custom email templates by:

1. Going to Settings > Technical > Email > Templates
2. Creating a new template with model `purchase.order`
3. Using the provided templates as examples

### Custom Portal Pages

The module provides a base structure that can be extended for additional vendor portal pages.

## 🐛 Troubleshooting

### Common Issues

1. **Vendors Can't Access RFQs**
   - Ensure the vendor has portal access
   - Check that the RFQ is in 'draft' or 'sent' state
   - Verify the vendor is set as the partner on the RFQ

2. **Email Notifications Not Sent**
   - Check outgoing mail server configuration
   - Verify email template is active
   - Check the purchase order has a responsible user with email

3. **JavaScript Not Working**
   - Clear browser cache
   - Check browser console for errors
   - Ensure assets are properly loaded

4. **Permission Errors**
   - Update the module to refresh security rules
   - Check user groups and permissions
   - Verify record rules are properly applied

### Debug Mode

Enable debug mode to access additional debugging information:
- Add `?debug=1` to the URL
- Check logs in Settings > Technical > Logging

## 🔄 Upgrade Notes

### From Future Versions

When upgrading this module:

1. **Backup your database** before upgrading
2. Update the module files
3. Go to Apps > Upgrade
4. Test the functionality thoroughly

### Data Migration

The module preserves existing data:
- Existing RFQs are not affected
- New fields are added without data loss
- Portal access remains intact

## 🤝 Contributing

To contribute to this module:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

### Development Setup

```bash
# Clone the repository
git clone <repository-url>

# Install dependencies
pip install -r requirements.txt

# Run tests
python -m pytest tests/
```

## 📞 Support

For support and questions:

- **Email**: support@yourcompany.com
- **Documentation**: [Module Documentation](https://docs.yourcompany.com)
- **Issues**: Create an issue in the repository

## 📄 License

This module is licensed under LGPL-3. See the LICENSE file for details.

## 🙏 Acknowledgments

- Odoo SA for the excellent framework
- The Odoo community for inspiration and best practices
- Beta testers who helped improve the module

---

**Version**: 18.0.1.0.0  
**Author**: Your Company  
**Maintainer**: Your Company  
**Category**: Purchase  
**Auto-install**: False 