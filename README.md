# `otto-engine` ![](https://travis-ci.org/sheaffej/otto-engine.svg?branch=master) [![Coverage Status](https://coveralls.io/repos/github/sheaffej/otto-engine/badge.svg?branch=master)](https://coveralls.io/github/sheaffej/otto-engine?branch=master)

An automation engine for [Home Assistant](https://www.home-assistant.io/).

This is a general purpose automation engine that integrates with [Home Assistant](https://www.home-assistant.io/), and provides higher fidelity automation rules and flexibility than Home Assistant's built-in automation capability.

### Project Background
I implemented [Home Assistant](https://www.home-assistant.io/) as the central component of my home automation (a.k.a. Smart Home) project. Sensors and devices communicate with Home Assistant, which provides an open and extensible way to retrieve sensor/device status, events, and control devices.

However, the automation engine in Home Assistant is (in my opinion) limited and difficult to use. Rules need to be written in YAML and reloading rules requires a restart, so testing and debugging rules is tedious. Also, I found the possible automations limited, which was causing me to create overly complicated rules to work around the limitations.

Fortunately Home Assistant has a very clean and open API, and also support for WebSockets to integrate external processes. There is another project [AppDaemon](https://github.com/home-assistant/appdaemon) which also uses the Home Assistant's WebSocket API with very good results. However AppDaemon's approach is to use Python mini-apps as automations, and I wanted to create automations using declarative rules.

I originally built `otto-engine` for my personal use, and therefore after getting the prototype working, I simply evolved it incrementally to perform the functions I needed in the most minimalistic way. It worked well for me, but as it matured, I decided I should release it on GitHub as a public repository so others may use it, or derive other work from it.

## Current Project Status
I am currently evolving the project to include unit and integration tests and performing some basic refactoring to support the tests.

Once the main unit and integration tests are in place, I will start more significant refactoring to simplify and re-organize the code so it is more consumable as an open source project.

## How it works

`otto-engine` communicates with Home Assistant over the [WebSocket API](https://developers.home-assistant.io/docs/en/external_api_websocket.html). 

`otto-engine` subcribes to *events* (such as sensor or device state change events) by sending a message over the WebSocket to Home Assistant. Then any time there is a state change with a sensor, device, etc, `otto-engine` receives an event message from Home Assistant over the WebSocket. This is an asynchronous messaging protocol.

Home Assistant exposes the things it can be asked to do as *services*. `otto-engine` can then cause Home Assistant to take an action by calling a service via the WebSocket connection. 

So the communication between Home Assistant and `otto-engine` consists of:

* **Events**: Home Assistant's way of telling `otto-engine` that something has changed
* **Services**: `otto-engine`'s way of asking Home Assistant to perform some action

Therefore `otto-engine` simply needs to be a rules engine, that listens for events, and evaluates a set of rules based on those events to determine what actions (if any) need to be performed by Home Assistant.

Rules are described as JSON documents. Each rule has:

* **ID**: A string identifier for the rule
* **Description**: A human-friendly title for the rule
* **Enabled**: True/False, so rules can be disabled without deleting them
* **Group**: A human-friendly title of a group of rules (like Lights, or Alerts)
* **Notes**: A free-text area to store notes about the rule
* **Triggers**: A list of Trigger definitions that will cause this rule to be evaluated
* **Rule Condition**: A boolean expression of Conditions to determine if the rule's actions should be run or not
* **Actions**: A list of Actions, each of which consists of:
	* **Action Condition**: A boolean expression of Conditions to determine if this action should be run or not
	* **Action Sequence**: A list of Action Items that will be run in order, if the action condition evaluates to true

Below is an example rule:

```json
{
	"id": "30194955",
	"description": "Motion (home occupied) turns on Kitchen light",
	"enabled": true,
	"group": "Lights",
	"notes": "Motion when home is not occupied should not turn on the lights",
	"triggers": [{
		"platform": "state",
		"entity_id": "sensor.kitchen_motion_sensor",
		"to": "on"
	}],
	"rule_condition": {
		"condition": "and",
		"conditions": [{
				"condition": "state",
				"entity_id": "input_boolean.home_is_occupied",
				"state": "on"
			},
			{
				"condition": "state",
				"entity_id": "switch.kitchen_lights",
				"state": "off"
			}
		]
	},
	"actions": [{
		"action_condition": {
			"condition": "state",
			"entity_id": "switch.kitchen_lights",
			"state": "off"
		},
		"action_sequence": [{
			"domain": "switch",
			"service": "turn_on",
			"data": {
				"entity_id": "switch.kitchen_lights"
			}
		}]
	}]
}
```

When designing the rule schema, there were a few things I wanted rules to be able to do:

* I wanted to be able to easily enable/disable rules. For example I have rules that I use only when I am on vacation. They are complex rules, and I don't want to have to delete them, and re-create them every time I go on vacation. 
* I wanted to have a condition for the entire rule (i.e. `rule_condition`), but also then have different action paths depending on the current state of the home. So each Action also has an `action_condition`. There is of course some "condition overlap" here, for instance in the example above, both the `rule_condition` and `action_condition` do the same thing. I included both in this rule simply to demonstrate the schema.
* I wanted to be able to create, test, modify, enable/disable, and delete rules without restarting Home Assistant.
* I wanted to have a UI to create, view, and modify the rules

Rules are created, modified, and viewed over a REST API. I have a complementary project called [`otto-ui`](https://github.com/sheaffej/otto-ui) which is a web-based UI to work with the rules. The `otto-ui` project is built with Angular 2 / TypeScript. That project is private because I have some private configuration details still hard-coded into it. But I plan to release that as a public repository also in the future.

Rules are persisted as JSON files currently on the same file system that `otto-engine` is running. However the persistence module's API was designed to be persistence-neutral, and therefore can be extended to use other persistence engines (like MySQL,  MongoDB, or Elasticsearch). 