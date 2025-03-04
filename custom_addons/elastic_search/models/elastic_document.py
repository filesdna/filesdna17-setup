# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError

from tika import parser
from elasticsearch import Elasticsearch
import re
import requests

ELASTICSEARCH_URL = 'https://elastic.filesdna.com:9200/'
API_KEY = 'UHJOWmU0c0JjM09ieEtGdDlVX2k6RGFQWko1NGtUemlmZmNKMFdBYkl3Zw=='

class ElasticDocument(models.Model):
    _name = 'elastic.document'
    _description = 'Document for Elasticsearch Indexing'

    name = fields.Char('Document Name', required=True)
    file = fields.Binary('File', required=True)
    file_name = fields.Char('File Name')
    user_id = fields.Many2one('res.users', 'User', required=True, default=lambda self: self.env.user)

    def create_elasticsearch_client(self):
        return Elasticsearch(
            hosts=[ELASTICSEARCH_URL],
            headers={'Authorization': f'ApiKey {API_KEY}'}
        )
    
    def normalize_string(self,s):
        """
        Convert the input string to lowercase and replace spaces or special characters with underscores.
        
        Args:
            s (str): The input string to normalize.
            
        Returns:
            str: The normalized string.
        """
        # Convert to lowercase
        s = s.lower()
        
        # Replace spaces and special characters with underscores
        s = re.sub(r'[^\w\s]', '_', s)  # Replace special characters (excluding alphanumeric and spaces) with underscores
        s = re.sub(r'\s+', '_', s)      # Replace one or more spaces with a single underscore
        
        return s
        
    def create_user_index(self, es_client):
        index_name = f'{self.normalize_string(self.env.user.company_id.name)}'
        if not es_client.indices.exists(index=index_name):
            try:
                settings = {
                    "settings": {
                        "analysis": {
                            "analyzer": {
                                "custom_ngram_analyzer": {
                                    "type": "custom",
                                    "tokenizer": "custom_ngram_tokenizer",
                                    "filter": ["lowercase"]
                                }
                            },
                            "tokenizer": {
                                "custom_ngram_tokenizer": {
                                    "type": "ngram",
                                    "min_gram": 3,
                                    "max_gram": 4
                                }
                            }
                        }
                    },
                    "mappings": {
                        "properties": {
                            "content": {
                                "type": "text",
                                "analyzer": "custom_ngram_analyzer"
                            },
                            "file_name": {
                                "type": "keyword"
                            }
                        }
                    }
                }
                es_client.indices.create(index=index_name, body=settings)
            except Exception as e:
                raise UserError(f"Error creating index for user {self.env.user.company_id.name}: {e}")
        else:
            print(f"Index for user {self.env.user.company_id.name}: {index_name} already exists")

    def index_file_to_elasticsearch(self, es_client, document_id, file_name, content):
        index_name = f'{self.normalize_string(self.env.user.company_id.name)}'
        try:
            response = es_client.index(
                index=index_name,
                id=document_id,
                body={'content': content, 'file_name': file_name}
            )
            print(response)
        except Exception as e:
            raise UserError(f"Error indexing {file_name} for user {self.env.user.company_id.name}: {e}")
    