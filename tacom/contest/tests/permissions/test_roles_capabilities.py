import pytest
from unittest import TestCase

from contest.permissions.capabilities import CAPABILITIES, Capability
from contest.permissions.roles import (
    GLOBAL_ROLE_CAPABILITIES,
    CONTEST_ROLE_CAPABILITIES,
)


@pytest.mark.system
@pytest.mark.unit
class RolesCapabilitiesTests(TestCase):
    @staticmethod
    def test_all_capabilities_registered():
        for cap in Capability:
            assert cap in CAPABILITIES

    @staticmethod
    def test_role_capabilities_are_registered():
        defined = set(CAPABILITIES.keys())

        for role_map in [GLOBAL_ROLE_CAPABILITIES, CONTEST_ROLE_CAPABILITIES]:
            for caps in role_map.values():
                for cap in caps:
                    assert cap in defined

    @staticmethod
    def test_scope_consistency():
        for role, caps in CONTEST_ROLE_CAPABILITIES.items():
            for cap in caps:
                assert CAPABILITIES[cap]["scope"] == "contest"
