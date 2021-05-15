# -*- coding: utf-8 -*-
{
    'name': "基金基础功能",
    'summary': """""",
    'author': "Debasish Dash",
    'website': "http://www.debweb.com",
    'category': 'CRM',
    'version': '12.0.1',
    'depends': ['base', 'fund_wizard'],
    'data': [
        'security/ir.model.access.csv',
        'views/security.xml',
        'views/menus.xml',
        'views/fund_base_wizard.xml',
        'views/no_risk_data.xml',
        'views/market_situation.xml',
        'views/fund_base_data.xml',
        'views/indicators_config.xml',
        'views/transaction_date_config.xml',
        'views/market_config.xml',

    ],
    # 'license': 'LGPL-3',
    'installable':True,
    'application': True,
    'auto_install':False,
}
