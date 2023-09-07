import requests
import json
from port.client import PortClient

project_name = 'port-gcp-exporter-project'
auth_token = 'Bearer ya29.a0AfB_byCtx4UN8jJxkeDfo99AM_KXPBap7ju3A5OMHB16KKHBikZhEpP0ogPs-Ok3LDQl9TiNHUw2jL6_mr21Oxh2jVq38yfkIOIYSXCjzw2Bz3OuHRWQX6DhlKSpN7L9Lb55HbLBbkCokvmkfXSGxqcSoHWrxa5a3KH9dcbRaCgYKAfgSARESFQHsvYlsdML-kUj-Yz05OLmEyn9H6w0175'
storage_base_api = 'https://storage.googleapis.com/storage/v1'

# Todo: this should be a class and storage_base_api should be a global var inside the class
# Todo: functions should receive an http client and not authorization each one
# Todo: need to have pagination for requests
# Todo: Error handling and exception try catch
# Todo: In bucket blueprint switch location to enum instead of string
# Todo:
def get_buckets(project_name,auth_token, buckets_api_suffix='/b'):
    buckets_api = storage_base_api + buckets_api_suffix
    headers = {'Authorization': auth_token}
    payload = {'project': project_name}
    r = requests.get(buckets_api, params=payload, headers=headers)
    buckets = r.json()['items']
    return buckets

def get_bucket_objects(bucket_name, auth_token):
    objects_api = storage_base_api + f'/b/{bucket_name}/o'
    headers = {'Authorization': auth_token}
    r = requests.get(objects_api, headers=headers)
    objects = r.json()['items']
    return objects




project_buckets = get_buckets(project_name=project_name, auth_token=auth_token)
#bucket_names = list(map(lambda bucket: bucket['name'], project_buckets))
#
#for bucket in bucket_names:
#    bucket_objects = get_bucket_objects(bucket, auth_token)
#    print('bucket: ' + bucket)
#    print('objects: ')
#    print(bucket_objects)

client = PortClient(client_id="Z8N8IJNnR8uJM2fSBmDEar6WNaTUripj",
                    client_secret="o9q0CFsW3HEjZVxxVv6FSLLojVCVWehx1lty9SaBQPl0XiX3Irl7r3BaprjTqM01",
                    user_agent="",
                    api_url="https://api.getport.io/v1")

blueprint_id = 'gcp-bucket'

import random
import string

letters = string.ascii_lowercase
for bucket in project_buckets:
    unique_id = ''.join(random.choice(letters) for i in range(10))
    entity = {'identifier': unique_id,#bucket['id'],
              'title': bucket['name'],
              'icon': 'GCP',
              'team': [],
              'properties': {'link': bucket['selfLink'],
                             'name': bucket['name'],
                             'id': bucket['id'],
                             'location': bucket['location'],
                             'storageclass': bucket['storageClass'],
                             'timecreated': bucket['timeCreated'],
                             'lastupdatetime': bucket['updated'],
                             'iamconfiguration': bucket['iamConfiguration']},
              'relations': {
                  'hosting_bucket_of_files': [],
                  'hosting_bucket': []
              }}
    client.update_entity(blueprint_id ,entity)

#blueprints = client.get_blueprints()
#print(blueprints.json())