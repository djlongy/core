# Copyright: (c) 2024, Long Nguyen
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import pytest
import sys

if sys.version_info < (2, 7):
    pytestmark = pytest.mark.skip("pfSense Ansible modules require Python >= 2.7")

from ansible_collections.pfsensible.core.plugins.modules import pfsense_haproxy_frontend
from ansible_collections.pfsensible.core.plugins.module_utils.haproxy_frontend import PFSenseHaproxyFrontendModule
from .pfsense_module import TestPFSenseModule


class TestPFSenseHaproxyFrontendModule(TestPFSenseModule):

    module = pfsense_haproxy_frontend

    def __init__(self, *args, **kwargs):
        super(TestPFSenseHaproxyFrontendModule, self).__init__(*args, **kwargs)
        self.config_file = 'pfsense_haproxy_frontend_config.xml'
        self.pfmodule = PFSenseHaproxyFrontendModule

    def check_target_elt(self, obj, target_elt):
        """ test the xml definition """
        self.check_param_equal(obj, target_elt, 'name')
        self.check_param_equal(obj, target_elt, 'status', 'active')
        self.check_param_equal(obj, target_elt, 'type', 'tcp')
        if 'backend' in obj:
            self.assert_xml_elt_equal(target_elt, 'backend_serverpool', obj['backend'])

    def get_target_elt(self, obj, absent=False, module_result=None):
        """ get the generated xml definition """
        pkgs_elt = self.xml_result.find('installedpackages')
        haproxy_elt = pkgs_elt.find('haproxy') if pkgs_elt is not None else None
        backends_elt = haproxy_elt.find('ha_backends') if haproxy_elt is not None else None
        if backends_elt is None:
            return None

        for item in backends_elt:
            if item.tag != 'item':
                continue
            name_elt = item.find('name')
            if name_elt is not None and name_elt.text == obj['name']:
                return item

        return None

    ##############
    # Create tests
    #
    def test_frontend_create(self):
        """ test creating a frontend """
        obj = dict(name='fe_gitlab_443', backend='be_gitlab_443',
                   extaddrs=[dict(address='192.168.20.50', port='443')])
        command = "create haproxy_frontend 'fe_gitlab_443', backend='be_gitlab_443', listen=192.168.20.50_ipv4:443"
        self.do_module_test(obj, command=command)

    def test_frontend_create_http(self):
        """ test creating an http frontend """
        obj = dict(name='fe_web_80', type='http', backend='be_gitlab_443',
                   extaddrs=[dict(address='192.168.20.50', port='80')])
        command = "create haproxy_frontend 'fe_web_80', type='http', backend='be_gitlab_443', listen=192.168.20.50_ipv4:80"
        self.do_module_test(obj, command=command)

    ##############
    # Update tests
    #
    def test_frontend_update_noop(self):
        """ test idempotency """
        obj = dict(name='fe_vault_8200', backend='be_vault_8200',
                   extaddrs=[dict(address='192.168.20.50', port='8200')])
        self.do_module_test(obj, changed=False)

    def test_frontend_update_backend(self):
        """ test changing backend """
        obj = dict(name='fe_vault_8200', backend='be_gitlab_443',
                   extaddrs=[dict(address='192.168.20.50', port='8200')])
        command = "update haproxy_frontend 'fe_vault_8200' set backend='be_gitlab_443'"
        self.do_module_test(obj, command=command)

    ##############
    # Delete tests
    #
    def test_frontend_delete(self):
        """ test deleting a frontend """
        obj = dict(name='fe_vault_8200')
        command = "delete haproxy_frontend 'fe_vault_8200'"
        self.do_module_test(obj, command=command, delete=True)

    ##############
    # Validation tests
    #
    def test_frontend_invalid_name(self):
        """ test invalid name """
        obj = dict(name='fe invalid!', backend='be_vault_8200',
                   extaddrs=[dict(address='192.168.20.50', port='8200')])
        msg = "The field 'name' contains invalid characters."
        self.do_module_test(obj, msg=msg, failed=True)

    def test_frontend_missing_backend(self):
        """ test referencing nonexistent backend """
        obj = dict(name='fe_test', backend='be_nonexistent',
                   extaddrs=[dict(address='192.168.20.50', port='8200')])
        msg = "Backend 'be_nonexistent' not found. Create it first."
        self.do_module_test(obj, msg=msg, failed=True)
