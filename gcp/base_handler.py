import copy
import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

import boto3

import consts
from port.entities import create_entities_json

logger = logging.getLogger(__name__)


class BaseHandler:
    def __init__(self, resource_config, port_client):
        self.resource_config = copy.deepcopy(resource_config)
        self.port_client = port_client
        self.kind = self.resource_config.get("kind", "")
        selector = self.resource_config.get("selector", {})
        self.selector_query = selector.get("query")
        self.selector_gcp = selector.get("gcp", {})
        self.regions_config = self.selector_gcp.get("regions_config", {})
        self.next_token = self.selector_gcp.get("next_token", "") #Todo: understand what is the token
        self.mappings = (self.resource_config.get("port", {}).get("entity", {}).get("mappings", []))
        self.gcp_entities = set()
        self.skip_delete = False
        self.project_name = consts.GCP_PROJECT_NAME

    def handle(self):
        raise NotImplementedError("Subclasses should implement 'handle' function")

    def handle_single_resource_item(self, resource_id, action_type='upsert'):
        raise NotImplementedError("Subclasses should implement 'handle_single_resource_item' function")

    def _cleanup_regions(self, region):
        self.regions.remove(region)
        self.regions_config.pop(region, None)
        self.selector_gcp["regions"] = self.regions
        self.selector_gcp["regions_config"] = self.regions_config