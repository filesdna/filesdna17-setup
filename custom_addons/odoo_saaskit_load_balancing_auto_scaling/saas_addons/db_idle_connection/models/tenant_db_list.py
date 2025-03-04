from odoo import models, fields, api, _
from odoo.tools import config
import logging
import psycopg2

_logger = logging.getLogger(__name__)


class tenant_database_list(models.Model):
    _inherit = "tenant.database.list"
    _description = 'Tenant Database List'

    # def closing_pg_connections(self):
    #     for db_name in self.env['tenant.database.list'].search([]):
    #         con = psycopg2.connect (database = config['db_name'] or 'saasmaster_v16', user = config['db_user'] or 'root', password  = config['db_password'] or 'toor', host = config['db_host'] or 'localhost', port = config['db_port'] or 5432)
    #         cur = con.cursor()
    #
    #         _logger.info("working in closing pg connection ................{}".format(db_name.name))
    #
    #         close_query = "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '{}' AND pid <> pg_backend_pid() AND state in ('idle');".format(db_name.name)
    #         _logger.info("close_query >>>>>>>>>\n {}".format(close_query))
    #         cur.execute(close_query)
    #
    #         con.close()

    def closing_pg_connections(self):
        for db_name in self.env['tenant.database.list'].search([]):
            con = psycopg2.connect(database=config['db_name'] or 'saasmaster_v17',
                                   user=  config['db_user'] or 'root',
                                   password= config['db_password'] or 'toor',
                                   host=config['db_host'] or 'localhost',
                                   port=config['db_port'] or 5432)
            cur = con.cursor()

            query = """
                  SELECT pid, NOW() - pg_stat_activity.query_start AS idle_time
                  FROM pg_stat_activity
                  WHERE pg_stat_activity.datname = %s
                  AND state = 'idle'
                  AND query_start < NOW() - INTERVAL '30 minutes';
              """
            cur.execute(query, (db_name.name,))
            results = cur.fetchall()

            for pid, idle_time in results:
                cur.execute("SELECT pg_terminate_backend(%s)", (pid,))
            con.close()
