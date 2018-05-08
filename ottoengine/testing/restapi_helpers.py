import requests
from unittest import TestCase
# from ottoengine.testing.rule_helpers import AutomationRuleSpec


def put_rule(testcase, rest_url, json_rule):
    """
        :param TestCase testcase: TestCase object
        :param str rest_url: http://host:port
        :param str rulespec: JSON rule
        :rtype: dict
    """
    resp = requests.put(rest_url + "/rest/rule", json={"data": json_rule}).json()
    print("Put rule response: {}".format(resp))
    testcase.assertEqual(resp.get("success"), True)
    testcase.assertEqual(resp.get("id"), json_rule["id"])
    return resp


def get_rule(testcase, rest_url, rule_id):
    resp = requests.get(rest_url + "/rest/rule/{}".format(rule_id)).json()
    print("Get rule response: {}".format(resp))
    testcase.assertEqual(resp.get("success"), True)
    testcase.assertEqual(resp.get("id"), rule_id)
    return resp


def reload_rules(testcase, rest_url):
    """
        :param TestCase self: TestCase object
        :param str rest_url: http://host:port
        :rtype: dict
    """
    resp = requests.get(rest_url + "/rest/reload").json()
    print("Reload rules response: {}".format(resp))
    testcase.assertEqual(resp.get("success"), True)
    return resp


def delete_rule(testcase, rest_url, rule_id):
    resp = requests.delete(rest_url + "/rest/rule/{}".format(rule_id)).json()
    print("Delete rule response: {}".format(resp))
    testcase.assertEqual(resp.get("success"), True)
    testcase.assertEqual(resp.get("id"), rule_id)
    return resp
