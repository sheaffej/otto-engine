BASEURL="http://localhost:5000"

# rm -f json_rules/12345.json

echo
echo
echo "===== PUT bad rule ===="
curl -H "Content-Type: application/json" -X PUT -d '{"data": {"name": "John", "age": 44}}'  ${BASEURL}/rest/rule

echo
echo
echo "==== GET missing rule 1234 ===="
curl -X GET ${BASEURL}/rest/rule/1234

echo
echo
echo "==== PUT good rule /rest/rule with ID 1234==="
curl -H "Content-Type: application/json" -X PUT -d '{"data": {"id": "12345", "description": "Turn everything on after a 3 second delay if both triggered", "enabled": true, "group": "Test", "triggers": [{"platform": "state", "entity_id": "input_boolean.state_home_occupied", "to": "on", "from": "off"}, {"platform": "state", "entity_id": "input_boolean.state_motion_in_home", "to": "on", "from": "off"}, {"platform": "numeric_state", "entity_id": "input_slider.temp_slider", "above": 80}, {"platform": "event", "event_type": "call_service", "event_data": {"service": "test_service"}}], "rule_condition": {"condition": "and", "conditions": [{"condition": "state", "entity_id": "input_boolean.state_home_occupied", "state": "on"}, {"condition": "state", "entity_id": "input_boolean.state_motion_in_home", "state": "on"}]}, "actions": [{"action_condition": {"condition": "state", "entity_id": "input_boolean.state_home_occupied", "state": "on"}, "action_sequence": [{"domain": "input_boolean", "service": "turn_on", "data": {"entity_id": "input_boolean.action_light"}}, {"domain": "input_boolean", "service": "turn_on", "data": {"entity_id": "input_boolean.action_siren"}}]}, {"action_condition": {"condition": "state", "entity_id": "input_boolean.state_motion_in_home", "state": "on"}, "action_sequence": [{"delay": {"days": 0, "secs": 3, "ms": 0}}, {"domain": "input_boolean", "service": "turn_on", "data": {"entity_id": "input_boolean.action_light2"}}, {"domain": "input_boolean", "service": "turn_on", "data": {"entity_id": "input_boolean.action_siren2"}}]}]}}' ${BASEURL}/rest/rule

echo
echo
echo "==== Re-PUT good rule with wrong ID /rest/rule/4545 ===="
curl -H "Content-Type: application/json" -X PUT -d '{"data": {"id": "12345", "description": "Turn everything on after a 3 second delay if both triggered", "enabled": true, "group": "Test", "triggers": [{"platform": "state", "entity_id": "input_boolean.state_home_occupied", "to": "on", "from": "off"}, {"platform": "state", "entity_id": "input_boolean.state_motion_in_home", "to": "on", "from": "off"}, {"platform": "numeric_state", "entity_id": "input_slider.temp_slider", "above": 80}, {"platform": "event", "event_type": "call_service", "event_data": {"service": "test_service"}}], "rule_condition": {"condition": "and", "conditions": [{"condition": "state", "entity_id": "input_boolean.state_home_occupied", "state": "on"}, {"condition": "state", "entity_id": "input_boolean.state_motion_in_home", "state": "on"}]}, "actions": [{"action_condition": {"condition": "state", "entity_id": "input_boolean.state_home_occupied", "state": "on"}, "action_sequence": [{"domain": "input_boolean", "service": "turn_on", "data": {"entity_id": "input_boolean.action_light"}}, {"domain": "input_boolean", "service": "turn_on", "data": {"entity_id": "input_boolean.action_siren"}}]}, {"action_condition": {"condition": "state", "entity_id": "input_boolean.state_motion_in_home", "state": "on"}, "action_sequence": [{"delay": {"days": 0, "secs": 3, "ms": 0}}, {"domain": "input_boolean", "service": "turn_on", "data": {"entity_id": "input_boolean.action_light2"}}, {"domain": "input_boolean", "service": "turn_on", "data": {"entity_id": "input_boolean.action_siren2"}}]}]}}' ${BASEURL}/rest/rule/4545

echo
echo
echo "==== GET good rule 12345 ===="
curl -X GET ${BASEURL}/rest/rule/12345

echo
echo
echo "==== DELETE existing rule 12345 ===="
curl -X DELETE ${BASEURL}/rest/rule/12345

echo
echo
echo
echo "==== DELETE missing rule 4545 ===="
curl -X DELETE ${BASEURL}/rest/rule/4545

echo
echo
