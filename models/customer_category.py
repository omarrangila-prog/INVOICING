from odoo import models, fields


class CustomerCategory(models.Model):
    _name = 'customer.category'
    _description = 'Customer Category'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name asc'

    name = fields.Char(
        string='Category Name',
        required=True,
        tracking=True
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
