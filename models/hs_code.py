from odoo import api, fields, models


class ItemHsCode(models.Model):
    _name = 'item.hs.code'
    _description = 'Item HS Code'
    _rec_name = 'code'

    code = fields.Char(string='HS Code', required=True)
    description = fields.Text(string='Description')
    default_uom = fields.Char(string='Default UOM')
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('item_hs_code_unique', 'unique(code)', 'HS Code must be unique.')
    ]