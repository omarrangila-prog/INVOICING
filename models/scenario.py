from odoo import fields, models


class DigitalScenario(models.Model):
    _name = 'digital.scenario'
    _description = 'Digital Scenario'
    _rec_name = 'name'
    _order = 'name asc'
 
    name = fields.Char(string='Scenario Code', required=True)
    description = fields.Char(string='Description')
    sales_type = fields.Char(string='Sales Type')
    tax_rate = fields.Float(string='Tax Rate (%)', default=0.0)
    sro_schedule = fields.Char(string='SRO Schedule No')
    sro_serial_no = fields.Char(string='SRO Item Serial No')
    active = fields.Boolean(default=True)

    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f"{rec.name} - {rec.description}" if rec.description else rec.name
    
    @classmethod
    def _name_search(cls, name='', domain=None, operator='ilike', limit=100, order=None):
        domain = domain or []
        if name:
            domain = ['|', ('name', operator, name), ('description', operator, name)] + domain
        return super()._name_search(name=name, domain=domain, operator=operator, limit=limit, order=order)
