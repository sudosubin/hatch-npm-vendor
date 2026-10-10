from __future__ import annotations

from pathlib import Path
from typing import Any

from hatchling.builders.hooks.plugin.interface import BuildHookInterface

from hatch_npm_vendor.vendor import (
    install_packages,
    parse_package_specs,
    should_skip,
)

DEFAULT_SRC = "src"
DEFAULT_REGISTRY = "https://registry.npmjs.org"


class NpmVendorBuildHook(BuildHookInterface):
    PLUGIN_NAME = "npm-vendor"

    def initialize(self, version: str, build_data: dict[str, Any]) -> None:
        if should_skip():
            self.app.display_warning(
                "Skipping npm vendoring (HATCH_NPM_VENDOR_SKIP is set)"
            )
            return

        install_packages(
            Path(self.root),
            build_data,
            parse_package_specs(self.config),
            src=str(self.config.get("src", DEFAULT_SRC)),
            registry=str(self.config.get("registry", DEFAULT_REGISTRY)),
        )
