from odoo import models, fields, api
import requests
import logging
import re

_logger = logging.getLogger(__name__)

ELASTICSEARCH_URL = 'https://elastic.filesdna.com:9200'
API_KEY = 'UHJOWmU0c0JjM09ieEtGdDlVX2k6RGFQWko1NGtUemlmZmNKMFdBYkl3Zw=='

class SearchWizard(models.TransientModel):
    _name = 'elastic_search.wizard'
    _description = 'Elastic Search Wizard'

    elastic_search = fields.Char(string="Elastic Search")
    operator = fields.Selection([('AND', 'AND'), ('OR', 'OR')], string="Operator", default="AND")
    date_from = fields.Date(string="Date From")
    date_to = fields.Date(string="Date To")

    def normalize_string(self, s):
        """
        Convert the input string to lowercase and replace spaces or special characters with underscores.
        """
        s = s.lower()
        s = re.sub(r'[^\w\s]', '_', s)  # Replace special characters with underscores
        s = re.sub(r'\s+', '_', s)      # Replace one or more spaces with a single underscore
        return s

    @api.model
    def _search_elastic(self, value, operator):
        """
        Search Elasticsearch with the given value and operator.
        """
        query = {
            "query": {
                "query_string": {
                    "query": value,
                    "default_operator": operator  # Dynamically use selected operator (AND/OR)
                }
            }
        }

        # Elasticsearch URL and headers
        url = f"{ELASTICSEARCH_URL}/{self.normalize_string(self.env.user.company_id.name)}/_search"
        headers = {
            "Content-Type": "application/json",
            'Authorization': f'ApiKey {API_KEY}'
        }

        # Elasticsearch request
        response = requests.post(url, headers=headers, json=query)
        _logger.debug("Elasticsearch query URL: %s", url)
        _logger.debug("Elasticsearch query payload: %s", query)
        _logger.debug("Elasticsearch response status: %s", response.status_code)

        document_ids = []
        if response.status_code == 200:
            results = response.json()
            document_ids = [int(hit['_id']) for hit in results['hits']['hits'] if hit['_id'].isdigit()]
        else:
            _logger.error("Elasticsearch query failed with status code: %s", response.status_code)

        return document_ids

    def action_search(self):
        """ Perform the search, then filter results by date in Odoo """
        self.ensure_one()

        # Step 1: Search in Elasticsearch
        document_ids = self._search_elastic(self.elastic_search, self.operator)

        # Step 2: Filter the results in Odoo by the date range (date_from and date_to)
        domain = [('id', 'in', document_ids)]

        if self.date_from:
            domain.append(('create_date', '>=', self.date_from))
        if self.date_to:
            domain.append(('create_date', '<=', self.date_to))

        # Step 3: Return the filtered results to be displayed in Odoo
        return {
            'type': 'ir.actions.act_window',
            'name': 'Search Results',
            'res_model': 'dms.file',
            'view_mode': 'kanban,tree,form',
            'domain': domain,
            'context': dict(self.env.context),
        }
