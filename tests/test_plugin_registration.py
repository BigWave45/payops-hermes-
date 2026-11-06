"""Hermes registration contract smoke tests."""
from pathlib import Path

import yaml

import payops


class FakePluginContext:
    def __init__(self):
        self.tools = []

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
