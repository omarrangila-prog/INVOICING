{
    'name': 'Keleven Digital Invoicing',
    'version': '19.0.1.0.0',
    'category': 'Accounting/Invoicing',
    'sequence': 1,
    'summary': 'Complete ERP Invoicing Module with Customer Accounts, Item Accounts, Digital Invoicing, and Invoice Book',
    'description': 'Digital Invoicing Module for FBR compliance with Customer Accounts, Item Master, Digital Invoicing, Invoice Book, and Dashboard.',
    'author': 'Keleven Global LLC',
    'website': 'https://kelevenglobal.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'web',
        'mail',
        'account',
    ],
    'data': [
        # 1. Security Groups (must be first - other files reference these groups)
        'security/security.xml',

        # 2. Access Rights
        'security/ir.model.access.csv',

        # 3. Sequences and base data (Scenarios,Hscode,UOM)
        'data/sequence.xml',
        'data/uom_data.xml',
        'data/scenario_data.xml',
        'data/item_hs_code.xml',

        # 4. Report actions (menus.xml references these, so must come before menus)
        'reports/report_digital_invoice.xml',
        'reports/report_templates.xml',

        # 5. Window Actions (menus.xml references these too)
        'views/actions.xml',


        # 7. Menus (all actions must exist before this)
        'views/menus.xml',

        # 8. Views (order doesn't matter much here)
        'views/customer_account_views.xml',
        'views/item_account_views.xml',
        'views/digital_invoice_views.xml',
        'views/digital_invoice_book_views.xml',
        'views/res_company_views.xml',
        'views/fbr_log_views.xml',
        'views/dashboard.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'keleven_invoicing/static/src/css/dashboard.css',
            'keleven_invoicing/static/src/css/invoicing.css',
            'keleven_invoicing/static/src/js/invoicing.js',
            'keleven_invoicing/static/src/js/dashboard.js',
            'keleven_invoicing/static/src/js/invoice_line_description.js',
            'keleven_invoicing/static/src/xml/invoice_line_description.xml',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'icon': '/keleven_invoicing/static/description/icon.png',
    'images': ['static/description/icon.png'],
}