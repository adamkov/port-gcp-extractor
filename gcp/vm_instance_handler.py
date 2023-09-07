import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

import consts
from gcp.base_handler import BaseHandler
from port.entities import create_entities_json, handle_entities
from google.cloud import compute_v1

logger = logging.getLogger(__name__)


class VMInstanceHandler(BaseHandler):
    def __init__(self, resource_config, port_client):
        super().__init__(resource_config, port_client)
        self.vm_client = compute_v1.InstancesClient()

    def handle(self):

        for region in list(self.regions):
            vm_client = compute_v1.InstancesClient()
            logger.info(f"List gcp vm Instance, region: {region}")
            try:
                instances = vm_client.list(project=consts.GCP_PROJECT_NAME, zone=region)
            except Exception as e:
                logger.error(f"Failed to list gcp vm Instance in region: {region}; error {e}")
                break
            self._handle_list_response(instances)

        return {'gcp_entities': self.gcp_entities, 'next_resource_config': None, 'skip_delete': self.skip_delete}

    def _handle_list_response(self, instances):
        with ThreadPoolExecutor(max_workers=consts.MAX_UPSERT_WORKERS) as executor:
            futures = [executor.submit(self.handle_single_resource_item, instance, 'upsert') for instance in instances]

            for completed_future in as_completed(futures):
                result = completed_future.result()
                self.gcp_entities.update(result.get('gcp_entities', set()))
                self.skip_delete = result.get('skip_delete', False) if not self.skip_delete else self.skip_delete

    def handle_single_resource_item(self, instance, action_type='upsert'):
        entities = []
        skip_delete = False
        topic_name = instance.name

        try:
            topic_obj ={}
            if action_type == 'upsert':
                logger.info(f"Describe topic: {topic_name}")


                # Handles unserializable date properties in the JSON by turning them into a string
                topic_obj = json.loads(json.dumps(self._instance_obj_to_json_obj(instance), default=str))

            elif action_type == 'delete':
                topic_obj = {"identifier": instance.name}  # Entity identifier to delete

            entities = create_entities_json(topic_obj, self.selector_query, self.mappings, action_type)

        except Exception as e:
            logger.error(f"Failed to extract bucket: {topic_name}, error: {e}")
            skip_delete = True

        gcp_entities = handle_entities(entities, self.port_client, action_type)

        return {'gcp_entities': gcp_entities, 'skip_delete': skip_delete}

    def _instance_obj_to_json_obj(self, instance):
        """
        Patch funtion to decode the instance object
        :param topic: google cloud instance object
        :return: decodable JSON object
        """
        return {"name": instance.name,
                "self_link": instance.self_link,
                "zone": instance.zone,
                "status": instance.status,
                "machine_type": instance.machine_type
                }


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