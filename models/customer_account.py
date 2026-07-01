from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, MissingError, UserError


class CustomerAccount(models.Model):
    _name = 'customer.account'
    _description = 'Customer Account'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'code desc'

    company_id = fields.Many2one('res.company', string='Company',required=True,default=lambda self: self.env.company.id)

    code = fields.Char(
        string='Customer Code',
        readonly=True,
        copy=False,
        tracking=True
    )

    name = fields.Char(
        string='Customer Name',
        required=True,
        tracking=True
    )

    main_category_id = fields.Many2one(
        'customer.category',
        string='Customer Category',
        required=True,
        tracking=True,
        index=True
    )

    sub_category_id = fields.Many2one(
        'customer.subcategory',
        string='Sub Category',
        required=True,
        tracking=True,
        domain="[('category_id', '=', main_category_id)]"
    )
    account_type = fields.Selection(
        [('receivable', 'Receivable'), ('others', 'Others')],
        string='Account Type', required=True, default='receivable', tracking=True,index=True
    )

    opening_balance = fields.Float(
        string='Opening Balance',
        default=0.0,
        tracking=True
    )

    balance_type = fields.Selection(
        [
            ('debit', 'Debit'),
            ('credit', 'Credit')
        ],
        string='Debit/Credit',
        default='debit',
        tracking=True
    )

    credit_limit = fields.Float(
        string='Credit Limit',
        default=0.0,
        tracking=True
    )

    credit_days = fields.Integer(
        string='Credit Days',
        default=0,
        tracking=True
    )
    invoice_ids = fields.One2many('digital.invoice', 'buyer_id', string='Invoices')
    t_ent = fields.Integer(string='Total Invoices', compute='_compute_t_ent')
   

    active = fields.Boolean(
        default=True,
        tracking=True
    )

    ntn = fields.Char(string='NTN/CNIC', tracking=True)
    cnic = fields.Char(string='CNIC', visible=False, tracking=True)
    province = fields.Char(string='Province', tracking=True)
    registration_type = fields.Selection(
        [('registered', 'Registered'), ('unregistered', 'Unregistered')],
        string='Registration Type', required=True, default='registered', tracking=True,index=True
    )
    stn = fields.Char(string='STN', tracking=True)
    address = fields.Text(string='Address', tracking=True)
    phone = fields.Char(string='Phone', tracking=True)
    email = fields.Char(string='Email', tracking=True)

    @api.depends('invoice_ids')
    def _compute_t_ent(self):
        for rec in self:
            rec.t_ent = len(rec.invoice_ids)

    def action_view_invoices(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Invoices Book',
            'res_model': 'digital.invoice',
            'view_mode': 'list,form',
            'domain': [('buyer_id', '=', self.id)],
            'context': {'default_buyer_id': self.id},
        }

    def action_fetch_registration_type(self):
        """Call FBR's Get_Reg_Type endpoint with this customer's NTN/CNIC
        and set Registration Type from the response."""
        import requests
        self.ensure_one()

        if not self.ntn:
            raise UserError(_('Set NTN/CNIC before fetching the Registration Type from FBR.'))

        company = self.env.company
        token = company.fbr_sandbox_token if company.is_fbr_sandbox else company.fbr_token
        if not token:
            raise UserError(_(
                'FBR %s Token is not configured for this company.'
            ) % (_('Sandbox') if company.is_fbr_sandbox else _('Production')))

        url = 'https://gw.fbr.gov.pk/dist/v1/Get_Reg_Type'
        headers = {
            'Authorization': 'Bearer %s' % token.strip(),
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }
        payload = {
            'Registration_No': self.ntn,
        }

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
        except requests.exceptions.Timeout:
            raise UserError(_('FBR request timed out after 30 seconds.'))
        except requests.exceptions.ConnectionError as e:
            raise UserError(_('Connection error contacting FBR: %s') % str(e))

        try:
            data = response.json()
        except ValueError:
            raise UserError(_(
                'FBR returned an invalid (non-JSON) response (HTTP %s): %s'
            ) % (response.status_code, response.text[:300]))

        reg_type_text = (data.get('REGISTRATION_TYPE') or '').strip()
        if not reg_type_text:
            raise UserError(_('FBR response did not include a Registration Type.'))

        reg_type_key = reg_type_text.lower()
        valid_keys = [key for key, label in self._fields['registration_type'].selection]
        if reg_type_key not in valid_keys:
            raise UserError(_(
                'FBR returned an unrecognized Registration Type: "%s".'
            ) % reg_type_text)

        self.registration_type = reg_type_key

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Registration Type Updated'),
                'message': _('Set to "%s" (from FBR).') % reg_type_text,
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.client', 'tag': 'reload'},
            },
        }

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('code'):
                vals['code'] = self.env['ir.sequence'].next_by_code('customer.account.sequence') or '/'
        return super().create(vals_list)
    
    @api.onchange('main_category_id')
    def _onchange_main_category_id(self):
        self.sub_category_id = False

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

 