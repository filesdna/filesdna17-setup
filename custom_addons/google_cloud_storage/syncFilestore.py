import os
from google.cloud import storage
db_name = "portal1"
path = "/filesdna/.local/share/Odoo/filestore/" + db_name
bucket_name = "demo7-dna"
json_file_path = f"/filesdna/.local/share/Odoo/filestore/{db_name}/5d/5d28d77340cb01b04b178783ea5a4265b87936b4"
client = storage.Client.from_service_account_json(json_file_path)
bucket = client.get_bucket(bucket_name)
for r, d, f in os.walk(path):
    for file in f:
        path = os.path.join(r, file)
        fname = path.split("filestore/")[1]
        blob = bucket.blob(fname)
        blob.upload_from_filename(path)
        print (fname)
print ("---upload finish-----")
