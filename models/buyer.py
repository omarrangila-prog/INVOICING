from odoo import fields, models


class DigitalBuyer(models.Model):
    _name = 'digital.buyer'
    _description = 'Digital Invoice Buyer'

    name = fields.Char(string='Buyer Name', required=True)
    ntn = fields.Char(string='NTN')
    cnic = fields.Char(string='CNIC')
    province = fields.Char(string='Province')
    registration_type = fields.Char(string='Registration Type')
    stn = fields.Char(string='STN')
    address = fields.Text(string='Address')
    phone = fields.Char(string='Phone')
    email = fields.Char(string='Email')
    active = fields.Boolean(string='Active', default=True)
