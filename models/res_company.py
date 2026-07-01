from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    fbr_token = fields.Char(
        string='Production Token',
        copy=False,
        groups='base.group_system'  # only admin can see/edit
    )
    fbr_sandbox_token = fields.Char(string='FBR Sandbox Token')
    is_fbr_sandbox = fields.Boolean(string='Use Sandbox/Testing Environment', default=False)
    fbr_ntn = fields.Char(string='NTN/CNIC',groups='base.group_system')
    fbr_business_name = fields.Char(string='Business Name',groups='base.group_system')
    fbr_business_address = fields.Text(string='Business Address',groups='base.group_system')
    fbr_business_province = fields.Char(string='Business Province',groups='base.group_system')

    fbr_di_logo = fields.Binary(string='FBR DI Logo')

    @api.depends('fbr_token')
    def _compute_fbr_di_logo(self):
        import base64, os
        logo_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'static', 'src', 'img', 'di_logo.png')
        for company in self:
            if os.path.exists(logo_path):
                with open(logo_path, 'rb') as f:
                    company.fbr_di_logo = base64.b64encode(f.read()).decode()
            else:
                company.fbr_di_logo = False