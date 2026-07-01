/* Dashboard-specific JavaScript */

odoo.define('invoicing.dashboard_widget', function (require) {
    'use strict';

    var Widget = require('web.Widget');
    var rpc = require('web.rpc');

    var DashboardWidget = Widget.extend({
        template: 'invoicing.dashboard_widget',

        start: function () {
            var self = this;
            return this._super().then(function () {
                self._load_kpi_data();
            });
        },

        _load_kpi_data: function () {
            var self = this;
            
            // Load KPI metrics
            rpc.query({
                model: 'digital.invoice',
                method: 'get_dashboard_data',
                args: [],
            }).then(function (data) {
                self._render_kpis(data);
            });

            // Load recent invoices
            rpc.query({
                model: 'digital.invoice',
                method: 'search_read',
                domain: [['state', '!=', 'cancelled']],
                fields: ['bill_no', 'invoice_date', 'buyer_id', 'grand_total', 'state'],
                limit: 5,
                order: 'invoice_date desc',
            }).then(function (invoices) {
                self._render_recent_invoices(invoices);
            });
        },

        _render_kpis: function (data) {
            // Render KPI data
            console.log('Dashboard KPI Data:', data);
        },

        _render_recent_invoices: function (invoices) {
            var html = '<table class="table table-sm">';
            html += '<thead><tr><th>Invoice</th><th>Date</th><th>Buyer</th><th>Amount</th><th>Status</th></tr></thead>';
            html += '<tbody>';
            
            invoices.forEach(function (inv) {
                var status_class = 'badge badge-' + (inv.state === 'draft' ? 'secondary' : 'success');
                html += '<tr>';
                html += '<td><strong>' + inv.bill_no + '</strong></td>';
                html += '<td>' + inv.invoice_date + '</td>';
                html += '<td>' + inv.buyer_id[1] + '</td>';
                html += '<td>' + inv.grand_total.toFixed(2) + '</td>';
                html += '<td><span class="' + status_class + '">' + inv.state + '</span></td>';
                html += '</tr>';
            });
            
            html += '</tbody></table>';
            
            var list_elem = document.getElementById('recent_invoices_list');
            if (list_elem) {
                list_elem.innerHTML = html;
            }
        },
    });

    return DashboardWidget;
});
