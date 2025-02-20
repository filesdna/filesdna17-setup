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
  "name"                 :  "FilesDNA Google Cloud Storage",
  "summary"              :  """Store your FilesDNA attachment to Google Cloud Storage""",
  "category"             :  "Document Managment",
  "version"              :  "1.0.3",
  "author"               :  "Borderless Security",
  "license"              :  "Other proprietary",
  "maintainer"           :  "Borderless Security",
  "website"              :  "https://borderlesssecurity.com",
  "description"          :  """Store your FilesDNA attachment to Google Cloud Storage""",
  "depends"              :  ['base','web'],
  "data"                 :  [
                              # 'views/res_config.xml'
                              ],
  "images"               :  ['static/description/Banner.png'],
  "application"          :  True,
  "installable"          :  True,
  "auto_install"         :  False,
  "price"                :  169,
  "currency"             :  "USD",
  "external_dependencies":  {'python': ['google-cloud-storage']},
}
