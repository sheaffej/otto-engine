# `otto-engine`

An automation engine for [Home Assistant](https://www.home-assistant.io/).

This is a general purpose automation engine that integrates with [Home Assistant](https://www.home-assistant.io/), and provides higher fidelity automation rules and flexibility than Home Assistant's built-in automation capability.

### Project Background
I implemented [Home Assistant](https://www.home-assistant.io/) as the central component of my home automation (a.k.a. Smart Home) project. Sensors and devices communicate with Home Assistant, which provides an open and extensible way to retrieve sensor/device status, events, and control devices.

However, the automation engine in Home Assistant is (in my opinion) limited and difficult to use. Rules need to be written in YAML and reloading rules requires a restart, so testing and debugging rules is tedious. Also, I found the possible automations limited, which was causing me to create overly complicated rules to work around the limitations.

Fortunately Home Assistant has a very clean and open API, and also support for WWebSockets to integrate external processes. There is another project [AppDaemon](https://github.com/home-assistant/appdaemon) which also uses the Home Assistant WebSocket API with very good results. However AppDaemon's approach is to use Python mini-apps as automations, and I wanted to create automations using declarative rules.

I originally built `otto-engine` for my personal use, and therefore after getting the prototype working, I just evolved it to perform the functions I needed. It worked well for me, but then I decided to release it on GitHub as a public repository. 

##Current Project Status
I am currently evolving the project to include unit and integration tests and performing some basic refactoring to support the tests.

Once the main unit and integration tests are in place, I will start more significant refactoring to simplify and re-organize the code so it aligns with typical open source project conventions.

## How it works

`otto-engine` communicates with Home Assistant over the [Web Socket API](https://developers.home-assistant.io/docs/en/external_api_websocket.html). 

Rules are created, modified, and viewed over a REST API. There is a complementary project called `otto-ui` which is a web-based UI to work with the rules.

Rules are stored a JSON files currently, on the same file system that `otto-engine` is running. However the persistence module's API was designed to be persistence neutral, and therefore be modified to use other persistence engines.