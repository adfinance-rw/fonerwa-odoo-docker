from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime
from odoo.tools import float_round
import io
import xlsxwriter
import base64
from datetime import timedelta

class StockReportWizard(models.TransientModel):
    _name = 'stock.report.wizard'
    _description = 'Stock Report Wizard'

    date_from = fields.Date(string='From Date', required=True)
    date_to = fields.Date(string='To Date', required=True)
    location_id = fields.Many2one('stock.location', string='Location')
    product_ids = fields.Many2many('product.product', string='Products')
    category_id = fields.Many2one('product.category', string='Product Category')
    group_by_location = fields.Boolean(string='Group by Location', default=False)
    include_all_types = fields.Boolean(string='Include All Product Types', default=False, 
                                       help="Include consumable and service products in addition to stockable products")
    show_zero_stock = fields.Boolean(string='Show Zero Stock Products', default=True,
                                     help="Show products with zero current stock if they had movements during the period")
    
    excel_file = fields.Binary('Excel Report', readonly=True)
    file_name = fields.Char('File Name', readonly=True)

    detailed_excel_file = fields.Binary('Detailed Excel Report', readonly=True)
    detailed_file_name = fields.Char('Detailed File Name', readonly=True)

    def _get_products_domain(self):
        domain = []
        # Filter by product type unless include_all_types is checked
        if not self.include_all_types:
            domain.append(('type', '=', 'product'))  # Only stockable products
        
        if self.product_ids:
            domain.append(('id', 'in', self.product_ids.ids))
        if self.category_id:
            domain.append(('categ_id', '=', self.category_id.id))
        return domain

    def _get_stock_data(self, product):
        """Get actual stock data for a product"""
        domain = [('product_id', '=', product.id)]
        if self.location_id:
            domain.append(('location_id', '=', self.location_id.id))
        else:
            domain.append(('location_id.usage', '=', 'internal'))

        quants = self.env['stock.quant'].search(domain)
        
        return {
            'quantity': float_round(sum(quants.mapped('quantity')), precision_digits=3),
            'value': float_round(sum(quant.quantity * product.standard_price for quant in quants), precision_digits=2)
        }

    def _get_product_moves(self, product):
        """Get incoming and outgoing moves for the period"""
        domain = [
            ('product_id', '=', product.id),
            ('state', '=', 'done'),
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
        ]
        
        if self.location_id:
            domain.extend(['|',
                ('location_dest_id', '=', self.location_id.id),
                ('location_id', '=', self.location_id.id)
            ])
        else:
            domain.extend([
                '|',
                ('location_dest_id.usage', '=', 'internal'),
                ('location_id.usage', '=', 'internal')
            ])

        moves = self.env['stock.move'].search(domain)
        
        incoming = sum(moves.filtered(
            lambda m: (self.location_id and m.location_dest_id == self.location_id) or
                     (not self.location_id and m.location_dest_id.usage == 'internal' and 
                      m.location_id.usage != 'internal')
        ).mapped('product_qty'))
        
        outgoing = sum(moves.filtered(
            lambda m: (self.location_id and m.location_id == self.location_id) or
                     (not self.location_id and m.location_id.usage == 'internal' and 
                      m.location_dest_id.usage != 'internal')
        ).mapped('product_qty'))

        return {
            'incoming': float_round(incoming, precision_digits=3),
            'outgoing': float_round(outgoing, precision_digits=3)
        }

    def _get_stock_at_date(self, product, date):
        """Get stock balance at a specific date"""
        # Get current stock
        stock_data = self._get_stock_data(product)
        current_qty = stock_data['quantity']
        
        # Get moves between target date and now to reverse calculate
        domain = [
            ('product_id', '=', product.id),
            ('state', '=', 'done'),
            ('date', '>', date),  # All moves after our target date
        ]
        
        if self.location_id:
            domain.extend(['|',
                ('location_dest_id', '=', self.location_id.id),
                ('location_id', '=', self.location_id.id)
            ])
        else:
            domain.extend([
                '|',
                ('location_dest_id.usage', '=', 'internal'),
                ('location_id.usage', '=', 'internal')
            ])

        moves = self.env['stock.move'].search(domain)
        
        # Reverse calculate the balance at date
        balance = current_qty
        for move in moves:
            if (self.location_id and move.location_dest_id == self.location_id) or \
               (not self.location_id and move.location_dest_id.usage == 'internal' and 
                move.location_id.usage != 'internal'):
                balance -= move.product_qty  # Subtract incoming moves that happened after our date
            elif (self.location_id and move.location_id == self.location_id) or \
                 (not self.location_id and move.location_id.usage == 'internal' and 
                  move.location_dest_id.usage != 'internal'):
                balance += move.product_qty  # Add back outgoing moves that happened after our date
            
        return float_round(balance, precision_digits=3)

    def _get_initial_stock(self, product):
        """Get stock balance at the start date"""
        # Get stock balance from the day before start date
        date_before = self.date_from - timedelta(days=1)
        return self._get_stock_at_date(product, date_before)

    def generate_report(self):
        products = self.env['product.product'].search(self._get_products_domain())
        if not products:
            raise UserError(_('No products found matching the selected criteria.'))

        report_data = []
        
        for product in products:
            # Get actual current stock data
            stock_data = self._get_stock_data(product)
            
            # Get movement data
            moves = self._get_product_moves(product)
            
            # Get initial balance at start date
            initial_balance = self._get_initial_stock(product)
            
            # Determine if we should include this product
            has_stock = stock_data['quantity'] != 0
            has_movements = moves['incoming'] != 0 or moves['outgoing'] != 0 or initial_balance != 0
            is_selected = bool(self.product_ids)
            
            # Skip products with no stock and no movements, unless:
            # - show_zero_stock is enabled and product had movements during the period
            # - specific products were selected
            if not has_stock and not is_selected:
                if not self.show_zero_stock or not has_movements:
                    continue
            
            report_data.append({
                'product': product.display_name,
                'category': product.categ_id.name,
                'uom': product.uom_id.name,
                'initial_balance': initial_balance,
                'incoming_qty': moves['incoming'],
                'outgoing_qty': moves['outgoing'],
                'balance_qty': stock_data['quantity'],
                'unit_cost': product.standard_price,
                'total_value': stock_data['value']
            })

        if not report_data:
            raise UserError(_('No products with stock or movements found for the selected criteria and date range.'))

        return self._generate_excel_report(report_data)

    def _generate_excel_report(self, report_data):
        """Generate Excel report with actual stock data"""
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output)
        sheet = workbook.add_worksheet('Stock Report')

        # Styles
        header_format = workbook.add_format({
            'bold': True,
            'align': 'center',
            'bg_color': '#D3D3D3',
            'border': 1
        })
        
        number_format = workbook.add_format({
            'num_format': '#,##0.00',
            'border': 1
        })

        # Headers
        headers = [
            'Product', 'Category', 'UoM', 'Initial Balance',
            'Incoming Qty', 'Outgoing Qty', 'Balance Qty',
            'Unit Cost', 'Total Value'
        ]

        for col, header in enumerate(headers):
            sheet.write(0, col, header, header_format)

        # Data
        for row, data in enumerate(report_data, start=1):
            sheet.write(row, 0, data['product'])
            sheet.write(row, 1, data['category'])
            sheet.write(row, 2, data['uom'])
            sheet.write(row, 3, data['initial_balance'], number_format)
            sheet.write(row, 4, data['incoming_qty'], number_format)
            sheet.write(row, 5, data['outgoing_qty'], number_format)
            sheet.write(row, 6, data['balance_qty'], number_format)
            sheet.write(row, 7, data['unit_cost'], number_format)
            sheet.write(row, 8, data['total_value'], number_format)

        workbook.close()
        output.seek(0)
        
        excel_data = base64.b64encode(output.getvalue())
        filename = f'Stock_Report_{fields.Date.today().strftime("%Y%m%d")}.xlsx'
        
        self.write({
            'excel_file': excel_data,
            'file_name': filename
        })
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'stock.report.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def download_report(self):
        """Action to download the generated Excel report"""
        if not self.excel_file:
            raise UserError(_('Please generate the report first.'))
        
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/?model=stock.report.wizard&id={}&field=excel_file&filename_field=file_name&download=true'.format(self.id),
            'target': 'self',
        }

    def generate_detailed_report(self):
        """Generate detailed movement history report"""
        products = self.env['product.product'].search(self._get_products_domain())
        if not products:
            raise UserError(_('No products found matching the selected criteria.'))

        # Prepare workbook
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output)
        
        # Styles
        header_format = workbook.add_format({
            'bold': True, 
            'align': 'center',
            'bg_color': '#D3D3D3',
            'border': 1
        })
        product_header_format = workbook.add_format({
            'bold': True,
            'font_size': 12,
            'bg_color': '#4F81BD',
            'font_color': 'white',
            'border': 1
        })
        date_format = workbook.add_format({
            'num_format': 'dd/mm/yyyy',
            'border': 1
        })
        number_format = workbook.add_format({
            'num_format': '#,##0.00',
            'border': 1
        })

        # Create single worksheet
        sheet = workbook.add_worksheet('Detailed Stock Report')
        
        # Headers
        headers = [
            'Date', 'Reference', 'Source Location', 'Destination Location',
            'Initial Balance', 'In Qty', 'Out Qty', 'Balance',
            'Unit Cost', 'Value'
        ]

        current_row = 0

        for product in products:
            # Add product header
            sheet.merge_range(current_row, 0, current_row, len(headers)-1, 
                             f'Product: {product.display_name} [{product.default_code or ""}]', 
                             product_header_format)
            current_row += 1

            # Add column headers for this product section
            for col, header in enumerate(headers):
                sheet.write(current_row, col, header, header_format)
            current_row += 1

            # Get initial balance at start date
            initial_balance = self._get_initial_stock(product)
            sheet.write(current_row, 0, self.date_from, date_format)
            sheet.write(current_row, 4, initial_balance, number_format)
            sheet.write(current_row, 7, initial_balance, number_format)
            sheet.write(current_row, 8, product.standard_price, number_format)
            sheet.write(current_row, 9, initial_balance * product.standard_price, number_format)
            current_row += 1
            
            # Get moves within date range
            domain = [
                ('product_id', '=', product.id),
                ('state', '=', 'done'),
                ('date', '>=', self.date_from),
                ('date', '<=', self.date_to),
            ]
            
            if self.location_id:
                domain.extend(['|',
                    ('location_dest_id', '=', self.location_id.id),
                    ('location_id', '=', self.location_id.id)
                ])
            else:
                domain.extend([
                    '|',
                    ('location_dest_id.usage', '=', 'internal'),
                    ('location_id.usage', '=', 'internal')
                ])

            moves = self.env['stock.move'].search(domain, order='date')
            
            # Filter out internal adjustments that don't affect stock
            filtered_moves = moves.filtered(lambda m: 
                not any(ref in (m.reference or m.name or '') 
                       for ref in ['Product Quantity Updated', 'End of month inventory'])
                or (m.location_id.usage != 'internal' or m.location_dest_id.usage != 'internal')
            )

            running_balance = initial_balance
            for move in filtered_moves:
                in_qty = out_qty = 0.0
                
                if (self.location_id and move.location_dest_id == self.location_id) or \
                   (not self.location_id and move.location_dest_id.usage == 'internal' and 
                    move.location_id.usage != 'internal'):
                    in_qty = move.product_qty
                    running_balance += move.product_qty
                elif (self.location_id and move.location_id == self.location_id) or \
                     (not self.location_id and move.location_id.usage == 'internal' and 
                      move.location_dest_id.usage != 'internal'):
                    out_qty = move.product_qty
                    running_balance -= move.product_qty

                sheet.write(current_row, 0, move.date, date_format)
                sheet.write(current_row, 1, move.reference or move.name)
                sheet.write(current_row, 2, move.location_id.display_name)
                sheet.write(current_row, 3, move.location_dest_id.display_name)
                sheet.write(current_row, 5, in_qty, number_format)
                sheet.write(current_row, 6, out_qty, number_format)
                sheet.write(current_row, 7, running_balance, number_format)
                sheet.write(current_row, 8, product.standard_price, number_format)
                sheet.write(current_row, 9, running_balance * product.standard_price, number_format)
                current_row += 1

            # Add final balance verification
            final_balance = self._get_stock_at_date(product, self.date_to)
            if abs(final_balance - running_balance) > 0.001:  # Small threshold for float comparison
                # Add a reconciliation line if there's a difference
                sheet.write(current_row, 0, self.date_to, date_format)
                sheet.write(current_row, 1, 'Balance Adjustment')
                adjustment = final_balance - running_balance
                if adjustment > 0:
                    sheet.write(current_row, 5, adjustment, number_format)
                else:
                    sheet.write(current_row, 6, -adjustment, number_format)
                sheet.write(current_row, 7, final_balance, number_format)
                sheet.write(current_row, 8, product.standard_price, number_format)
                sheet.write(current_row, 9, final_balance * product.standard_price, number_format)
                current_row += 1

            # Add a blank row between products
            current_row += 1

        # Adjust column widths
        sheet.set_column('A:A', 18)  # Date
        sheet.set_column('B:B', 20)  # Reference
        sheet.set_column('C:D', 30)  # Locations
        sheet.set_column('E:I', 15)  # Quantities and costs
        sheet.set_column('J:J', 18)  # Value

        workbook.close()
        output.seek(0)
        
        excel_data = base64.b64encode(output.getvalue())
        filename = f'Detailed_Stock_Report_{fields.Date.today().strftime("%Y%m%d")}.xlsx'
        
        self.write({
            'detailed_excel_file': excel_data,
            'detailed_file_name': filename
        })
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'stock.report.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def download_detailed_report(self):
        """Action to download the generated detailed Excel report"""
        if not self.detailed_excel_file:
            raise UserError(_('Please generate the detailed report first.'))
        
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/?model=stock.report.wizard&id={}&field=detailed_excel_file&filename_field=detailed_file_name&download=true'.format(self.id),
            'target': 'self',
        }
