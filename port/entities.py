import logging

import jq

logger = logging.getLogger(__name__)


def handle_entities(entities, port_client, action_type="upsert"):
    gcp_entities = set()
    for entity in entities:
        blueprint_id = entity.get("blueprint")
        entity_id = entity.get("identifier")

        gcp_entities.add(f"{blueprint_id};{entity_id}")

        try:
            if action_type == "upsert":
                port_client.upsert_entity(entity)
            elif action_type == "delete":
                port_client.delete_entity(entity)
        except Exception as e:
            logger.error(
                f"Failed to handle entity: {entity_id} of blueprint: {blueprint_id}, action: {action_type}; {e}"
            )

    return gcp_entities


def create_entities_json(resource_object, selector_jq_query, jq_mappings, action_type="upsert"):
    def run_jq_query(jq_query):
        return jq.first(jq_query, resource_object)

    def raise_missing_exception(missing_field, mapping):
        raise Exception(
            f"Missing required field value for entity, field: {missing_field}, mapping: {mapping.get(missing_field)}"
        )

    def dedup_list(lst):
        return [dict(tup) for tup in {tuple(obj.items()) for obj in lst}]

    if action_type == "delete":
        return dedup_list(
            [
                {
                    "identifier": resource_object["identifier"],
                    "blueprint": mapping.get("blueprint", "").strip('"')
                                 or raise_missing_exception("blueprint", mapping),
                }
                for mapping in jq_mappings
            ]
        )

    if selector_jq_query and not run_jq_query(selector_jq_query):
        return []

    return [
        {
            k: v
            for k, v in {
            "identifier": run_jq_query(mapping.get("identifier", "null"))
                          or raise_missing_exception("identifier", mapping),
            "title": run_jq_query(mapping.get("title", "null"))
            if mapping.get("title")
            else None,
            "blueprint": mapping.get("blueprint", "").strip('"')
                         or raise_missing_exception("blueprint", mapping),
            "icon": run_jq_query(mapping.get("icon", "null"))
            if mapping.get("icon")
            else None,
            "team": run_jq_query(mapping.get("team", "null"))
            if mapping.get("team")
            else None,
            "properties": {
                prop_key: run_jq_query(prop_val)
                for prop_key, prop_val in mapping.get("properties", {}).items()
            },
            "relations": {
                             rel_key: run_jq_query(rel_val)
                             for rel_key, rel_val in mapping.get("relations", {}).items()
                         }
                         or None,
        }.items()
            if v is not None
        }
        for mapping in jq_mappings
    ]