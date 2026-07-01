from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError, MissingError


class DigitalInvoice(models.Model):
    _name = 'digital.invoice'
    _description = 'Digital Invoice'
    _order = 'id desc'
    _rec_name = 'bill_no'

    company_id = fields.Many2one('res.company', string='Company',required=True,default=lambda self: self.env.company.id)

    company_is_sandbox = fields.Boolean(
    related='company_id.is_fbr_sandbox', 
    string='Is Sandbox', 
    readonly=True)

    is_sn001 = fields.Boolean(
    compute='_compute_is_sn001', store=False)

    fbr_qr_code = fields.Binary(
    string='QR Code',
    compute='_compute_fbr_qr_code',
    store=False)

    fbr_qr_report = fields.Char(
    string='FBR QR Report',
    compute='_compute_fbr_qr_code',
    store=True)

    fbr_environment = fields.Selection([
    ('sandbox', 'Sandbox / Test'),
    ('production', 'Production / Live'),
    ], string='FBR Environment', readonly=True, copy=False)

    bill_no = fields.Char(string='Bill No', copy=False, readonly=True, default='New')
    invoice_date = fields.Date(string='Date', required=True, default=fields.Date.context_today)
    due_days = fields.Integer(string='Due Days', default=30)
    reference = fields.Char(string='Reference')
    currency_id = fields.Many2one(
        'res.currency', string='Currency', required=True,
        default=lambda self: self.env.company.currency_id)
    buyer_id = fields.Many2one('customer.account', string='Buyer', ondelete='restrict')
    scenario_id = fields.Many2one(
    'digital.scenario', string='Scenario', ondelete='restrict',
    default=lambda self: self.env['digital.scenario'].search(
        [('name', '=', 'SN001')], limit=1).id)
    invoice_line_ids = fields.One2many(
        'digital.invoice.line', 'invoice_id', string='Invoice Items', copy=True)
    subtotal = fields.Monetary(string='Subtotal', compute='_compute_totals', store=True)
    gst_amount = fields.Monetary(string='Total GST', compute='_compute_totals', store=True)
    fst_amount = fields.Monetary(string='Total FST', compute='_compute_totals', store=True)
    tax_amount = fields.Monetary(string='Total Tax', compute='_compute_totals', store=True)
    grand_total = fields.Monetary(string='Grand Total', compute='_compute_totals', store=True)
    fbr_net_total = fields.Monetary(
        string='Net Amount (Regulatory)', compute='_compute_totals', store=True,
        help='Sum of line amounts expressed in each item\'s Regulatory UOM '
             '(e.g. KG) instead of the Commercial UOM. Should always '
             'match Subtotal — shown for compliance reconciliation purposes.')
    fbr_id = fields.Char(string='FBR ID')
    fbr_date = fields.Date(string='FBR Date')
    fbr_validated = fields.Boolean(string='FBR Validated', default=False, copy=False)
    edit_note = fields.Text(string='Edit Note')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('validated', 'Validated'),
        ('posted', 'Posted'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', readonly=True)

    # Buyer related fields
    buyer_ntn = fields.Char(string='NTN/CNIC', related='buyer_id.ntn', store=True)
    buyer_province = fields.Char(string='Province', related='buyer_id.province', store=True)
    buyer_registration_type = fields.Selection(
        string='Registration Type', related='buyer_id.registration_type', store=True)
    buyer_stn = fields.Char(string='STN', related='buyer_id.stn', store=True)
    buyer_address = fields.Text(string='Address', related='buyer_id.address', store=True)
    buyer_phone = fields.Char(string='Phone', related='buyer_id.phone', store=True)
    buyer_email = fields.Char(string='Email', related='buyer_id.email', store=True)

    # Scenario related fields
    scenario_description = fields.Char(
        related='scenario_id.description', readonly=True, string='Description')
    scenario_sales_type = fields.Char(
        related='scenario_id.sales_type', readonly=True, string='Sales Type')
    scenario_tax_rate = fields.Float(
        related='scenario_id.tax_rate', readonly=True, string='Tax Rate (%)')
    scenario_sro_schedule = fields.Char(
        related='scenario_id.sro_schedule', readonly=True, string='SRO Schedule')
    scenario_sro_serial_no = fields.Char(
        related='scenario_id.sro_serial_no', readonly=True, string='SRO Serial No')

    # -------------------------------------------------------------------------
    # ORM overrides
    # -------------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('bill_no', 'New') == 'New':
                vals['bill_no'] = self.env['ir.sequence'].next_by_code(
                    'digital.invoice.sequence') or 'New'
        records = super().create(vals_list)
        records._check_state()
        records._create_invoice_book_entry()
        return records

    def write(self, vals):
         # Block editing of posted invoices
        for record in self:
            if record.state == 'posted' and not self.env.context.get('no_reset_draft'):
                raise UserError(_('Posted invoices cannot be edited. They have been submitted to FBR.'))
        
        # If validated invoice is edited — reset to draft and clear FBR validation
        edit_fields = {
            'buyer_id', 'invoice_date', 'invoice_line_ids',
            'scenario_id', 'reference', 'currency_id'
        }
        # Only reset if user is editing — not when system writes state/fbr fields
        if not self.env.context.get('no_reset_draft'):
            for record in self:
                if record.state == 'validated' and any(f in vals for f in edit_fields):
                    vals['state'] = 'draft'
                    vals['fbr_validated'] = False

        result = super().write(vals)
        self._check_state()
        return result

    def _check_state(self):
        for record in self:
            if record.state not in ('draft', 'cancelled') and not record.invoice_line_ids:
                record.state = 'draft'
                record.fbr_validated = False

    def unlink(self):
        for invoice in self:
            if invoice.state == 'posted':
                raise UserError(_(
                    'You cannot delete a posted invoice. '
                    'Posted invoices are submitted to FBR and cannot be deleted.'
                ))
        return super().unlink()

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
    
    @api.depends('fbr_id')
    def _compute_fbr_qr_code(self):
        import qrcode
        import base64
        from io import BytesIO
        for record in self:
            if record.fbr_id:
                qr = qrcode.QRCode(version=1, box_size=4, border=2)
                qr.add_data(record.fbr_id)
                qr.make(fit=True)
                img = qr.make_image(fill_color='black', back_color='white')
                buffer = BytesIO()
                img.save(buffer, format='PNG')
                qr_data = base64.b64encode(buffer.getvalue()).decode('utf-8')
                record.fbr_qr_code = qr_data
                record.fbr_qr_report = qr_data

            else:
                record.fbr_qr_code = False
                record.fbr_qr_report = False

    @api.depends('scenario_id')
    def _compute_is_sn001(self):
        for rec in self:
            rec.is_sn001 = bool(
                rec.scenario_id and rec.scenario_id.name and
                'SN001' in rec.scenario_id.name)
                
    # -------------------------------------------------------------------------
    # Onchange
    # -------------------------------------------------------------------------
    @api.onchange('scenario_id')
    def _onchange_scenario_id(self):
        if self.scenario_id:
            is_sn001 = self.scenario_id.name and 'SN001' in self.scenario_id.name
            for line in self.invoice_line_ids:
                line.sale_type = self.scenario_id.sales_type
                line.sro_schedule = self.scenario_id.sro_schedule
                line.item_sr_no = self.scenario_id.sro_serial_no
                line.tax_rate = self.scenario_id.tax_rate
                if is_sn001:
                    line.further_tax_rate = 0.0
                    line.further_tax_amount = 0.0
        else:
            for line in self.invoice_line_ids:
                line.sale_type = False
                line.sro_schedule = False
                line.item_sr_no = False
                if line.product_id:
                    line.tax_rate = line.product_id.sales_tax

    # -------------------------------------------------------------------------
    # Computed
    # -------------------------------------------------------------------------
    @api.depends(
        'invoice_line_ids.tax_exclusive',
        'invoice_line_ids.tax_amount',
        'invoice_line_ids.further_tax_amount',
        'invoice_line_ids.fbr_net_amount')
    def _compute_totals(self):
        for invoice in self:
            subtotal = sum(line.tax_exclusive for line in invoice.invoice_line_ids)
            gst_amount = sum(line.tax_amount for line in invoice.invoice_line_ids)
            fst_amount = sum(line.further_tax_amount for line in invoice.invoice_line_ids)
            invoice.subtotal = subtotal
            invoice.gst_amount = gst_amount
            invoice.fst_amount = fst_amount
            invoice.tax_amount = gst_amount + fst_amount
            invoice.grand_total = subtotal + invoice.tax_amount
            invoice.fbr_net_total = sum(line.fbr_net_amount for line in invoice.invoice_line_ids)

    # -------------------------------------------------------------------------
    # Constraints
    # -------------------------------------------------------------------------
    @api.constrains('buyer_id', 'scenario_id')
    def _check_invoice_requirements(self):
        for invoice in self:
            if not invoice.buyer_id:
                raise ValidationError(_('Buyer is required to save the invoice.'))
            if not invoice.scenario_id:
                raise ValidationError(_('Scenario is required to save the invoice.'))

    # -------------------------------------------------------------------------
    # State actions
    # -------------------------------------------------------------------------
    def action_post(self):
        for invoice in self:
            if invoice.state != 'validated':
                raise ValidationError(_('Invoice must be validated before posting to FBR.'))
            invoice.state = 'posted'

    def action_new_invoice(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'digital.invoice',
            'view_mode': 'form',
            'target': 'current',
            'context': {'default_state': 'draft'},
        }

    def action_generate_pdf(self):
        return self.env.ref('keleven_invoicing.action_report_digital_invoice').report_action(self)

    def _get_di_logo(self):
        import base64
        import os
        logo_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'static', 'src', 'img', 'di_logo.png')
        try:
            with open(logo_path, 'rb') as f:
                return base64.b64encode(f.read()).decode('utf-8')
        except Exception:
            return False
    # -------------------------------------------------------------------------
    # FBR API
    # -------------------------------------------------------------------------
    def _check_fbr_regulatory_rates(self):
        """Block FBR validate/post unless every line has:
        1. Regulatory UOM, Rate per Regulatory UOM, and Regulatory Qty all set
           — otherwise the FBR payload would carry a blank/zero field.
        2. Regulatory Net Amount exactly matching Net Amount — this is also
           enforced as a save-time constraint on digital.invoice.line
           (_check_fbr_net_amount_matches), this is a defensive re-check.
        """
        for invoice in self:
            real_lines = invoice.invoice_line_ids.filtered(lambda l: not l.display_type)
            missing = real_lines.filtered(
                lambda l: not l.fbr_uom or not l.fbr_uom_rate or not l.fbr_quantity)
            if missing:
                item_names = ', '.join(missing.mapped('product_id.name'))
                raise UserError(_(
                    'Cannot submit to FBR: the following item(s) are missing '
                    'Regulatory UOM, Rate per Regulatory UOM, or Regulatory '
                    'Qty — all three are required: %s. '
                    'Set the rate on these items before validating or posting.'
                ) % item_names)

            mismatched = real_lines.filtered(
                lambda l: round(l.fbr_net_amount, 2) != round(l.net_amount, 2))
            if mismatched:
                item_names = ', '.join(mismatched.mapped('product_id.name'))
                raise UserError(_(
                    'Cannot submit to FBR: Regulatory Net Amount does not '
                    'match Net Amount for: %s. Adjust Rate per Regulatory '
                    'UOM or Regulatory Qty so both reconcile exactly.'
                ) % item_names)
            
    def _get_fbr_token(self):
        company = self.env.company
        if company.is_fbr_sandbox:
            token = company.fbr_sandbox_token
            if not token:
                raise UserError(_('FBR Sandbox Token is not configured.'))
        else:
            token = company.fbr_token
            if not token:
                raise UserError(_('FBR Production Token is not configured.'))
        return token

    def _build_fbr_payload(self):
        self.ensure_one()
        company = self.env.company
        items = []
        for line in self.invoice_line_ids.filtered(lambda l: not l.display_type):
            items.append({
                "hsCode": line.hs_code or "",
                "productDescription": line.product_id.name if line.product_id else "",
                "rate": f"{int(line.tax_rate)}%" if line.tax_rate else "0%",
                "uoM": line.fbr_uom or "",
                "quantity": round(line.fbr_quantity or 0.0, 2),
                "totalValues": round(line.fbr_net_amount or 0.0, 2),
                "valueSalesExcludingST": round(line.fbr_gross_amount or 0.0, 2),
                "salesTaxApplicable": round(line.fbr_tax_amount or 0.0, 2),
                "fixedNotifiedValueOrRetailPrice": 0.0,
                "salesTaxWithheldAtSource": 0.0,
                "extraTax": 0.0,
                "furtherTax": round(line.fbr_further_tax_amount or 0.0, 2),
                "sroScheduleNo": line.sro_schedule or "",
                "fedPayable": 0.0,
                "discount": 0.0,
                "saleType": line.sale_type or "Goods at standard rate (default)",
                "sroItemSerialNo": line.item_sr_no or "",
            })

        return {
            "invoiceType": "Sale Invoice",
            "invoiceDate": str(self.invoice_date),
            "sellerBusinessName": company.fbr_business_name or "",
            "sellerNTNCNIC": company.fbr_ntn or "",
            "sellerProvince": company.fbr_business_province or "",
            "sellerAddress": company.fbr_business_address or "",
            "buyerNTNCNIC": self.buyer_ntn or "",
            "buyerBusinessName": self.buyer_id.name if self.buyer_id else "",
            "buyerProvince": self.buyer_province or "",
            "buyerAddress": self.buyer_address or "",
            "buyerRegistrationType": self.buyer_registration_type.capitalize() if self.buyer_registration_type else "",
            "scenarioId": self.scenario_id.name if self.scenario_id else "",
            "sourceInvoiceNo": (self.bill_no or "").replace('/', '-'),
            "items": items,
        }

    def _call_fbr_api(self, validate=True):
        import requests
        import json
        import logging
        _logger = logging.getLogger(__name__)

        self.ensure_one()
        token = self._get_fbr_token()
        if self.env.company.is_fbr_sandbox:
            if validate:
                url = "https://gw.fbr.gov.pk/di_data/v1/di/validateinvoicedata_sb"
            else:
                url = "https://gw.fbr.gov.pk/di_data/v1/di/postinvoicedata_sb"
        else:
            if validate:
                url = "https://gw.fbr.gov.pk/di_data/v1/di/validateinvoicedata"
            else:
                url = "https://gw.fbr.gov.pk/di_data/v1/di/postinvoicedata"
        
        payload = self._build_fbr_payload()
        json_body = json.dumps(payload, separators=(',', ':'))

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": "Bearer %s" % token.strip(),
            "User-Agent": "FBR-Integration-Client",
            "Accept-Encoding": "gzip, deflate, br",
        }

        _logger.info("FBR API | Invoice: %s | URL: %s", self.bill_no, url)

        fbr_invoice_number = ''
        fbr_date = ''
        raw = ''
        is_success = False
        error_msg = ''

        try:
            response = requests.post(url, data=json_body, headers=headers, timeout=30)
            raw = response.text

            if not raw or not raw.strip():
                error_msg = 'Empty response from FBR server.'
                is_success = False
            else:
                result = response.json()
                fbr_invoice_number = result.get('invoiceNumber', '')
                fbr_date = result.get('dated', '')
                # is_invalid = 'invalid' in raw.lower()
                # is_success = response.ok and not is_invalid
                # if not is_success:
                #     error_msg = result.get('message') or result.get('status') or 'FBR returned invalid response.'
                validation_response = result.get('validationResponse', {})
                status_code = validation_response.get('statusCode', '')
                is_success = response.ok and status_code not in ('01', '02', '03')
                error_msg_from_fbr = validation_response.get('error', '') or result.get('message', '')
                if not is_success:
                    error_msg = error_msg_from_fbr or 'FBR returned invalid response.'

        except requests.exceptions.Timeout:
            error_msg = 'Request timed out after 30 seconds.'
            is_success = False
        except requests.exceptions.ConnectionError as e:
            error_msg = 'Connection error: %s' % str(e)
            is_success = False
        except Exception as e:
            error_msg = 'Unexpected error: %s' % str(e)
            is_success = False

        # Save log regardless of success or failure
        self.env['digital.fbr.log'].create({
            'invoice_id': self.id,
            'invoice_number': self.bill_no,
            'action_type': 'validate' if validate else 'post',
            'url': url,
            'request_payload': json_body,
            'response_raw': raw,
            'fbr_invoice_number': fbr_invoice_number,
            'fbr_date': fbr_date,
            'status': 'success' if is_success else 'failed',
            'error_message': error_msg if not is_success else False,
        })

        return is_success, fbr_invoice_number, fbr_date, error_msg

    def action_fbr_validate(self):
        self.ensure_one()
        if not self.invoice_line_ids:
            raise UserError(_('Invoice must have at least one item line before validating.'))
        self._check_fbr_regulatory_rates()
        is_success, fbr_number, fbr_date, error_msg = self._call_fbr_api(validate=True)

        if is_success:
            self.with_context(no_reset_draft=True).write({'state': 'validated','fbr_validated': True})
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('FBR Validation Successful'),
                    'message': _('Invoice validated by FBR. FBR No: %s') % (fbr_number or 'N/A'),
                    'type': 'success',
                    'sticky': False,
                    'next': {'type': 'ir.actions.client', 'tag': 'reload'},
                },
            }
        else:
            self.write({'state': 'draft', 'fbr_validated': False})
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('FBR Validation Failed'),
                    'message': error_msg or _('Validation failed. Check FBR Logs for details.'),
                    'type': 'danger',
                    'sticky': True,
                },
            }

    def action_fbr_post(self):
        self.ensure_one()

        if not self.fbr_validated:
            raise UserError(_(
                'You must validate with FBR first before posting. '
                'Click "Validate FBR" and ensure it succeeds.'))
        if not self.invoice_line_ids:
            raise UserError(_('Invoice must have at least one item line before posting.'))
        self._check_fbr_regulatory_rates()
        is_success, fbr_number, fbr_date, error_msg = self._call_fbr_api(validate=False)

        if is_success:
            self.with_context(no_reset_draft=True).write({
                'fbr_id': fbr_number,
                'fbr_date': fbr_date,
                'state': 'posted',
                'fbr_environment': 'sandbox' if self.env.company.is_fbr_sandbox else 'production',
            })
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Posted to FBR Successfully'),
                    'message': _('Invoice posted. FBR No: %s') % (fbr_number or 'N/A'),
                    'type': 'success',
                    'sticky': False,
                    'next': {'type': 'ir.actions.client', 'tag': 'reload'},
                },
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('FBR Post Failed'),
                    'message': error_msg or _('Post failed. Check FBR Logs for details.'),
                    'type': 'danger',
                    'sticky': True,
                },
            }

    # -------------------------------------------------------------------------
    # Invoice Book
    # -------------------------------------------------------------------------
    def _create_invoice_book_entry(self):
        InvoiceBook = self.env['digital.invoice.book']
        for invoice in self:
            real_lines = invoice.invoice_line_ids.filtered(lambda l: not l.display_type)
            if real_lines:
                for line in real_lines:
                    InvoiceBook.create({
                        'invoice_id': invoice.id,
                        'invoice_number': invoice.bill_no,
                        'customer_id': invoice.buyer_id.id,
                        'invoice_date': invoice.invoice_date,
                        'item_name': line.product_id.name if line.product_id else '',
                        'quantity': line.quantity,
                        'amount': line.tax_exclusive,
                        'tax_amount': line.tax_amount,
                        'hs_code': line.hs_code,
                        'sales_type': line.sale_type,
                        'status': invoice.state,
                        'fbr_reference': invoice.fbr_id,
                    })

    # -------------------------------------------------------------------------
    # Dashboard
    # -------------------------------------------------------------------------
    @api.model
    def get_dashboard_data(self):
        from datetime import date
        from dateutil.relativedelta import relativedelta

        today = date.today()
        month_start = today.replace(day=1)
        month_end = (month_start + relativedelta(months=1)) - relativedelta(days=1)

        total_invoices = self.search_count([
            ('invoice_date', '>=', month_start),
            ('invoice_date', '<=', month_end),
            ('state', '!=', 'cancelled'),
        ])
        invoices_month = self.search([
            ('invoice_date', '>=', month_start),
            ('invoice_date', '<=', month_end),
            ('state', '!=', 'cancelled'),
        ])
        total_revenue = sum(inv.grand_total for inv in invoices_month)
        total_tax = sum(inv.tax_amount for inv in invoices_month)
        fbr_posted = self.search_count([
            ('invoice_date', '>=', month_start),
            ('invoice_date', '<=', month_end),
            ('state', '=', 'posted'),
            ('fbr_id', '!=', False),
        ])
        draft_invoices = self.search_count([('state', '=', 'draft')])
        avg_invoice = total_revenue / total_invoices if total_invoices > 0 else 0

        return {
            'total_invoices': total_invoices,
            'total_revenue': total_revenue,
            'total_tax': total_tax,
            'total_customers': self.env['customer.account'].search_count([('active', '=', True)]),
            'fbr_posted': fbr_posted,
            'draft_invoices': draft_invoices,
            'avg_invoice': avg_invoice,
            'total_items': self.env['item.master'].search_count([('active', '=', True)]),
        }