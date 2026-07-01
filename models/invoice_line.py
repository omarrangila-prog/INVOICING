from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class DigitalInvoiceLine(models.Model):
    _name = 'digital.invoice.line'
    _description = 'Digital Invoice Line'
    _order = 'sequence, id'

    invoice_id = fields.Many2one('digital.invoice', string='Invoice', ondelete='cascade', required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    display_type = fields.Selection([
        ('line_section', 'Section'),
        ('line_note', 'Note'),
    ], default=False, help='Technical field for the Section/Note row UI.')
    name = fields.Text(string='Description', help='Section title or Note text.')
    line_description = fields.Text(
        string='Item Description',
        help='Optional free-text note for this line item (e.g. extra specs, '
             'remarks). Independent from the Section/Note "name" field above — '
             'editing or styling this can never affect Section/Note behavior.'
    )
    product_id = fields.Many2one('item.master', string='Item', ondelete='restrict')
    hs_code = fields.Char(string='HS Code', related='product_id.hs_code_id.code', store=True, readonly=False)

    # Commercial UOM — shown on the invoice. Defaults to the item's
    # Commercial UOM (e.g. ROLL); falls back to the Regulatory UOM if no
    # Commercial UOM is set on the item. Price and Quantity below are
    # always entered in terms of this Commercial UOM.
    # Plain stored field (not related) so it snapshots at line-creation time
    # and stays editable per-line if needed.
    uom = fields.Char(string='UOM', store=True)

    price = fields.Float(string='Price', digits='Product Price',
                          help='Price per unit of Commercial UOM.')
    quantity = fields.Float(string='Quantity', default=1.0,
                             help='Quantity in Commercial UOM.')
    tax_exclusive = fields.Float(string='Tax Exclusive', compute='_compute_amounts', store=True)
    tax_rate = fields.Float(string='Tax Rate (%)', default=0.0)
    tax_amount = fields.Float(string='Tax Amount', compute='_compute_amounts', store=True)
    further_tax_rate = fields.Float(string='Further Tax Rate (%)', default=0.0)
    further_tax_amount = fields.Float(string='Further Tax Amount', compute='_compute_amounts', store=True)
    net_amount = fields.Float(string='Net Amount', compute='_compute_amounts', store=True)
    sro_schedule = fields.Char(string='SRO Schedule')
    item_sr_no = fields.Char(string='Item Sr No')
    sale_type = fields.Char(string='Sale Type')

    # -------------------------------------------------------------------------
    # Hidden Regulatory UOM-equivalent calculations
    # Not shown on the invoice form by default — surfaced as optional columns
    # at the end of the line table and rolled up into digital.invoice.fbr_net_total.
    # -------------------------------------------------------------------------
    fbr_uom = fields.Char(
        string='Regulatory UOM', related='product_id.uom_id.name', store=True, readonly=True)
    fbr_uom_rate = fields.Float(
        string='Rate per Regulatory UOM', store=True, digits='Product Price',
        help='Defaults from the Item Master\'s "Rate per Regulatory UOM" when '
             'the item is selected. Can be freely overridden per line — doing '
             'so recalculates Regulatory Gross/Tax/Further Tax/Net Amount as '
             'this Rate × the current Regulatory Qty.')
    fbr_quantity = fields.Float(
        string='Regulatory Qty', store=True,
        help='Defaults from Tax Exclusive ÷ Rate per Regulatory UOM when the '
             'item is selected. Can be freely overridden per line (e.g. a '
             'measured actual quantity) — doing so recalculates Regulatory '
             'Gross/Tax/Further Tax/Net Amount as the current Rate × this Qty.')
    fbr_gross_amount = fields.Float(
        string='Regulatory Gross Amount', compute='_compute_fbr_equivalent', store=True)
    fbr_tax_amount = fields.Float(
        string='Regulatory Tax Amount', compute='_compute_fbr_equivalent', store=True)
    fbr_further_tax_amount = fields.Float(
        string='Regulatory Further Tax Amount', compute='_compute_fbr_equivalent', store=True)
    fbr_net_amount = fields.Float(
        string='Regulatory Net Amount', compute='_compute_fbr_equivalent', store=True)

    @api.depends('price', 'quantity', 'tax_rate', 'further_tax_rate')
    def _compute_amounts(self):
        for line in self:
            line.tax_exclusive = line.price * line.quantity
            line.tax_amount = line.price * line.quantity * (line.tax_rate or 0.0) / 100.0
            line.further_tax_amount = line.price * line.quantity * (line.further_tax_rate or 0.0) / 100.0
            line.net_amount = line.tax_exclusive + line.tax_amount + line.further_tax_amount

    @api.depends('fbr_uom_rate', 'fbr_quantity', 'tax_rate', 'further_tax_rate')
    def _compute_fbr_equivalent(self):
        """Regulatory Gross/Tax/Further-Tax/Net Amount are derived purely
        from fbr_uom_rate x fbr_quantity — whatever those two currently are,
        whether auto-defaulted at item selection or manually overridden.
        They are NOT locked to the Commercial amounts. _check_fbr_net_amount_matches
        (constraint, below) and digital.invoice._check_fbr_regulatory_rates
        (called before FBR submission) are what enforce that the two sides
        reconcile — they don't reconcile automatically.
        """
        for line in self:
            line.fbr_gross_amount = (line.fbr_uom_rate or 0.0) * (line.fbr_quantity or 0.0)
            line.fbr_tax_amount = line.fbr_gross_amount * (line.tax_rate or 0.0) / 100.0
            line.fbr_further_tax_amount = line.fbr_gross_amount * (line.further_tax_rate or 0.0) / 100.0
            line.fbr_net_amount = (
                line.fbr_gross_amount + line.fbr_tax_amount + line.fbr_further_tax_amount)

    @api.constrains('display_type', 'product_id', 'price')
    def _check_display_type_requirements(self):
        for line in self:
            if line.display_type:
                if line.product_id or line.price:
                    raise ValidationError(_(
                        'A Section/Note line cannot have an Item or Price set.'))
            else:
                if not line.product_id:
                    raise ValidationError(_('Item is required for a regular invoice line.'))

    @api.constrains('fbr_net_amount', 'net_amount', 'fbr_uom_rate', 'fbr_quantity')
    def _check_fbr_net_amount_matches(self):
        """Block saving if the Regulatory side has been touched (rate or qty
        set) but doesn't reconcile with the Commercial Net Amount. Lines
        where neither is set yet are left alone — FBR submission itself is
        blocked separately (digital.invoice._check_fbr_regulatory_rates)
        until both are filled in, so this doesn't block ordinary invoicing
        for items that don't have Regulatory data configured yet.
        """
        for line in self:
            if not line.fbr_uom_rate and not line.fbr_quantity:
                continue
            if round(line.fbr_net_amount, 2) != round(line.net_amount, 2):
                raise ValidationError(_(
                    'Regulatory Net Amount (%.2f) does not match Net Amount '
                    '(%.2f) for item "%s". Adjust Rate per Regulatory UOM or '
                    'Regulatory Qty so both reconcile exactly before saving.'
                ) % (line.fbr_net_amount, line.net_amount, line.product_id.name or ''))

    @api.onchange('fbr_uom_rate')
    def _onchange_fbr_uom_rate(self):
        """First priority: keep Rate x Qty = Tax Exclusive. Editing the
        Rate recalculates Regulatory Qty to match."""
        if self.fbr_uom_rate:
            self.fbr_quantity = self.tax_exclusive / self.fbr_uom_rate
        else:
            self.fbr_quantity = 0.0

    @api.onchange('fbr_quantity')
    def _onchange_fbr_quantity(self):
        """First priority: keep Rate x Qty = Tax Exclusive. Editing the
        Qty recalculates Rate per Regulatory UOM to match."""
        if self.fbr_quantity:
            self.fbr_uom_rate = self.tax_exclusive / self.fbr_quantity
        else:
            self.fbr_uom_rate = 0.0

    @api.onchange('price', 'quantity')
    def _onchange_commercial_amounts(self):
        """First priority: when the Commercial Price/Quantity change (and
        therefore Tax Exclusive changes), keep Regulatory Qty in sync using
        the current Rate per Regulatory UOM — same Qty = Tax Exclusive ÷
        Rate relationship used at item selection."""
        if self.fbr_uom_rate:
            self.fbr_quantity = self.tax_exclusive / self.fbr_uom_rate
        else:
            self.fbr_quantity = 0.0

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.price = self.product_id.sale_price
            self.tax_rate = self.product_id.sales_tax
            self.further_tax_rate = self.product_id.further_tax
            self.uom = self.product_id.pack_uom_id.name or self.product_id.uom_id.name
            # First priority, always re-derived fresh whenever the item is
            # selected or changed: Regulatory Qty = Tax Exclusive ÷ Rate per
            # Regulatory UOM (from the Item Master). This overrides any
            # prior manual edits on this line, since the item itself changed.
            self.fbr_uom_rate = self.product_id.fbr_uom_rate
            self.fbr_quantity = (
                self.tax_exclusive / self.fbr_uom_rate if self.fbr_uom_rate else 0.0)
            if self.invoice_id.scenario_id:
                self._apply_scenario(self.invoice_id.scenario_id)
            
    def _apply_scenario(self, scenario):
        if scenario:
            self.sale_type = scenario.sales_type
            self.sro_schedule = scenario.sro_schedule
            self.item_sr_no = scenario.sro_serial_no
            self.tax_rate = scenario.tax_rate