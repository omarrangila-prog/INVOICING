from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, MissingError, UserError


class ItemMaster(models.Model):
    _name = 'item.master'
    _description = 'Item Master'
    _order = 'id desc'

    company_id = fields.Many2one('res.company', string='Company',required=True,default=lambda self: self.env.company.id)

    main_category_id = fields.Many2one(
        'item.category', string='Main Category', required=True, ondelete='restrict'
    )
    name = fields.Char(string='Item Name', required=True)
    code = fields.Char(string='Item Code', readonly=True, copy=False)
    sub_category_id = fields.Many2one(
        'item.subcategory', string='Sub Category', required=True, ondelete='restrict',
        domain="[('category_id', '=', main_category_id)]"
    )
    isbn = fields.Char(string='ISBN')
    sale_price = fields.Float(string='Sale Price')
    purchase_price = fields.Float(string='Purchase Price')
    uom_id = fields.Many2one(
        'item.uom', string='Regulatory UOM', required=True, ondelete='restrict',
        help='The official/statutory unit (e.g. KG) used for HS-code and '
             'FBR regulatory purposes.'
    )
    pack_uom_id = fields.Many2one(
        'item.uom', string='Commercial UOM', ondelete='restrict',
        help='The unit actually used when invoicing the customer '
             '(e.g. ROLL, BOX). Shown on the invoice line.'
    )
    qty_per_pack = fields.Integer(string='Qty (In 1 Pack)')
    fbr_uom_rate = fields.Float(
        string='Rate per Regulatory UOM',
        digits='Product Price',
        help='Fixed/notified rate per the Regulatory UOM (e.g. per KG). '
             'Used to back-calculate the Regulatory quantity for hidden '
             'compliance-equivalent reporting on invoice lines, independent '
             'of the Commercial UOM price.'
    )
    discount = fields.Float(string='Discount')
    discount_type = fields.Selection(
        [('fixed', 'Fixed'), ('percentage', 'Percentage')],
        string='Discount Type', default='fixed'
    )
    image = fields.Binary(string='Picture', attachment=True)
    active = fields.Boolean(default=True)
    hs_code_id = fields.Many2one(
        'item.hs.code', string='HS Code', required=True, ondelete='restrict'
    )
    sro_schedule = fields.Char(string='SRO Schedule')
    item_serial_no = fields.Char(string='Item Serial No')
    sales_tax = fields.Float(string='Sales Tax')
    further_tax = fields.Float(string='Further Tax')
    scenario_id = fields.Many2one(
        'digital.scenario', string='Scenario', ondelete='restrict'
    )
    hs_description = fields.Text(
        string='HS Description', related='hs_code_id.description', readonly=True
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('code'):
                vals['code'] = self.env['ir.sequence'].next_by_code('item.master.sequence') or '/'
        records = super().create(vals_list)
        records._populate_from_hs_code()
        return records

    def write(self, vals):
        result = super().write(vals)
        if 'hs_code_id' in vals:
            self._populate_from_hs_code()
        return result

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
    
    @api.onchange('hs_code_id')
    def _onchange_hs_code_id(self):
        self._populate_from_hs_code()

    @api.onchange('main_category_id')
    def _onchange_main_category_id(self):
        self.sub_category_id = False

    def _populate_from_hs_code(self):
        for record in self:
            if record.hs_code_id:
                default_uom = record.hs_code_id.default_uom
                if default_uom:
                    uom = self.env['item.uom'].search([('name', '=', default_uom)], limit=1)
                    if uom:
                        record.uom_id = uom

    @api.constrains('main_category_id', 'name', 'sub_category_id', 'uom_id', 'hs_code_id')
    def _check_required_fields(self):
        for record in self:
            if not record.main_category_id:
                raise ValidationError(_('Main Category is required.'))
            if not record.name:
                raise ValidationError(_('Item Name is required.'))
            if not record.sub_category_id:
                raise ValidationError(_('Sub Category is required.'))
            if not record.uom_id:
                raise ValidationError(_('UOM is required.'))
            if not record.hs_code_id:
                raise ValidationError(_('HS Code is required.'))

    def action_fetch_regulatory_uom(self):
        """Call FBR's HS_UOM reference endpoint with this item's HS Code
        and set Regulatory UOM (uom_id) from the response."""
        import requests
        self.ensure_one()

        if not self.hs_code_id or not self.hs_code_id.code:
            raise UserError(_('Set an HS Code before fetching the Regulatory UOM from FBR.'))

        company = self.env.company
        token = company.fbr_sandbox_token if company.is_fbr_sandbox else company.fbr_token
        if not token:
            raise UserError(_(
                'FBR %s Token is not configured for this company.'
            ) % (_('Sandbox') if company.is_fbr_sandbox else _('Production')))

        url = 'https://gw.fbr.gov.pk/pdi/v2/HS_UOM'
        headers = {
            'Authorization': 'Bearer %s' % token.strip(),
            'Accept': 'application/json',
        }
        params = {
            'hs_code': self.hs_code_id.code,
            'annexure_id': 3,
        }

        try:
            response = requests.get(url, headers=headers, params=params, timeout=30)
        except requests.exceptions.Timeout:
            raise UserError(_('FBR request timed out after 30 seconds.'))
        except requests.exceptions.ConnectionError as e:
            raise UserError(_('Connection error contacting FBR: %s') % str(e))

        if not response.ok:
            raise UserError(_(
                'FBR returned an error (HTTP %s): %s'
            ) % (response.status_code, response.text[:300]))

        try:
            data = response.json()
        except ValueError:
            raise UserError(_('FBR returned an invalid (non-JSON) response.'))

        if not data or not isinstance(data, list):
            raise UserError(_('FBR returned no UOM for HS Code %s.') % self.hs_code_id.code)

        description = (data[0].get('description') or '').strip()
        if not description:
            raise UserError(_('FBR response did not include a UOM description.'))

        Uom = self.env['item.uom']
        uom = Uom.search([('name', '=', description)], limit=1)
        if not uom:
            uom = Uom.create({'name': description})

        self.uom_id = uom.id

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Regulatory UOM Updated'),
                'message': _('Set to "%s" (from FBR).') % description,
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.client', 'tag': 'reload'},
            },
        }

    @api.model
    def fetch_hs_code_details(self, hs_code_id):
        if not hs_code_id:
            return {
                'uom_id': False,
                # 'sales_tax': 0.0,
                # 'further_tax': 0.0,
            }
        hs_code = self.env['item.hs.code'].browse(hs_code_id)
        return {
            'uom_id': self.env['item.uom'].search([('name', '=', hs_code.default_uom)], limit=1).id if hs_code.default_uom else False,
            # 'sales_tax': hs_code.sales_tax,
            # 'further_tax': hs_code.further_tax,
        }
