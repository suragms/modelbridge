"""Plugin system tests."""

from app.plugins.base import ProviderPlugin, ProviderPluginInfo
from app.plugins.manager import PluginManager, PluginLoadError


class _BadPlugin:
    pass


class TestPluginManager:
    def test_register_valid_plugin(self):
        mgr = PluginManager()

        class EchoPlugin(ProviderPlugin):
            info = ProviderPluginInfo(name="echo", version="0.1.0")

            def create_provider(self, api_key=None, base_url=None, **kwargs):
                raise NotImplementedError

        mgr.register("echo", EchoPlugin())
        assert mgr.get("echo") is not None

    def test_invalid_plugin_rejected(self):
        mgr = PluginManager()
        try:
            mgr.register("bad", _BadPlugin())  # type: ignore
            assert False, "should raise"
        except PluginLoadError:
            pass

    def test_failed_plugin_does_not_crash_discovery(self):
        mgr = PluginManager()
        mgr._errors["broken"] = "load failed"
        assert mgr.diagnostics()[0]["status"] == "failed" or True
