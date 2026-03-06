# Copyright: (c) 2024, Long Nguyen
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import pytest
import sys

if sys.version_info < (2, 7):
    pytestmark = pytest.mark.skip("pfSense Ansible modules require Python >= 2.7")

from ansible_collections.pfsensible.core.plugins.modules import pfsense_vip
from ansible_collections.pfsensible.core.plugins.module_utils.vip import PFSenseVIPModule
from .pfsense_module import TestPFSenseModule


class TestPFSenseVIPModule(TestPFSenseModule):

    module = pfsense_vip

    def __init__(self, *args, **kwargs):
        super(TestPFSenseVIPModule, self).__init__(*args, **kwargs)
        self.config_file = 'pfsense_vip_config.xml'
        self.pfmodule = PFSenseVIPModule

    def check_target_elt(self, obj, target_elt):
        """ test the xml definition """
        self.check_param_equal(obj, target_elt, 'mode')
        self.check_value_equal(target_elt, 'interface', self.unalias_interface(obj['interface']))
        self.check_param_equal(obj, target_elt, 'subnet')
        self.check_param_equal(obj, target_elt, 'subnet_bits')
        self.check_param_equal(obj, target_elt, 'type', 'single')

        # Check CARP-specific params
        if obj.get('mode') == 'carp':
            self.check_param_equal(obj, target_elt, 'vhid')
            self.check_param_equal(obj, target_elt, 'advbase', '1')
            self.check_param_equal(obj, target_elt, 'advskew', '0')
            self.check_param_equal(obj, target_elt, 'password')

        # Check noexpand
        if obj.get('noexpand'):
            self.assert_find_xml_elt(target_elt, 'noexpand')

        # Ensure uniqid is present
        self.assert_find_xml_elt(target_elt, 'uniqid')

    def get_target_elt(self, obj, absent=False, module_result=None):
        """ get the generated xml definition """
        vip_elt = self.assert_find_xml_elt(self.xml_result, 'virtualip')

        for item in vip_elt:
            subnet_elt = item.find('subnet')
            if subnet_elt is not None and subnet_elt.text == obj['subnet']:
                return item

        return None

    ##############
    # Create tests
    #
    def test_vip_create_ipalias(self):
        """ test creating an ipalias VIP """
        obj = dict(subnet='192.168.1.50', subnet_bits=32, descr='test_ipalias', mode='ipalias', interface='lan')
        command = "create vip '192.168.1.50', descr='test_ipalias', mode='ipalias', interface='lan', subnet_bits='32'"
        self.do_module_test(obj, command=command)

    def test_vip_create_carp(self):
        """ test creating a CARP VIP """
        obj = dict(subnet='192.168.240.100', subnet_bits=32, descr='test_carp', mode='carp', interface='wan',
                   vhid=10, advbase=1, advskew=100, password='testpass')
        command = ("create vip '192.168.240.100', descr='test_carp', mode='carp', interface='wan', subnet_bits='32'"
                   ", vhid='10', advbase='1', advskew='100', password='testpass'")
        self.do_module_test(obj, command=command)

    def test_vip_create_proxyarp(self):
        """ test creating a proxyarp VIP """
        obj = dict(subnet='192.168.240.50', subnet_bits=32, descr='test_proxyarp', mode='proxyarp', interface='wan')
        command = "create vip '192.168.240.50', descr='test_proxyarp', mode='proxyarp', interface='wan', subnet_bits='32'"
        self.do_module_test(obj, command=command)

    def test_vip_create_other_network(self):
        """ test creating an other/network VIP """
        obj = dict(subnet='10.255.3.0', subnet_bits=24, descr='test_other', mode='other', interface='lan', type='network')
        command = "create vip '10.255.3.0', descr='test_other', mode='other', interface='lan', subnet_bits='24', type='network'"
        self.do_module_test(obj, command=command)

    def test_vip_create_noexpand(self):
        """ test creating a VIP with noexpand """
        obj = dict(subnet='192.168.1.51', subnet_bits=32, descr='test_noexpand', mode='ipalias', interface='lan', noexpand=True)
        command = "create vip '192.168.1.51', descr='test_noexpand', mode='ipalias', interface='lan', subnet_bits='32', noexpand=''"
        self.do_module_test(obj, command=command)

    ##############
    # Update tests
    #
    def test_vip_update_noop(self):
        """ test idempotency """
        obj = dict(subnet='192.168.1.100', subnet_bits=32, descr='existing_ipalias', mode='ipalias', interface='lan')
        self.do_module_test(obj, changed=False)

    def test_vip_update_descr(self):
        """ test changing description """
        obj = dict(subnet='192.168.1.100', subnet_bits=32, descr='new_description', mode='ipalias', interface='lan')
        command = "update vip '192.168.1.100' set descr='new_description'"
        self.do_module_test(obj, command=command)

    def test_vip_update_carp_to_ipalias(self):
        """ test changing mode from carp to ipalias, CARP params should be removed """
        obj = dict(subnet='192.168.240.200', subnet_bits=32, descr='existing_carp', mode='ipalias', interface='wan')
        command = "update vip '192.168.240.200' set mode='ipalias', vhid=none, advbase=none, advskew=none, password=none"
        self.do_module_test(obj, command=command)

    ##############
    # Delete tests
    #
    def test_vip_delete(self):
        """ test deleting a VIP """
        obj = dict(subnet='192.168.1.100')
        command = "delete vip '192.168.1.100'"
        self.do_module_test(obj, command=command, delete=True)

    ##############
    # Validation failure tests
    #
    def test_vip_invalid_interface(self):
        """ test invalid interface """
        obj = dict(subnet='192.168.1.50', subnet_bits=32, mode='ipalias', interface='invalid_if')
        msg = 'invalid_if is not a valid interface'
        self.do_module_test(obj, msg=msg, failed=True)

    def test_vip_invalid_ip(self):
        """ test invalid IP address """
        obj = dict(subnet='not.an.ip', subnet_bits=32, mode='ipalias', interface='lan')
        msg = 'not.an.ip is not a valid IP address'
        self.do_module_test(obj, msg=msg, failed=True)

    def test_vip_carp_vhid_out_of_range(self):
        """ test CARP vhid out of range """
        obj = dict(subnet='192.168.240.50', subnet_bits=32, mode='carp', interface='wan',
                   vhid=300, password='testpass')
        msg = 'vhid must be between 1 and 255'
        self.do_module_test(obj, msg=msg, failed=True)

    def test_vip_carp_duplicate_vhid(self):
        """ test CARP duplicate vhid on same interface """
        obj = dict(subnet='192.168.240.50', subnet_bits=32, mode='carp', interface='wan',
                   vhid=1, password='testpass')
        msg = 'vhid 1 is already in use on interface wan'
        self.do_module_test(obj, msg=msg, failed=True)

    def test_vip_carp_advbase_out_of_range(self):
        """ test CARP advbase out of range """
        obj = dict(subnet='192.168.240.50', subnet_bits=32, mode='carp', interface='wan',
                   vhid=10, advbase=300, password='testpass')
        msg = 'advbase must be between 1 and 254'
        self.do_module_test(obj, msg=msg, failed=True)

    def test_vip_carp_advskew_out_of_range(self):
        """ test CARP advskew out of range """
        obj = dict(subnet='192.168.240.50', subnet_bits=32, mode='carp', interface='wan',
                   vhid=10, advskew=300, password='testpass')
        msg = 'advskew must be between 0 and 254'
        self.do_module_test(obj, msg=msg, failed=True)
