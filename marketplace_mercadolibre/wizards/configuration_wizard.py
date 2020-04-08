from odoo import fields, models
from ..mercadolibre import Meli


class ConfigurationCategories(models.TransientModel):
    _name = 'marketplace.meli.configuration.categories'
    _description = 'Parent categories for MercadoLibre configuration'

    name = fields.Char()
    code = fields.Char()
    parent_id = fields.Many2one('marketplace.meli.configuration.categories')
    child_ids = fields.One2many('marketplace.meli.configuration.categories', 'parent_id')


class ConfigurationWizard(models.TransientModel):
    _name = 'marketplace.meli.configuration.wizard'
    _description = 'MercadoLibre configuration wizard'

    def _default_delete(self):
        self.category_ids.search([]).unlink()
        return False

    site_id = fields.Many2one('marketplace.site')
    country = fields.Selection([
        ('MLA', 'Argentina'),
        ('MLB', 'Brasil'),
        ('MLC', 'Chile'),
        ('MCO', 'Colombia'),
        ('MCR', 'Costa Rica'),
        ('MEC', 'Ecuador'),
        ('MLM', 'México'),
        ('MPA', 'Panamá'),
        ('MPE', 'Perú'),
        ('MPT', 'Portugal'),
        ('MRD', 'República Dominicana'),
        ('MLU', 'Uruguay'),
        ('MLV', 'Venezuela')
    ], required=True)
    category_ids = fields.Many2many('marketplace.meli.configuration.categories',
                                    'marketplace_meli_config_categories',
                                    'config_id', 'category_id', string='Categories',
                                    default=_default_delete)

    def get_data(self):
        client = Meli(self.site_id.meli_app_id, self.site_id.meli_secret_key)
        res = client.get('/sites/%s/listing_types' % self.country)
        listing_ids = self.env['marketplace.meli.listing.type'].search([])
        # Disabling for now all listing types
        listing_ids.write({'active': False})
        listings_dict = {listing.code: listing for listing in listing_ids}
        for listing in res.json():
            if listing['id'] in listings_dict:
                # enabling existing listings found
                listings_dict[listing['id']].active = True
            else:
                # creating new ones
                listing_ids.create({'name': listing['name'], 'code': listing['id']})
        # setting currency
        res = client.get('/sites/%s' % self.country)
        self.site_id.write({
            'meli_currency_id': res.json().get('default_currency_id')
        })

        category_ids = self.env['marketplace.meli.category'].search([])
        categories_dict = {category.code: category for category in category_ids}
        for category_id in self.category_ids:
            if category_id.code in categories_dict:
                categories_dict[category_id.code].write({
                    'active': True,
                    'name': category_id.name,
                    'parent_id': category_id.parent_id and categories_dict[category_id.parent_id.code].id
                })
            else:
                categories_dict[category_id.code] = category_ids.create({
                    'name': category_id.name,
                    'code': category_id.code,
                    'parent_id': category_id.parent_id and categories_dict[category_id.parent_id.code].id
                })
            get_child_categories(client, categories_dict[category_id.code], categories_dict)
        self.category_ids.search([]).unlink()
        return True

    def get_parent_categories(self):
        category_ids = self.env['marketplace.meli.category'].search([])
        categories_dict = {cat.code: cat for cat in category_ids}
        client = Meli(self.site_id.meli_app_id, self.site_id.meli_secret_key)
        parent_categories = self.category_ids
        if not parent_categories:
            res = client.get('/sites/%s/categories' % self.country)
            # Disabling for now all categories
            category_ids.write({'active': False})
            for category in res.json():
                self.category_ids.create({
                    'code': category['id'],
                    'name': category['name']
                })
        for parent in parent_categories:
            if parent.code in categories_dict:
                categories_dict[parent.code].write({
                    'active': True,
                    'name': parent.name,
                    'parent_id': parent.parent_id and categories_dict[parent.parent_id.code].id
                })
            else:
                categories_dict[parent.code] = category_ids.create({
                    'name': parent.name,
                    'code': parent.code,
                    'parent_id': parent.parent_id and categories_dict[parent.parent_id.code].id
                })
            res = client.get('/categories/%s' % parent.code)
            self.category_ids = [(0, 0, {
                'name': category['name'],
                'code': category['id'],
                'parent_id': parent.id
            }) for category in res.json().get('children_categories', [])]
        self.category_ids = [(3, p.id) for p in parent_categories]
        return {
            'type': 'ir.actions.act_window',
            'name': 'Configuración',
            'res_model': 'marketplace.meli.configuration.wizard',
            'view_mode': 'form',
            'view_type': 'form',
            'target': 'new',
            'res_id': self.id
        }


def get_child_categories(client, category_id, categories_dict):
    res = client.get('/categories/%s' % category_id.code)
    for category in res.json().get('children_categories', []):
        if category['id'] in categories_dict:
            # enabling parent category found
            categories_dict[category['id']].write({
                'active': True,
                'parent_id': category_id.id
            })
        else:
            categories_dict.update({
                category['id']: category_id.create({
                    'name': category['name'],
                    'code': category['id'],
                    'parent_id': category_id.id
                })
            })
        get_child_categories(client, categories_dict[category['id']], categories_dict)
