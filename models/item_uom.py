from odoo import api, fields, models


class ItemUom(models.Model):
    _name = 'item.uom'
    _description = 'Item Unit of Measure'

    name = fields.Char(string='Unit of Measure', required=True)
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('item_uom_name_unique', 'unique(name)', 'Unit of Measure name must be unique.')
    ]
