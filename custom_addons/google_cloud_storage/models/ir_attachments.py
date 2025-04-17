# -*- coding: utf-8 -*-
import base64
from odoo import api, models, fields, _
import os
from google.cloud import storage
import time
from odoo.exceptions import UserError, ValidationError
from odoo.tools import config
import logging

google_bucket = config['google_bucket']
_logger = logging.getLogger(__name__)

cloud_bucket_instance = False

class GoogleCloudAttachment(models.Model):

    _inherit = "ir.attachment"

    # For passing mimetype to _file_write
    def _get_datas_related_values(self, data, mimetype):
        self = self.with_context(content_type = mimetype)
        return super()._get_datas_related_values(data,mimetype)
        
    # for creating a instance of Google Cloud Storage Bucket
    def get_bucket(self):
        global cloud_bucket_instance
        try:
            json_file =  f"/opt/filesdna17/custom_addons/google_cloud_storage/google_creds.json"
            bucket = google_bucket
            _logger.info("Google Bucket name %s...........",bucket)
            _logger.info("File service account Path  ... %s",json_file)
            if json_file:
                client = storage.Client.from_service_account_json(json_file)
            if bucket:
                cloud_bucket = client.get_bucket(bucket)
                cloud_bucket_instance = cloud_bucket
        except Exception as e:
            raise UserError("Error: problem in google Bucket connection ..")
        return True


    # for creating a path for the _file_write
    def _set_cloud_blob_name(self, checksum):
        current_time_seconds = time.time()
        current_time_milliseconds = int(current_time_seconds)
        dbname = self._cr.dbname
        fname = checksum[:2] + '/' + checksum + '-' + str(current_time_milliseconds)[:9]
        company_name = self.env.user.company_id.name
        _logger.info("Write File Path to google baucket  ... /%s/%s",dbname,fname)
        return fname, '/'.join([dbname,fname])


    # for creating a path for the _file_read
    @api.model
    def _get_cloud_blob_name(self,fname):
        dbname = self._cr.dbname
        blob_name = fname
        company_name = self.env.user.company_id.name
        return '/'.join([dbname, blob_name])


    # for reading from the cloud
    @api.model
    def _file_read(self, fname):
        asset_list = ['text/css','text/scss','application/javascript','image/svg+xml']
        content_type = self.mimetype
        if content_type not in asset_list:
            if not cloud_bucket_instance:
                self.get_bucket()
            if cloud_bucket_instance:
                try: 
                    blob_name = self._get_cloud_blob_name(fname)
                    blob = cloud_bucket_instance.blob(blob_name)
                    print(blob_name,'read file')
                    read = blob.download_as_string()
                    return read
                except:
                    print('not Found')
        return super(GoogleCloudAttachment, self)._file_read(fname)
    
   
    # for writing into the cloud
    @api.model
    def _file_write(self, value, checksum):
        asset_list = ['text/css','text/scss','application/javascript','image/svg+xml']
        content_type = self.env.context.get('content_type')
        website_id = self.env.context.get('website_id')
        if not cloud_bucket_instance :
            self.get_bucket()
        if cloud_bucket_instance and content_type not in asset_list and not website_id:
            fname, blob_name = self._set_cloud_blob_name(checksum)
            temp_folder_path = f'/opt/filesdna17/custom_addons/temp-folder/{fname[:2]}'
            os.makedirs(temp_folder_path, exist_ok=True)
            file_path = os.path.join(temp_folder_path, checksum)
            with open(file_path, 'wb') as fp:
                fp.write(value)
            blob = cloud_bucket_instance.blob(blob_name)
            content_type = self._context.get("content_type", "text/plain")
            blob.upload_from_string(value,content_type = content_type)
        else:
            fname = super(GoogleCloudAttachment, self)._file_write(value, checksum)

        return fname


    # for deleting from the cloud
    def _mark_for_gc(self, fname):
        if not cloud_bucket_instance:
            self.get_bucket()
        if cloud_bucket_instance:
            try:
                blob_name = self._get_cloud_blob_name('checklist/%s' % fname)
                blob_name_source = self._get_cloud_blob_name(fname)
                blob = cloud_bucket_instance.blob(blob_name)
                blob_source = cloud_bucket_instance.blob(blob_name_source)
                print(blob_name,'Delete Function')
                value = base64.b64decode('')
                blob.upload_from_string(value)
                blob.delete()
                blob_source.delete()
                _logger.debug('Google Cloud Storage: _mark_for_gc key:%s marked for GC', blob_name)
            except Exception as e:
                _logger.error('Google Cloud Storage: File mark as GC, Storage %r,Exception %r', storage,e)
        else:
            super(GoogleCloudAttachment, self)._mark_for_gc(fname)


    @api.autovacuum
    def _gc_file_store(self):
        """ Perform the garbage collection of the filestore. """
        if not cloud_bucket_instance:
            self.get_bucket()
        if cloud_bucket_instance:
            cr = self._cr
            cr.commit()
            cr.execute("LOCK ir_attachment IN SHARE MODE")
            checklist = {}
            whitelist = set()
            removed = 0
            try:
                if not cloud_bucket_instance:
                    self.get_bucket()
                for gc_blob_name in cloud_bucket_instance.list_blobs(Prefix=self._get_cloud_blob_name('checklist')):
                    key = self._get_cloud_blob_name(gc_blob_name[1 + len(self._get_cloud_blob_name('checklist/')):])
                    checklist[key] = gc_blob_name

                for names in cr.split_for_in_conditions(checklist):
                    cr.execute("SELECT store_fname FROM ir_attachment WHERE store_fname IN %s", [names])
                    whitelist.update(row[0] for row in cr.fetchall())

                for key, value in checklist.iteritems():
                    if key not in whitelist:
                        #remove checklist blob
                        print(key,value,'Remove Checklist Blob')
                        cloud_bucket_instance.delete_blob(key)
                        #remove original blob
                        cloud_bucket_instance.delete_blob(value)
                        removed += 1
                        _logger.info('Google Cloud Storage: _file_gc_ deleted key:%s successfully', key)
            except Exception as e:
                _logger.error('Google Cloud Storage: _file_gc_ method delete : EXCEPTION %r'% (e))
            cr.commit()
            _logger.debug("Google Cloud Storage: filestore gc %d checked, %d removed", len(checklist), removed)
        else:
            super(GoogleCloudAttachment, self)._gc_file_store()
