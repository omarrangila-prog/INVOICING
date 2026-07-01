from odoo import fields, models
from odoo.exceptions import MissingError

class DigitalFbrLog(models.Model):
    _name = 'digital.fbr.log'
    _description = 'FBR API Log'
    _order = 'id desc'
    _rec_name = 'invoice_number'

    company_id = fields.Many2one(
        'res.company', string='Company',
        related='invoice_id.company_id', store=True, readonly=True)

    invoice_id = fields.Many2one(
        'digital.invoice', string='Invoice', ondelete='set null')
    invoice_number = fields.Char(string='Invoice Number', readonly=True)
    action_type = fields.Selection([
        ('validate', 'Validate'),
        ('post', 'Post'),
    ], string='Action', readonly=True)
    url = fields.Char(string='API URL', readonly=True)
    request_payload = fields.Text(string='Request JSON', readonly=True)
    response_raw = fields.Text(string='Response JSON', readonly=True)
    fbr_invoice_number = fields.Char(string='FBR Invoice Number', readonly=True)
    fbr_date = fields.Char(string='FBR Date', readonly=True)
    status = fields.Selection([
        ('success', 'Success'),
        ('failed', 'Failed'),
    ], string='Status', readonly=True)
    error_message = fields.Text(string='Error Message', readonly=True)
    create_date = fields.Datetime(string='Date', readonly=True)
    create_uid = fields.Many2one('res.users', string='Called By', readonly=True)

    def read(self, fields=None, load='_classic_read'):
        if not self.env.su:
            valid_ids = [
                record.id for record in self
                if not record.company_id or record.company_id.id in self.env.companies.ids
            ]
            if len(valid_ids) != len(self):
                if not valid_ids:
                    raise MissingError('')
                return self.browse(valid_ids).read(fields=fields, load=load)
        return super().read(fields=fields, load=load)