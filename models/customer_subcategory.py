from odoo import models, fields


class CustomerSubcategory(models.Model):
    _name = 'customer.subcategory'
    _description = 'Customer Sub-Category'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name asc'

    name = fields.Char(
        string='Sub-Category Name',
        required=True,
        tracking=True
    )
    
    category_id = fields.Many2one(
        'customer.category',
        string='Category',
        required=True,
        tracking=True,
        ondelete='cascade'
    )
    
    active = fields.Boolean(
        default=True,
        tracking=True
    )

    def name_get(self):
        result = []
        for record in self:
            result.append((record.id, record.name))
        return result
