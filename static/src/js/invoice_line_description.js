/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, useState, useRef, onMounted, onPatched } from "@odoo/owl";

/**
 * Description (name) field widget — hamburger icon that expands to a
 * textarea shown BELOW the Item/Product cell.
 *
 * Layout mechanism (inline, no hardcoded offsets):
 *  - The `name` column carries NO visible width of its own for regular
 *    rows (collapsed to 0 via CSS) so it never shows as an extra empty
 *    column between Item and HS Code. It stays a real <td> only so the
 *    native section_and_note colspan for Section/Note rows keeps working.
 *  - When expanded, the textarea is absolutely positioned so it can be
 *    as wide as the Item column while living in the collapsed cell.
 *  - Crucially, the vertical geometry is MEASURED, not guessed: on mount
 *    and on every re-render we read the row's natural content height and
 *    the textarea's own height, then:
 *       * position the textarea right below the row content (top = rowH)
 *       * grow the row by exactly the textarea height (padding-bottom)
 *    so it can never overlap the next row regardless of theme/zoom.
 *
 * Section/Note rows (display_type set) render the full-width textarea
 * inline via the native colspan and never call the measure/expand logic.
 */
export class InvoiceLineDescriptionField extends Component {
    static template = "invoicing.InvoiceLineDescriptionField";
    static props = {
        ...Component.props,
        record: { type: Object },
        name: { type: String },
        readonly: { type: Boolean, optional: true },
    };

    setup() {
        this.rootRef = useRef("root");
        this.state = useState({
            open: !!this.props.record.data[this.props.name],
        });
        onMounted(() => this.syncLayout());
        onPatched(() => this.syncLayout());
    }

    get isDisplayType() {
        return !!this.props.record.data.display_type;
    }

    get isSection() {
        return this.props.record.data.display_type === "line_section";
    }

    get value() {
        return this.props.record.data[this.props.name] || "";
    }

    get row() {
        return this.rootRef.el && this.rootRef.el.closest("tr");
    }

    /**
     * Measure the row and the open textarea, then set the exact vertical
     * offset + row growth so the textarea sits directly below the row
     * content without overlapping the next row. Runs after every render.
     */
    syncLayout() {
        const row = this.row;
        if (!row) {
            return;
        }
        // rootRef.el IS the .o_invoice_line_description wrapper (t-ref="root").
        const wrap = this.rootRef.el;
        const textarea = this.rootRef.el.querySelector("textarea");

        // Section/Note rows manage their own inline textarea — leave them.
        if (this.isDisplayType) {
            row.classList.remove("o_ld_expanded");
            row.style.removeProperty("--o-ld-pad");
            return;
        }

        // Collapsed (hamburger only) — no expansion.
        if (!this.state.open || !textarea) {
            row.classList.remove("o_ld_expanded");
            row.style.removeProperty("--o-ld-pad");
            if (wrap) {
                wrap.style.removeProperty("top");
            }
            return;
        }

        // Expanded: measure and place. Temporarily neutralise our own
        // padding so we read the row's *content* height, not last frame's.
        row.classList.add("o_ld_expanded");
        row.style.setProperty("--o-ld-pad", "0px");
        const rowContentH = row.getBoundingClientRect().height;
        const areaH = textarea.getBoundingClientRect().height || 30;

        // Place the textarea just under the row content, aligned with the
        // left edge of the Item (product_id) cell, and grow the row by
        // exactly the textarea height (plus a small gap) so nothing
        // downstream overlaps.
        if (wrap) {
            wrap.style.top = `${Math.round(rowContentH)}px`;
            const productCell = row.querySelector('td[name="product_id"]');
            const nameCell = this.rootRef.el.closest('td[name="name"]');
            if (productCell && nameCell) {
                // The wrap is absolutely positioned inside the (zero-width)
                // name cell; offset it left so it starts under the Item cell.
                const dx =
                    productCell.getBoundingClientRect().left -
                    nameCell.getBoundingClientRect().left;
                wrap.style.left = `${Math.round(dx)}px`;
                const w = Math.round(productCell.getBoundingClientRect().width);
                if (w > 0) {
                    wrap.style.width = `${w}px`;
                }
            }
        }
        const pad = Math.round(areaH + 4);
        row.style.setProperty("--o-ld-pad", `${pad}px`);
    }

    toggleOpen() {
        this.state.open = true;
    }

    onBlur(ev) {
        const val = ev.target.value;
        if (val !== this.value) {
            this.props.record.update({ [this.props.name]: val });
        }
        if (!val && !this.isDisplayType) {
            this.state.open = false;
        }
    }
}

export const invoiceLineDescriptionField = {
    component: InvoiceLineDescriptionField,
    supportedTypes: ["text", "char"],
};

registry.category("fields").add("invoice_line_description", invoiceLineDescriptionField);
