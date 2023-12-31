import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

import consts
from gcp.base_handler import BaseHandler
from port.entities import create_entities_json, handle_entities
from google.cloud import storage
logger = logging.getLogger(__name__)

class StorageHandler(BaseHandler):
    def __init__(self, resource_config, port_client):
        super().__init__(resource_config, port_client)
        #self.storage_base_api = 'https://storage.googleapis.com/storage/v1'
        #self.buckets_api = self.storage_base_api + '/b'
        self.storage_client = storage.Client(project=self.project_name)

    def handle(self):
        logger.info(f"List Storage buckets")
        try:
            buckets = self.storage_client.list_buckets()

            self._handle_list_response(buckets)

            #if self.lambda_context.get_remaining_time_in_millis() < consts.REMAINING_TIME_TO_REINVOKE_THRESHOLD:
            #    # Lambda timeout is too close, should return checkpoint for next run
            #    return self._handle_close_to_timeout(region)

            #self._cleanup_regions(region)
        except Exception as e:
            logger.error(f"Failed to list Storage buckets; error {e}")

        return {'gcp_entities': self.gcp_entities, 'next_resource_config': None, 'skip_delete': self.skip_delete}

    def _handle_list_response(self, buckets_reponse):
        with ThreadPoolExecutor(max_workers=consts.MAX_UPSERT_WORKERS) as executor:
            futures = [executor.submit(self.handle_single_resource_item, bucket, 'upsert') for bucket in buckets_reponse]
#
            for completed_future in as_completed(futures):
                result = completed_future.result()
                self.gcp_entities.update(result.get('gcp_entities', set()))
                self.skip_delete = result.get('skip_delete', False) if not self.skip_delete else self.skip_delete

    def handle_single_resource_item(self, bucket, action_type='upsert'):
        entities = []
        skip_delete = False
        bucket_name = bucket.name

        try:
            bucket_obj ={}
            if action_type == 'upsert':
                logger.info(f"Describe bucket: {bucket_name}")


                # Handles unserializable date properties in the JSON by turning them into a string
                bucket_obj = json.loads(json.dumps(bucket.__dict__, default=str))['_properties']

            elif action_type == 'delete':
                bucket_obj = {"identifier": bucket}  # Entity identifier to delete

            entities = create_entities_json(bucket_obj, self.selector_query, self.mappings, action_type)

        except Exception as e:
            logger.error(f"Failed to extract bucket: {bucket_name}, error: {e}")

        gcp_entities = handle_entities(entities, self.port_client, action_type)

        return {'gcp_entities': gcp_entities, 'skip_delete': skip_delete}

    def _handle_close_to_timeout(self, region):
        return
        #if self.next_token:
        #    self.selector_aws['next_token'] = self.next_token
        #else:
        #    self.selector_aws.pop('next_token', None)
        #    self._cleanup_regions(region)
        #    if not self.regions:  # Nothing left to sync
        #        return {'aws_entities': self.aws_entities, 'next_resource_config': None,
        #                'skip_delete': self.skip_delete}
#
        #if 'selector' not in self.resource_config:
        #    self.resource_config['selector'] = {}
        #self.resource_config['selector']['aws'] = self.selector_aws
#
        #return {'aws_entities': self.aws_entities, 'next_resource_config': self.resource_config,
        #        'skip_delete': self.skip_delete}