import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

import consts
from gcp.base_handler import BaseHandler
from port.entities import create_entities_json, handle_entities
from google.cloud import pubsub_v1

logger = logging.getLogger(__name__)

class PubSubHandler(BaseHandler):
    def __init__(self, resource_config, port_client):
        super().__init__(resource_config, port_client)
        self.pubSub_client = pubsub_v1.PublisherClient()
        self.project_path = f"projects/{consts.GCP_PROJECT_NAME}"

    def handle(self):
        logger.info(f"List Pub/Sub topics")
        try:
            topic_list = self.pubSub_client.list_topics(request={"project": self.project_path})

            self._handle_list_response(topic_list)

            #if self.lambda_context.get_remaining_time_in_millis() < consts.REMAINING_TIME_TO_REINVOKE_THRESHOLD:
            #    # Lambda timeout is too close, should return checkpoint for next run
            #    return self._handle_close_to_timeout(region)

            #self._cleanup_regions(region)
        except Exception as e:
            logger.error(f"Failed to list Storage buckets; error {e}")

        return {'gcp_entities': self.gcp_entities, 'next_resource_config': None, 'skip_delete': self.skip_delete}

    def _handle_list_response(self, topic_list):
        with ThreadPoolExecutor(max_workers=consts.MAX_UPSERT_WORKERS) as executor:
            futures = [executor.submit(self.handle_single_resource_item, topic, 'upsert') for topic in topic_list]

            for completed_future in as_completed(futures):
                result = completed_future.result()
                self.gcp_entities.update(result.get('gcp_entities', set()))
                self.skip_delete = result.get('skip_delete', False) if not self.skip_delete else self.skip_delete

    def handle_single_resource_item(self, topic, action_type='upsert'):
        entities = []
        skip_delete = False
        topic_name = topic.name

        try:
            topic_obj ={}
            if action_type == 'upsert':
                logger.info(f"Describe topic: {topic_name}")


                # Handles unserializable date properties in the JSON by turning them into a string
                topic_obj = json.loads(json.dumps(self._topic_obj_to_json_obj(topic), default=str))

            elif action_type == 'delete':
                topic_obj = {"identifier": topic.name}  # Entity identifier to delete

            entities = create_entities_json(topic_obj, self.selector_query, self.mappings, action_type)

        except Exception as e:
            logger.error(f"Failed to extract bucket: {topic_name}, error: {e}")
            skip_delete = True

        gcp_entities = handle_entities(entities, self.port_client, action_type)

        return {'gcp_entities': gcp_entities, 'skip_delete': skip_delete}

    def _topic_obj_to_json_obj(self, topic):
        """
        Patch funtion to decode the topic object
        :param topic: google cloud topic object
        :return: decodable JSON object
        """
        return {"name": topic.name,
                "schema_settings": str(topic.schema_settings),
                "message_retention_duration": str(topic.message_retention_duration),
                "message_storage_policy": str(topic.message_storage_policy)
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