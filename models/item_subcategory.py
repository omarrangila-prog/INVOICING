from odoo import api, fields, models


class ItemSubcategory(models.Model):
    _name = 'item.subcategory'
    _description = 'Item Sub Category'

    name = fields.Char(string='Sub Category', required=True)
    category_id = fields.Many2one(
        'item.category', string='Main Category', required=True, ondelete='cascade'
    )
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('item_subcategory_name_unique', 'unique(name, category_id)', 'Sub category must be unique for this category.')
    ]
