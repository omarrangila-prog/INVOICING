/** @odoo-module **/

import { onMounted, onPatched } from "@odoo/owl";
import { FormController } from "@web/views/form/form_controller";
import { patch } from "@web/core/utils/patch";

// Set first letter of customer name on avatar
function updateCustomerAvatar() {
    const avatar = document.querySelector('.o_cust_avatar');
    if (!avatar) return;
    const nameField = document.querySelector('.o_cust_name .o_field_widget span, .o_cust_name .o_field_widget input');
    if (nameField) {
        const name = nameField.value || nameField.textContent || '';
        const letter = name.trim().charAt(0).toUpperCase() || '?';
        avatar.setAttribute('data-letter', letter);
    }
}

// Auto-grow textareas inside cards
function autoGrowTextareas() {
    document.querySelectorAll('.o_cust_card textarea').forEach(function(ta) {
        ta.style.height = 'auto';
        ta.style.height = ta.scrollHeight + 'px';
        ta.addEventListener('input', function() {
            this.style.height = 'auto';
            this.style.height = this.scrollHeight + 'px';
        });
    });
}

patch(FormController.prototype, {
    setup() {
        super.setup();
        onMounted(() => {
            setTimeout(() => {
                updateCustomerAvatar();
                autoGrowTextareas();
            }, 300);
        });
        onPatched(() => {
            setTimeout(() => {
                updateCustomerAvatar();
                autoGrowTextareas();
            }, 100);
        });
    }
});