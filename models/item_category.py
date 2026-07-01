from odoo import api, fields, models


class ItemCategory(models.Model):
    _name = 'item.category'
    _description = 'Item Category'

    name = fields.Char(string='Main Category', required=True)
    active = fields.Boolean(default=True)
    subcategory_ids = fields.One2many(
        'item.subcategory', 'category_id', string='Sub Categories'
    )
    item_count = fields.Integer(
        string='Items', compute='_compute_item_count'
    )

    _sql_constraints = [
        ('item_category_name_unique', 'unique(name)', 'Category name must be unique.')
    ]

    @api.depends('subcategory_ids')
    def _compute_item_count(self):
        for record in self:
            record.item_count = len(record.subcategory_ids)
