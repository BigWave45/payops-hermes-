"""Hermes registration contract smoke tests."""
from pathlib import Path

import yaml

import payops


class FakePluginContext:
    def __init__(self, flutterwave_environment="sandbox"):
        self.tools = []
        self.flutterwave_environment = flutterwave_environment

    def get_config(self, key, default=None):
        if key == "flutterwave_environment":
            return self.flutterwave_environment
        return default

    def register_tool(self, *, name, toolset, schema, handler):
        self.tools.append({
            "name": name,
            "toolset": toolset,
            "schema": schema,
            "handler": handler,
        })


def test_registered_tools_match_manifest_and_schemas():
    plugin_dir = Path(payops.__file__).parent
    manifest = yaml.safe_load((plugin_dir / "plugin.yaml").read_text())

    ctx = FakePluginContext()
    payops.register(ctx)

    registered_names = [tool["name"] for tool in ctx.tools]
    assert registered_names == manifest["provides_tools"]
    assert len(registered_names) == len(set(registered_names))

    for tool in ctx.tools:
        assert tool["toolset"] == manifest["name"]
        assert tool["schema"]["name"] == tool["name"]
        assert callable(tool["handler"])


def test_flutterwave_environment_setting_is_passed_to_both_handlers():
    ctx = FakePluginContext("production")
    payops.register(ctx)
    assert all(
        tool["handler"].keywords["flutterwave_environment"] == "production"
        for tool in ctx.tools
    )


def test_invalid_flutterwave_environment_fails_plugin_registration():
    ctx = FakePluginContext("live")
    try:
        payops.register(ctx)
    except ValueError as exc:
        assert "flutterwave_environment" in str(exc)
    else:
        raise AssertionError("invalid environment should fail registration")
