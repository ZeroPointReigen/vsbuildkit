from collections import defaultdict
from dataclasses import dataclass
from functools import cached_property
import json
from packaging.version import Version, VERSION_PATTERN
from pathlib import Path
import re
import requests

from vsbuildkit.utils.dictwrapper import DictWrapper


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_CONFIG = SCRIPT_DIR / "default-config.json"


class VersionSpecifier:
    def __init__(self, version_range: str):
        self.lower_range = None
        self.upper_range = None
        self.lower_inclusive = True
        self.upper_inclusive = True
        self._parse_version(version_range)

    def __str__(self):
        lower_inclusive = "[" if self.lower_inclusive else "("
        upper_inclusive = "]" if self.upper_inclusive else ")"
        return f'{lower_inclusive}{self.lower_range if self.lower_range else ""},{self.upper_range if self.upper_range else ""}{upper_inclusive}'

    def __repr__(self):
        return f"VersionSpecifier('{str(self)}')"

    def __contains__(self, version):
        if isinstance(version, str):
            version = Version(version)

        """Check if the version is within the range."""
        if not self.lower_range and not self.upper_range:
            return True  # no range specified, so all versions are valid
        if self.lower_range and self.upper_range:
            lower_check = self.lower_range <= version if self.lower_inclusive else self.lower_range < version
            upper_check = version <= self.upper_range if self.upper_inclusive else version < self.upper_range
            return lower_check and upper_check
        elif self.lower_range:
            return self.lower_range <= version if self.lower_inclusive else self.lower_range < version
        elif self.upper_range:
            return version <= self.upper_range if self.upper_inclusive else version < self.upper_range

    def _parse_version(self, version_range: str):
        version_range = version_range.strip()
        if not version_range:
            raise ValueError("version range: empty")

        if version_range.count(",") != 1:
            raise ValueError(f"version range: {version_range}: must contain exactly one comma.")

        left, right = version_range.split(",")
        left_re = re.compile(r"^(?P<pre_range>[\[\(])(" + VERSION_PATTERN + r")?$", re.IGNORECASE | re.VERBOSE)
        left_match = left_re.match(left)
        if not left_match:
            raise ValueError(f"invalid lower range: ({left}) format")

        left_match = left_match.groupdict()
        self.lower_inclusive = left_match["pre_range"] == "["
        self.lower_range = Version(left_match["release"]) if left_match["release"] else None

        right_re = re.compile(r"^(" + VERSION_PATTERN + r")?(?P<post_range>[\]\)])$", re.IGNORECASE | re.VERBOSE)
        right_match = right_re.match(right)
        if not right_match:
            raise ValueError(f"invalid upper range ({right}) format")

        right_match = right_match.groupdict()
        self.upper_inclusive = right_match["post_range"] == "]"
        self.upper_range = Version(right_match["release"]) if right_match["release"] else None

    def contains(self, version: str):
        """Check if the version is within the range."""
        return version in self


@dataclass
class Dependency:
    name: str
    versionRange: str | VersionSpecifier

    def __post_init__(self):
        """Convert string version range to SpecifierSet if needed."""
        # if isinstance(self.versionRange, str):
        #     self.versionRange = SpecifierSet(self.versionRange)


class SdkPackage(DictWrapper):
    @cached_property
    def dependencies(self):
        """Return the dependencies of the SDK package."""
        deps = []
        for pkg in self.packages:
            for name, ver_range in pkg.dependencies.items():
                deps.append(Dependency(name=name, versionRange=ver_range))
        return deps


class VsManifest(DictWrapper):

    @cached_property
    def packages(self):
        raw_data = self._get_data()
        packages = defaultdict(list)

        for raw_package in raw_data["packages"]:
            packages[raw_package["id"]].append(DictWrapper(raw_package))

        return packages

    @cached_property
    def sdk_packages(self):
        packages = self.packages

        _sdk_packages = defaultdict(dict)
        for package_id, package_list in packages.items():
            if match := re.match(r"^Microsoft\.VisualStudio\.Component\.Windows(?:\d+)SDK.*\.(\d+)$", package_id, re.IGNORECASE):
                ver = match.group(1)
                _sdk_packages[Version(ver)] = SdkPackage({"id": package_id, "ver": ver, "packages": package_list})

        return _sdk_packages

    @cached_property
    def latest_sdk(self):
        sdk_packages = self.sdk_packages
        if not sdk_packages:
            return None

        latest_sdk = max(sdk_packages.keys())
        return sdk_packages[latest_sdk]


class ChannelManifest(DictWrapper):
    config_path: Path | str = None

    def _get_data(self):
        """Return the wrapped dictionary."""
        return self.channel_manifest

    @cached_property
    def config(self):
        print("Initializing Config ...")
        if self.config_path:
            if not self.config_path.exists():
                raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
            update_config = json.loads(self.config_path.read_bytes())
        else:
            update_config = {}

        _config = json.loads(DEFAULT_CONFIG.read_bytes())  # Start with default config
        _config.update(update_config)  # Update with the config from the provided config file
        _config.update(self._data)  # Update with the config from this channel manifest

        return _config

    @cached_property
    def channel_manifest(self):
        config = self.config
        print("Initializing Channel Manifest...")
        if "channel_url" not in config:
            raise KeyError("The configuration is missing the required 'channel_url' key.")

        try:
            resp = requests.get(config["channel_url"])
            resp.raise_for_status()
        except requests.RequestException as e:
            raise RuntimeError(f"Failed to fetch channel manifest from {config['channel_url']}: {e}")
        return resp.json()

    @cached_property
    def vs_manifest(self):
        channelItems = self.get("channelItems")
        if not channelItems:
            raise ValueError("The 'channelItems' attribute is missing or empty.")

        # Find the item with the required ID
        try:
            item = next(
                item for item in channelItems
                if item.get("id") == "Microsoft.VisualStudio.Manifests.VisualStudio"
            )
        except StopIteration:
            raise ValueError("No matching item found in 'channelItems' with ID 'Microsoft.VisualStudio.Manifests.VisualStudio'.")

        # Find the payload with the required fileName
        item_payloads = item.get("payloads")
        if not item_payloads:
            raise ValueError("The channel manifest's 'payloads' attribute is missing or empty.")
        
        try:
            payload = next(
                payload for payload in item_payloads
                if payload.get("fileName") == "VisualStudio.vsman"
            )
        except StopIteration:
            raise ValueError("No matching payload found in 'payloads' with fileName 'VisualStudio.vsman'.")

         # Fetch and return the Visual Studio manifest
        print("Initializing Visual Studio Manifest ...")
        patyload_url = payload.get("url")
        if not patyload_url:
            raise ValueError("The channel's vs manifest URL is missing.")
                
        try:
            resp = requests.get(patyload_url)
            resp.raise_for_status()
        except requests.RequestException as e:
            raise RuntimeError(f"Failed to fetch Visual Studio manifest from {patyload_url}: {e}")

        return VsManifest(resp.json())
