from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class DigitalInvoiceBook(models.Model):
    _name = 'digital.invoice.book'
    _description = 'Digital Invoice Book'
    _order = 'invoice_date desc, id desc'
    _rec_name = 'invoice_number'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    invoice_id = fields.Many2one(
        'digital.invoice',
        string='Digital Invoice',
        readonly=True,
        ondelete='cascade',
        tracking=True
    )

    invoice_number = fields.Char(
        string='Invoice Number',
        required=True,
        readonly=True,
        copy=False,
        tracking=True
    )

    customer_id = fields.Many2one(
        'customer.account',
        string='Customer',
        readonly=True,
        tracking=True
    )

    invoice_date = fields.Date(
        string='Invoice Date',
        required=True,
        readonly=True,
        tracking=True
    )

    item_name = fields.Char(
        string='Item',
        readonly=True,
        tracking=True
    )

    quantity = fields.Float(
        string='Quantity',
        readonly=True,
        tracking=True
    )

    amount = fields.Float(
        string='Amount',
        readonly=True,
        digits='Product Price',
        tracking=True
    )

    tax_amount = fields.Float(
        string='Tax Amount',
        readonly=True,
        digits='Product Price',
        tracking=True
    )

    hs_code = fields.Char(
        string='HS Code',
        readonly=True,
        tracking=True
    )

    sales_type = fields.Char(
        string='Sales Type',
        readonly=True,
        tracking=True
    )

    tax_scenario = fields.Many2one(
        'digital.scenario',
        string='Tax Scenario',
        readonly=True,
        tracking=True
    )

    status = fields.Selection(
        [
            ('draft', 'Draft'),
            ('validated', 'Validated'),
            ('posted', 'Posted'),
            ('cancelled', 'Cancelled')
        ],
        string='Status',
        readonly=True,
        default='draft',
        tracking=True
    )

    fbr_reference = fields.Char(
        string='FBR Reference Number',
        readonly=True,
        tracking=True
    )

    creation_date = fields.Datetime(
        string='Creation Date',
        readonly=True,
        default=fields.Datetime.now
    )

    total_tax_with_surcharge = fields.Float(
        string='Total Tax (including Surcharge)',
        compute='_compute_total_tax',
        store=True
    )

    net_total = fields.Float(
        string='Net Total',
        compute='_compute_net_total',
        store=True
    )

    @api.depends('amount', 'tax_amount')
    def _compute_total_tax(self):
        for record in self:
            record.total_tax_with_surcharge = record.tax_amount

    @api.depends('amount', 'tax_amount')
    def _compute_net_total(self):
        for record in self:
            record.net_total = record.amount + record.tax_amount

    def name_get(self):
        result = []
        for record in self:
            name = f"{record.invoice_number} - {record.customer_id.name if record.customer_id else 'N/A'}"
            result.append((record.id, name))
        return result

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
         if not vals.get('invoice_number'):
            raise ValidationError(_('Invoice Number is required.'))
        return super().create(vals_list)
        

    def action_view_invoice(self):
        """Action to view the related digital invoice"""
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'digital.invoice',
            'res_id': self.invoice_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
