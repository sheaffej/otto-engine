import flask
import flask_cors
import json
import logging

MIMETYPE = "application/json"

app = flask.Flask(__name__)
flask_cors.CORS(app)    # Allow all cross-origin requests
_LOG = logging.getLogger(__name__)
# _LOG.setLevel(logging.DEBUG)

engine_obj = None  # global reference to the OttoEngine object


def run_server():
    app.run(host='0.0.0.0')


def dict_to_json_response(data_dict: dict) -> flask.Response:
    return flask.Response(json.dumps(data_dict), mimetype=MIMETYPE)


@app.route('/shutdown', methods=['GET'])
def shutdown():
    '''Signal the Werkzeug server to shutdown'''
    func = flask.request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    func()
    return ""


@app.route('/rest/ping')
def ping():
    return dict_to_json_response({"success": True})


@app.route('/rest/reload', methods=['GET'])
def reload():
    result = engine_obj.reload_rules_threadsafe()
    success = result.get("success")
    if success:
        resp = {"success": success, "message": "Rules reloaded successfully"}
    else:
        resp = {"success": success, "message": result.get("message")}
    return dict_to_json_response(resp)


@app.route('/rest/rules', methods=['GET'])
def rules():
    rules = engine_obj.get_rules_threadsafe()
    resp = {"data": [rule.serialize() for rule in rules]}
    return dict_to_json_response(resp)


@app.route('/rest/entities', methods=['GET'])
def entities():
    entities = engine_obj.get_entities_threadsafe()
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
    services = engine_obj.get_services_threadsafe()
    resp = json.dumps({
        "data": [service.serialize() for service in services]
    })
    return resp


@app.route('/rest/rule', methods=['PUT'])
@app.route('/rest/rule/<rule_id>', methods=['GET', 'PUT', 'DELETE'])
def rule(rule_id=None):

    if flask.request.method == 'GET':
        """Return the rule with ID <rule_id>"""
        _LOG.info("GET for rule {}".format(rule_id))
        rule = engine_obj.get_rule_threadsafe(rule_id)
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
        _LOG.info("PUT for rule {}".format(rule_id))
        _LOG.debug(flask.request.data)

        data = flask.request.get_json().get("data")

        result = engine_obj.save_rule_threadsafe(data)

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
        _LOG.info("DELETE for rule {}".format(rule_id))
        success = engine_obj.delete_rule_threadsafe(rule_id)
        return json.dumps({
            "success": success,
            "id": rule_id
        })

    else:
        # POST Error 405 Method Not Allowed
        _LOG.error("ERROR: {}".format(flask.request.print))

    return resp


@app.route('/rest/clock/check', methods=['PUT'])
def clock_check():
    spec = flask.request.get_json().get('data')
    _LOG.info(spec)
    result = engine_obj.check_timespec_threadsafe(spec)

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


@app.route('/rest/logs', methods=['GET'])
def logs():
    resp = json.dumps({
        "data": [entry for entry in engine_obj.get_logs_threadsafe()]
    })
    return resp
