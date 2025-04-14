import json
from pathlib import Path
import re
from unittest.mock import MagicMock, patch
import pytest
from packaging.version import Version

from vsbuildkit.manifest import ChannelManifest, Dependency, SdkPackage, VersionSpecifier, VsManifest


class TestVersionSpecifier:
    def test_version_general_specifier(self):
        version_str = "[1.0.0,2.0.0)"
        vs = VersionSpecifier(version_str)
        assert str(vs) == version_str

        assert "1.0.0" in vs
        assert vs.contains("1.0.0")

        assert "1.99.99" in vs
        assert vs.contains("1.99.99")

        assert "2.0.0" not in vs
        assert not vs.contains("2.0.0")

    def test_version_specific_inclusive_lower(self):
        version_str = "[1.0.0,]"
        vs = VersionSpecifier(version_str)

        assert str(vs) == version_str

        assert "1.0.0" in vs
        assert vs.contains("1.0.0")

        assert "1.99.99" in vs
        assert vs.contains("1.99.99")

        assert "99.99.99" in vs
        assert vs.contains("99.99.99")

    def test_version_specific_inclusive_upper(self):
        version_str = "[,2.0.0]"
        vs = VersionSpecifier(version_str)
        assert str(vs) == version_str

        assert "0.0.0" in vs
        assert vs.contains("0.0.0")

        assert "1.0.0" in vs
        assert vs.contains("1.0.0")

        assert "1.99.99" in vs
        assert vs.contains("1.99.99")

        assert "2.0.0" in vs
        assert vs.contains("2.0.0")

    def test_version_exclusive_range(self):
        version_str = "(1.0.0,2.0.0)"
        vs = VersionSpecifier(version_str)
        assert str(vs) == version_str

        assert "0.0.0" not in vs
        assert not vs.contains("0.0.0")

        assert "1.0.0" not in vs
        assert not vs.contains("1.0.0")

        assert "1.0.1" in vs
        assert vs.contains("1.0.1")

        assert "1.99.99" in vs
        assert vs.contains("1.99.99")

        assert "2.0.0" not in vs
        assert not vs.contains("2.0.0")

        assert "2.0.1" not in vs
        assert not vs.contains("2.0.1")

    def test_empty_version_range(self):
        with pytest.raises(ValueError, match=re.escape("version range: empty")):
            VersionSpecifier("")

    def test_invalid_version_range_format(self):
        with pytest.raises(ValueError, match=re.escape("must contain exactly one comma")):
            VersionSpecifier("[1.0.0 2.0.0)")

        with pytest.raises(ValueError, match=re.escape("must contain exactly one comma")):
            VersionSpecifier("[1.0.0,2.0.0,3.0.0)")

    def test_invalid_lower_range(self):
        with pytest.raises(ValueError, match=re.escape("invalid lower range")):
            VersionSpecifier("[invalid,2.0.0)")

    def test_invalid_upper_range(self):
        with pytest.raises(ValueError, match=re.escape("invalid upper range")):
            VersionSpecifier("[1.0.0,invalid)")

    def test_repr(self):
        version_str = "[1.0.0,2.0.0)"
        vs = VersionSpecifier(version_str)
        assert repr(vs) == f"VersionSpecifier('{version_str}')"

    def test_contains_invalid_version(self):
        version_str = "[1.0.0,2.0.0)"
        vs = VersionSpecifier(version_str)

        with pytest.raises(ValueError):
            "invalid_version" in vs

    def test_no_bounds(self):
        version_str = "[,]"
        vs = VersionSpecifier(version_str)

        assert "0.0.0" in vs
        assert "999.999.999" in vs

    def test_only_lower_bound(self):
        version_str = "[1.0.0,)"
        vs = VersionSpecifier(version_str)

        assert "1.0.0" in vs
        assert "2.0.0" in vs
        assert "0.9.9" not in vs

    def test_only_upper_bound(self):
        version_str = "(,2.0.0]"
        vs = VersionSpecifier(version_str)

        assert "2.0.0" in vs
        assert "1.0.0" in vs
        assert "2.0.1" not in vs


class TestDependency:
    def test_dependency_initialization(self):
        dep = Dependency(name="test-package", versionRange="[1.0.0,2.0.0)")
        assert dep.name == "test-package"
        assert dep.versionRange == "[1.0.0,2.0.0)"

    def test_dependency_version_range_conversion(self):
        dep = Dependency(name="test-package", versionRange=VersionSpecifier("[1.0.0,2.0.0)"))
        assert isinstance(dep.versionRange, VersionSpecifier)
        assert dep.versionRange.lower_range == Version("1.0.0")
        assert dep.versionRange.upper_range == Version("2.0.0")


class TestSdkPackage:
    def test_sdk_package_dependencies(self):
        data = {
            "packages": [
                {"dependencies": {"dep1": "[1.0.0,2.0.0)", "dep2": "[2.0.0,3.0.0)"}},
                {"dependencies": {"dep3": "[3.0.0,4.0.0)"}},
            ]
        }
        sdk_package = SdkPackage(data)
        dependencies = sdk_package.dependencies

        assert len(dependencies) == 3
        assert dependencies[0].name == "dep1"
        assert dependencies[0].versionRange == "[1.0.0,2.0.0)"
        assert dependencies[1].name == "dep2"
        assert dependencies[2].name == "dep3"


class TestVsManifest:
    def test_vs_manifest_packages(self):
        data = {
            "packages": [
                {"id": "package1", "name": "Package 1"},
                {"id": "package2", "name": "Package 2"},
            ]
        }
        vs_manifest = VsManifest(data)
        packages = vs_manifest.packages

        assert len(packages) == 2
        assert "package1" in packages
        assert "package2" in packages
        assert packages["package1"][0]["name"] == "Package 1"

    def test_vs_manifest_sdk_packages(self):
        data = {
            "packages": [
                {"id": "Microsoft.VisualStudio.Component.Windows10SDK.19041", "name": "SDK 19041"},
                {"id": "Microsoft.VisualStudio.Component.Windows11SDK.22000", "name": "SDK 22000"},
            ]
        }
        vs_manifest = VsManifest(data)
        sdk_packages = vs_manifest.sdk_packages

        assert len(sdk_packages) == 2
        assert Version("19041") in sdk_packages
        assert Version("22000") in sdk_packages

    def test_vs_manifest_latest_sdk(self):
        data = {
            "packages": [
                {"id": "Microsoft.VisualStudio.Component.Windows10SDK.19041", "name": "SDK 19041"},
                {"id": "Microsoft.VisualStudio.Component.Windows11SDK.22000", "name": "SDK 22000"},
            ]
        }
        vs_manifest = VsManifest(data)
        latest_sdk = vs_manifest.latest_sdk

        assert latest_sdk["id"] == "Microsoft.VisualStudio.Component.Windows11SDK.22000"

    def test_latest_sdk_empty(self):
        # Test when sdk_packages is empty
        vs_manifest = VsManifest({"packages": []})
        assert vs_manifest.latest_sdk is None

    def test_vs_manifest_missing_channel_items(self):
        # Create a ChannelManifest instance
        manifest = ChannelManifest({})
        manifest.get = MagicMock(return_value=None)

        # Verify that ValueError is raised
        with pytest.raises(ValueError, match=re.escape("The 'channelItems' attribute is missing or empty.")):
            _ = manifest.vs_manifest

    def test_vs_manifest_empty_channel_items(self):

        # Create a ChannelManifest instance
        manifest = ChannelManifest({})
        manifest.get = MagicMock(return_value=[])

        # Verify that ValueError is raised
        with pytest.raises(ValueError, match=re.escape("The 'channelItems' attribute is missing or empty.")):
            _ = manifest.vs_manifest

    def test_vs_manifest_no_matching_item(self):
        # Mock `get` to return a list without the required ID

        # Create a ChannelManifest instance
        manifest = ChannelManifest({})
        manifest.get = MagicMock(return_value=[{"id": "Some.Other.ID"}])

        # Verify that ValueError is raised
        with pytest.raises(ValueError, match=re.escape("No matching item found in 'channelItems' with ID 'Microsoft.VisualStudio.Manifests.VisualStudio'.")):
            _ = manifest.vs_manifest

    def test_vs_manifest_no_matching_payload(self):
        # Create a ChannelManifest instance
        manifest = ChannelManifest({})
        manifest.get = MagicMock(
            return_value=[{"id": "Microsoft.VisualStudio.Manifests.VisualStudio", "payloads": [{"fileName": "SomeOtherFile.vsman"}]}]
        )

        # Verify that ValueError is raised
        with pytest.raises(ValueError, match=re.escape("No matching payload found in 'payloads' with fileName 'VisualStudio.vsman'.")):
            _ = manifest.vs_manifest

    def test_vs_manifest_missing_payloads(self):
        # Create a ChannelManifest instance
        manifest = ChannelManifest({})
        manifest.get = MagicMock(
            return_value=[{"id": "Microsoft.VisualStudio.Manifests.VisualStudio", "payloads": []}]
        )

        # Verify that ValueError is raised
        with pytest.raises(ValueError, match=re.escape("The channel manifest's 'payloads' attribute is missing or empty.")):
            _ = manifest.vs_manifest

    def test_vs_manifest_missing_payload_url(self):
        # Create a ChannelManifest instance
        manifest = ChannelManifest({})
        manifest.get = MagicMock(
            return_value=[{"id": "Microsoft.VisualStudio.Manifests.VisualStudio", "payloads": [{"fileName": "VisualStudio.vsman"}]}]
        )

        # Verify that ValueError is raised
        with pytest.raises(ValueError, match=re.escape("The channel's vs manifest URL is missing.")):
            _ = manifest.vs_manifest

    @patch("vsbuildkit.manifest.requests.get")
    def test_vs_manifest_failed_request(self, mock_requests_get):
        # Mock `requests.get` to raise a RequestException
        from requests.exceptions import RequestException

        mock_requests_get.side_effect = RequestException("Network error")

        # Create a ChannelManifest instance
        manifest = ChannelManifest({})
        manifest.get = MagicMock(
            return_value=[
                {"id": "Microsoft.VisualStudio.Manifests.VisualStudio", "payloads": [{"fileName": "VisualStudio.vsman", "url": "http://example.com"}]}
            ]
        )
        # Verify that RuntimeError is raised
        with pytest.raises(RuntimeError, match=re.escape("Failed to fetch Visual Studio manifest from http://example.com: Network error")):
            _ = manifest.vs_manifest

    @patch("vsbuildkit.manifest.requests.get")
    def test_vs_manifest_successful_request(self, mock_requests_get):
        # Mock `requests.get` to return a successful response
        mock_requests_get.return_value = MagicMock(status_code=200, json=lambda: {"key": "value"})

        # Create a ChannelManifest instance
        manifest = ChannelManifest({})
        manifest.get = MagicMock(
            return_value=[
                {"id": "Microsoft.VisualStudio.Manifests.VisualStudio", "payloads": [{"fileName": "VisualStudio.vsman", "url": "http://example.com"}]}
            ]
        )

        # Verify the returned VsManifest
        vs_manifest = manifest.vs_manifest
        assert isinstance(vs_manifest, VsManifest)
        assert vs_manifest["key"] == "value"

        # Verify that requests.get was called with the correct URL
        mock_requests_get.assert_called_once_with("http://example.com")


class TestChannelManifest:
    @patch("vsbuildkit.manifest.requests.get")
    def test_channel_manifest_config(self, mock_get):
        mock_get.return_value = MagicMock(status_code=200, json=lambda: {"channel_url": "http://example.com"})
        manifest = ChannelManifest({"channel_url": "http://example.com"})
        config = manifest.config

        assert "channel_url" in config
        assert config["channel_url"] == "http://example.com"

    @patch("vsbuildkit.manifest.requests.get")
    def test_channel_manifest_channel_manifest(self, mock_get):
        mock_get.return_value = MagicMock(status_code=200, json=lambda: {"key": "value"})
        manifest = ChannelManifest({"channel_url": "http://example.com"})
        channel_manifest = manifest.channel_manifest

        assert channel_manifest["key"] == "value"

    def test_channel_manifest_vs_manifest(self):
        mock_get_side_effects = iter(
            [
                MagicMock(
                    status_code=200,
                    json=lambda: {
                        "channelItems": [
                            {
                                "id": "Microsoft.VisualStudio.Manifests.VisualStudio",
                                "version": "17.13.35931.197",
                                "type": "Manifest",
                                "payloads": [{"fileName": "VisualStudio.vsman", "url": "http://example.com/VisualStudio.vsman"}],
                            }
                        ]
                    },
                ),
                MagicMock(
                    status_code=200,
                    json=lambda: {},
                ),
            ]
        )

        with patch("vsbuildkit.manifest.requests.get", side_effect=lambda *args, **kwargs: next(mock_get_side_effects)):
            manifest = ChannelManifest({"channel_url": "http://example.com"})
            vs_manifest = manifest.vs_manifest

        assert isinstance(vs_manifest, VsManifest)

    @patch("vsbuildkit.manifest.DEFAULT_CONFIG")
    def test_config_with_no_config_path(self, mock_default_config):
        # Mock the default config file
        mock_default_config.read_bytes.return_value = json.dumps({"default_key": "default_value"}).encode()

        # Create a ChannelManifest instance with no config_path
        manifest = ChannelManifest({"channel_key": "channel_value"})

        # Verify the merged configuration
        config = manifest.config
        assert config["default_key"] == "default_value"
        assert config["channel_key"] == "channel_value"

    @patch("vsbuildkit.manifest.DEFAULT_CONFIG")
    def test_config_with_nonexistent_config_path(self, mock_default_config):
        # Mock the default config file
        mock_default_config.read_bytes.return_value = json.dumps({"default_key": "default_value"}).encode()

        # Create a ChannelManifest instance with a non-existent config_path
        manifest = ChannelManifest({"channel_key": "channel_value"})
        manifest.config_path = Path("nonexistent_config.json")

        # Verify that FileNotFoundError is raised
        with pytest.raises(FileNotFoundError, match=re.escape("Configuration file not found: nonexistent_config.json")):
            _ = manifest.config

    @patch("vsbuildkit.manifest.DEFAULT_CONFIG")
    @patch("vsbuildkit.manifest.Path.read_bytes")
    @patch("vsbuildkit.manifest.Path.exists")
    def test_config_with_existing_config_path(self, mock_exists, mock_read_bytes, mock_default_config):
        # Mock the default config file
        mock_default_config.read_bytes.return_value = json.dumps({"default_key": "default_value"}).encode()

        # Mock the provided config file
        mock_read_bytes.return_value = json.dumps({"file_key": "file_value"}).encode()

        # Mock the Path.exists method to simulate the file's existence
        mock_exists.return_value = True

        # Create a ChannelManifest instance with an existing config_path
        manifest = ChannelManifest({"channel_key": "channel_value"})
        manifest.config_path = Path("existing_config.json")

        # Verify the merged configuration
        config = manifest.config
        assert config["default_key"] == "default_value"
        assert config["file_key"] == "file_value"
        assert config["channel_key"] == "channel_value"

    @patch("vsbuildkit.manifest.DEFAULT_CONFIG")
    def test_channel_manifest_missing_channel_url(self, mock_default_config):
        # Mock the default config file to exclude "channel_url"
        mock_default_config.read_bytes.return_value = json.dumps({"some_other_key": "value"}).encode()

        # Create a ChannelManifest instance without "channel_url" in the config
        manifest = ChannelManifest({"some_other_key": "value"})

        # Verify that KeyError is raised
        with pytest.raises(KeyError, match=re.escape("The configuration is missing the required 'channel_url' key.")):
            _ = manifest.channel_manifest

    @patch("vsbuildkit.manifest.requests.get")
    def test_channel_manifest_successful_request(self, mock_get):
        # Mock a successful response from requests.get
        mock_get.return_value = MagicMock(status_code=200, json=lambda: {"key": "value"})

        # Create a ChannelManifest instance with "channel_url" in the config
        manifest = ChannelManifest({"channel_url": "http://example.com"})

        # Verify the returned channel manifest
        channel_manifest = manifest.channel_manifest
        assert channel_manifest["key"] == "value"

        # Verify that requests.get was called with the correct URL
        mock_get.assert_called_once_with("http://example.com")

    @patch("vsbuildkit.manifest.requests.get")
    def test_channel_manifest_failed_request(self, mock_get):
        # Mock a failed response from requests.get with a ConnectionError
        from requests.exceptions import ConnectionError

        mock_get.side_effect = ConnectionError("Network error")

        # Create a ChannelManifest instance with "channel_url" in the config
        manifest = ChannelManifest({"channel_url": "http://example.com"})

        # Verify that RuntimeError is raised
        with pytest.raises(RuntimeError, match=re.escape("Failed to fetch channel manifest from http://example.com: Network error")):
            _ = manifest.channel_manifest
