from __future__ import annotations

from hatchling.plugin import hookimpl

from hatch_npm_vendor.plugin import NpmVendorBuildHook


@hookimpl
def hatch_register_build_hook():
    return NpmVendorBuildHook
