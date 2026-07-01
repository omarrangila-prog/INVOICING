from odoo import http
from odoo.http import request


class InvoicingController(http.Controller):

    @http.route('/invoicing/dashboard/data', auth='user', type='json')
    def get_dashboard_data(self, **kwargs):
        """API endpoint to fetch dashboard KPI data"""
        Invoice = request.env['digital.invoice']
        InvoiceBook = request.env['digital.invoice.book']
        Customer = request.env['customer.account']
        Item = request.env['item.master']
        
        # Get this month's data
        from datetime import datetime, date
        from dateutil.relativedelta import relativedelta
        
        today = date.today()
        month_start = today.replace(day=1)
        month_end = (month_start + relativedelta(months=1)) - relativedelta(days=1)
        
        # Count invoices this month
        total_invoices = Invoice.search_count([
            ('invoice_date', '>=', month_start),
            ('invoice_date', '<=', month_end),
            ('state', '!=', 'cancelled')
        ])
        
        # Calculate revenue this month
        invoices_month = Invoice.search([
            ('invoice_date', '>=', month_start),
            ('invoice_date', '<=', month_end),
            ('state', '!=', 'cancelled')
        ])
        total_revenue = sum(inv.grand_total for inv in invoices_month)
        total_tax = sum(inv.tax_amount for inv in invoices_month)
        
        # Count active customers
        total_customers = Customer.search_count([('active', '=', True)])
        
        # Count FBR posted this month
        fbr_posted = Invoice.search_count([
            ('invoice_date', '>=', month_start),
            ('invoice_date', '<=', month_end),
            ('state', '=', 'posted'),
            ('fbr_id', '!=', False)
        ])
        
        # Count draft invoices
        draft_invoices = Invoice.search_count([('state', '=', 'draft')])
        
        # Calculate average invoice value
        avg_invoice = total_revenue / total_invoices if total_invoices > 0 else 0
        
        # Count total items
        total_items = Item.search_count([('active', '=', True)])
        
        return {
            'total_invoices': total_invoices,
            'total_revenue': total_revenue,
            'total_tax': total_tax,
            'total_customers': total_customers,
            'fbr_posted': fbr_posted,
            'draft_invoices': draft_invoices,
            'avg_invoice': avg_invoice,
            'total_items': total_items,
        }

    @http.route('/invoicing/recent-invoices', auth='user', type='json')
    def get_recent_invoices(self, limit=5):
        """API endpoint to fetch recent invoices"""
        Invoice = request.env['digital.invoice']
        
        invoices = Invoice.search_read(
            domain=[('state', '!=', 'cancelled')],
            fields=['bill_no', 'invoice_date', 'buyer_id', 'grand_total', 'state'],
            limit=limit,
            order='invoice_date desc'
        )
        
        return {'invoices': invoices}
