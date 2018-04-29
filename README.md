# `otto-engine`

An automation engine for Home Assistant.

This is a general purpose automation engine that integrates with Home Assistant, and provides higher fidelity automation rules and flexibility than Home Assistant's built-in automation capability.

Otto-engine communicates with Home Assistant over the [Web Socket API](https://developers.home-assistant.io/docs/en/external_api_websocket.html). 

Rules are created, modified, and viewed over a REST API. There is a complementary project called Otto-UI which is a web-based UI to work with the rules.

Rules are stored a JSON files currently, on the same file system that Otto-engine is running. However the persistence module's API was designed to be persistence neutral, and therefore be modified to use other persistence engines.