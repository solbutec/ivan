===============
Marketplace MFH
===============

Base module for developing external marketplaces.

Handling multiple databases
---------------------------

In case your server handles multiple databases, you must add marketplace module
to the list of ``server_wide_modules``. Open your odoo config file and append
at the end of the line the module ``marketplace``

::

  server_wide_modules = web,web_kanban,marketplace
