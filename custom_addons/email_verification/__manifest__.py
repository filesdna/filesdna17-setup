# -*- coding: utf-8 -*-
#################################################################################
# Author      : Webkul Software Pvt. Ltd. (<https://webkul.com/>)
# Copyright(c): 2015-Present Webkul Software Pvt. Ltd.
# All Rights Reserved.
#
#
#
# This program is copyright property of the author mentioned above.
# You can`t redistribute it and/or modify it.
#
#
# You should have received a copy of the License along with this program.
# If not, see <https://store.webkul.com/license.html/>
#################################################################################
{
  "name"                 :  "Email Verification",
  "summary"              :  """This module allows to send token based email for verification of accounts and restricts checkout for non verified accounts.""",
  "category"             :  "Website",
  "version"              :  "1.0.1",
  "sequence"             :  10,
  "author"               :  "Webkul Software Pvt. Ltd.",
  "license"              :  "Other proprietary",
  "website"              :  "https://store.webkul.com",
  "description"          :  """https://store.webkul.com""",
  "live_test_url"        :  "http://odoodemo.webkul.com/?module=email_verification",
  "depends"              :  [
                             'mail',
                             'website_sale',
                             'website_webkul_addons',
                            ],
  "data"                 :  [
                             'data/email_template.xml',
                             'views/templates_view.xml',
                             'views/res_config_view.xml',
                             'views/res_users_view.xml',
                             'views/webkul_addons_config_inherit_view.xml',
                             'wizard/wizard_view.xml',
                             'security/ir.model.access.csv'
                            ],
  'assets'               :  {
                                'web.assets_frontend': [
                                    'email_verification/static/src/js/email_verification.js',
                                    # 'email_verification/static/src/js/template_view.js'
                                 ],
                            },
  "images"               :  ['static/description/banner.png'],
  "application"          :  True,
  "installable"          :  True,
  "auto_install"         :  False,
  "price"                :  29,
  "currency"             :  "USD",
  "pre_init_hook"        :  "pre_init_check",
}