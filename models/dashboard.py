from odoo import models, fields, api


class DigitalInvoiceDashboard(models.TransientModel):
    _name = 'digital.invoice.dashboard'
    _description = 'Digital Invoice Dashboard'

    def name_get(self):
        return [(rec.id, 'Digital Invoicing Dashboard') for rec in self]

    @api.model
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = 'Digital Invoicing Dashboard'

    # Filters
    date_from = fields.Date(string='From')
    date_to = fields.Date(string='To')
    customer_id = fields.Many2one('customer.account', string='Customer')
    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.company.currency_id)

    # KPI fields
    total_invoices = fields.Integer(string='Total Invoices', default=0)
    pending_invoices = fields.Integer(string='Pending', default=0)
    submitted_invoices = fields.Integer(string='Posted to FBR', default=0)
    total_customers = fields.Integer(string='Total Customers', default=0)

    total_amount = fields.Float(string='Total Amount', digits=(16, 2), default=0.0)
    pending_amount = fields.Float(string='Pending Amount', digits=(16, 2), default=0.0)
    submitted_amount = fields.Float(string='Submitted Amount', digits=(16, 2), default=0.0)
    received_amount = fields.Float(string='Received Amount', digits=(16, 2), default=0.0)

    total_gst = fields.Float(string='Total GST', digits=(16, 2), default=0.0)
    total_fst = fields.Float(string='Total FST', digits=(16, 2), default=0.0)
    total_tax = fields.Float(string='Total Tax', digits=(16, 2), default=0.0)
    fbr_compliance_rate = fields.Float(string='FBR Compliance Rate', default=0.0)

    def _load_kpis(self):
        domain = [('state', '!=', 'cancelled')]
        if self.date_from:
            domain.append(('invoice_date', '>=', self.date_from))
        if self.date_to:
            domain.append(('invoice_date', '<=', self.date_to))
        if self.customer_id:
            domain.append(('buyer_id', '=', self.customer_id.id))

        invoices = self.env['digital.invoice'].search(domain)
        posted = invoices.filtered(lambda i: i.state == 'posted')
        pending = invoices.filtered(lambda i: i.state in ('draft', 'validated'))

        self.total_invoices = len(invoices)
        self.total_amount = sum(invoices.mapped('grand_total'))
        self.submitted_invoices = len(posted)
        self.submitted_amount = sum(posted.mapped('grand_total'))
        self.pending_invoices = len(pending)
        self.pending_amount = sum(pending.mapped('grand_total'))
        self.received_amount = self.submitted_amount
        self.total_gst = sum(invoices.mapped('gst_amount'))
        self.total_fst = sum(invoices.mapped('fst_amount'))
        self.total_tax = sum(invoices.mapped('tax_amount'))
        self.total_customers = self.env['customer.account'].search_count(
            [('active', '=', True)])
        self.fbr_compliance_rate = round(
            (len(posted) / len(invoices) * 100) if invoices else 0.0, 1)

    @api.onchange('date_from', 'date_to', 'customer_id')
    def _onchange_filters(self):
        self._load_kpis()

    def action_view_pending(self):
        domain = [('state', 'in', ('draft', 'validated'))]
        if self.date_from:
            domain += [('invoice_date', '>=', self.date_from)]
        if self.date_to:
            domain += [('invoice_date', '<=', self.date_to)]
        if self.customer_id:
            domain += [('buyer_id', '=', self.customer_id.id)]
        return {
            'type': 'ir.actions.act_window',
            'name': 'Pending Invoices',
            'res_model': 'digital.invoice',
            'view_mode': 'list,form',
            'domain': domain,
        }

    def action_view_submitted(self):
        domain = [('state', '=', 'posted')]
        if self.date_from:
            domain += [('invoice_date', '>=', self.date_from)]
        if self.date_to:
            domain += [('invoice_date', '<=', self.date_to)]
        if self.customer_id:
            domain += [('buyer_id', '=', self.customer_id.id)]
        return {
            'type': 'ir.actions.act_window',
            'name': 'Posted Invoices',
            'res_model': 'digital.invoice',
            'view_mode': 'list,form',
            'domain': domain,
        }

    def action_view_all(self):
        domain = [('state', '!=', 'cancelled')]
        if self.date_from:
            domain += [('invoice_date', '>=', self.date_from)]
        if self.date_to:
            domain += [('invoice_date', '<=', self.date_to)]
        if self.customer_id:
            domain += [('buyer_id', '=', self.customer_id.id)]
        return {
            'type': 'ir.actions.act_window',
            'name': 'All Invoices',
            'res_model': 'digital.invoice',
            'view_mode': 'list,form',
            'domain': domain,
        }

    def action_view_invoice_book(self):
        domain = []
        if self.customer_id:
            domain += [('customer_id', '=', self.customer_id.id)]
        return {
            'type': 'ir.actions.act_window',
            'name': 'Customers',
            'res_model': 'customer.account',
            'view_mode': 'list,form',
            'domain': domain,
        }