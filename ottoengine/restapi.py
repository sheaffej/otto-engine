import flask
import flask_cors
import json

# from ottoengine.model import dataobjects


app = flask.Flask(__name__)
flask_cors.CORS(app)    # Allow all cross-origin requests
engine = None


def run_server():
    app.run(host='0.0.0.0')


@app.route('/test')
def test():
    result = "I was started at: {}".format(
        engine.get_state_threadsafe("engine", "start_time").strftime("%c"))
    return result


@app.route('/shutdown', methods=['GET'])
def shutdown():
    '''Signal the Werkzeug server to shutdown'''
    func = flask.request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    func()
    return ""


@app.route('/states', methods=['GET'])
def states():
    '''Display the engine states'''

    # Get the states
    entity_states = engine.states.get_all_entity_state_copy()

    # Display the states
    return flask.render_template('states.html.j2', entity_states=entity_states)


@app.route('/rest/ping')
def ping():
    return json.dumps({"success": True})


@app.route('/rest/reload', methods=['GET'])
def reload():
    result = engine.reload_rules()
    success = result.get("success")
    if success:
        return json.dumps({"success": success, "message": "Rules reloaded successfully"})
    else:
        return json.dumps({"success": success, "message": result.get("message")})


@app.route('/rest/rules', methods=['GET'])
def rules():
    rules = engine.get_rules()
    resp = json.dumps({
        "data": [rule.serialize() for rule in rules]
    })
    return resp


@app.route('/rest/entities', methods=['GET'])
def entities():
    entities = engine.get_entities()
    resp = json.dumps({
        "data": [
            {
                "entity_id": entity.get("entity_id"),
                "friendly_name": entity.get("friendly_name"),
                "hidden": entity.get("hidden"),
            }
            for entity in entities
        ]
    })
    return resp


@app.route('/rest/services', methods=['GET'])
def services():
    services = engine.get_services()
    resp = json.dumps({
        "data": [service.serialize() for service in services]
    })
    return resp


@app.route('/rest/rule', methods=['PUT'])
@app.route('/rest/rule/<rule_id>', methods=['GET', 'PUT', 'DELETE'])
def rule(rule_id=None):

    if flask.request.method == 'GET':
        """Return the rule with ID <rule_id>"""
        print("GET for rule {}".format(rule_id))
        rule = engine.get_rule(rule_id)
        # print(rule)
        if rule is None:
            resp = json.dumps({
                "success": False,
                "id": rule_id,
                "message:": "Rule was not found"
            })
        else:
            resp = json.dumps({
                "success": True,
                "id": rule_id,
                "data": rule.serialize()
            })
        return resp

    if flask.request.method == 'PUT':
        """Store the rule as ID <rule_id>"""
        print("PUT for rule {}".format(rule_id))
        print(flask.request.data)

        data = flask.request.get_json().get("data")
        print(data)

        result = engine.save_rule(data)

        success = result.get("success")
        if success:
            resp = json.dumps({
                "success": success,
                "id": data.get("id"),
                "message": "Rule saved"
            })
        else:
            resp = json.dumps({
                "success": success,
                "id": rule_id,
                "message": result.get("message"),
                "data": data
            })
        return resp

    if flask.request.method == 'DELETE':
        """Delete rule with ID <rule_id>"""
        print("DELETE for rule {}".format(rule_id))
        success = engine.delete_rule(rule_id)
        return json.dumps({
            "success": success,
            "id": rule_id
        })

    else:
        # POST Error 405 Method Not Allowed
        print("ERROR: {}".format(flask.request.print))

    return resp


@app.route('/rest/clock/check', methods=['PUT'])
def clock_check():
    spec = flask.request.get_json().get('data')
    print(spec)
    result = engine.check_timespec(spec)

    success = result.get("success")
    if success:
        resp = json.dumps({
            "success": success,
            "data": {"next_time": result.get("next_time")}
        })
    else:
        resp = json.dumps({
            "success": success,
            "message": result.get("message"),
            "data": {"spec": spec}
        })
    return resp
