============================
Marketplace Mercadolibre MFH
============================

Manage your products publishment on Mercado Libre.

Test account on Mercado Libre Chile
-----------------------------------

::

  {
    'id': 342076175,
    'nickname': 'TESTXA8QJSPL',
    'password': 'qatest9571',
    'site_status': 'active',
    'email': 'test_user_13693896@testuser.com'
  }

  {
    'id': 463934431,
    'nickname':'TESTAXCB0XGY',
    'password':'qatest8375',
    'site_status':"active",
    'email':'test_user_18198212@testuser.com'
  }
  test debit card 3661 366334 0014

Test account on Mercado Libre Venezuela
---------------------------------------

::

  {
    'id': 441662274,
    'nickname': 'TESTOZ2ZPWK0',
    'password': 'qatest2011',
    'site_status': 'active',
    'email': 'test_user_44845049@testuser.com'
  }
  {
    'id': 441919486,
    'nickname': 'TETE1867880',
    'password': 'qatest9048',
    'site_status': 'active',
    'email': 'test_user_29835210@testuser.com'
  }

Prefijos en nombre de tarjeta
-----------------------------
- APRO: Payment approved.
- CONT: Pending payment.
- CALL: Payment declined, call to authorize.
- FUND: Payment declined due to insufficient funds.
- SECU: Payment declined by security code.
- EXPI: Payment declined by expiration date.
- FORM: Payment declined due to error in form.
- OTHE: General decline.

Mercado Libre App
-----------------

- Odoo Connector
- ID: 5748834567548310
- Secret key: OXoQmch1oDyCQl2BEGwfIXuuvtRr4CbQ

Obtener token manualmente
-------------------------

https://developers.mercadolibre.com/es_ar/producto-autenticacion-autorizacion/

Parchear Odoo si se quieren recibir notificaciones
--------------------------------------------------
https://github.com/odoo/odoo/issues/7766
