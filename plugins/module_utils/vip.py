# -*- coding: utf-8 -*-

# Copyright: (c) 2024, Long Nguyen
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type
from ansible_collections.pfsensible.core.plugins.module_utils.module_base import PFSenseModuleBase
from ipaddress import ip_address

VIP_ARGUMENT_SPEC = dict(
    state=dict(default='present', choices=['present', 'absent']),
    subnet=dict(required=True, type='str'),
    subnet_bits=dict(required=False, type='int'),
    descr=dict(required=False, default='', type='str'),
    mode=dict(required=False, choices=['ipalias', 'carp', 'proxyarp', 'other']),
    interface=dict(required=False, type='str'),
    type=dict(default='single', choices=['single', 'network']),
    noexpand=dict(required=False, type='bool'),
    vhid=dict(required=False, type='int'),
    advbase=dict(required=False, type='int'),
    advskew=dict(required=False, type='int'),
    password=dict(required=False, type='str', no_log=True),
)

VIP_REQUIRED_IF = [
    ["state", "present", ["mode", "interface", "subnet_bits"]],
    ["mode", "carp", ["vhid", "password"]],
]


class PFSenseVIPModule(PFSenseModuleBase):
    """ module managing pfsense virtual IPs """

    @staticmethod
    def get_argument_spec():
        """ return argument spec """
        return VIP_ARGUMENT_SPEC

    ##############################
    # init
    #
    def __init__(self, module, pfsense=None):
        super(PFSenseVIPModule, self).__init__(module, pfsense, root='virtualip', create_root=True, node='vip', key='subnet')
        self.name = "pfsense_vip"

    ##############################
    # params processing
    #
    def _validate_params(self):
        """ do some extra checks on input parameters """
        params = self.params

        if params['state'] == 'present':
            # validate IP address
            try:
                ip_address(u'{0}'.format(params['subnet']))
            except ValueError:
                self.module.fail_json(msg='{0} is not a valid IP address'.format(params['subnet']))

            # validate subnet_bits
            addr = ip_address(u'{0}'.format(params['subnet']))
            if addr.version == 4:
                if params['subnet_bits'] < 1 or params['subnet_bits'] > 32:
                    self.module.fail_json(msg='subnet_bits must be between 1 and 32 for IPv4')
            else:
                if params['subnet_bits'] < 1 or params['subnet_bits'] > 128:
                    self.module.fail_json(msg='subnet_bits must be between 1 and 128 for IPv6')

            # validate CARP params
            if params['mode'] == 'carp':
                if params.get('vhid') is not None:
                    if params['vhid'] < 1 or params['vhid'] > 255:
                        self.module.fail_json(msg='vhid must be between 1 and 255')

                    # check vhid uniqueness per interface
                    interface = self.pfsense.parse_interface(params['interface'])
                    for vip_elt in self.root_elt:
                        if vip_elt.tag != 'vip':
                            continue
                        subnet_elt = vip_elt.find('subnet')
                        if subnet_elt is not None and subnet_elt.text == params['subnet']:
                            continue  # skip self
                        mode_elt = vip_elt.find('mode')
                        if mode_elt is None or mode_elt.text != 'carp':
                            continue
                        iface_elt = vip_elt.find('interface')
                        vhid_elt = vip_elt.find('vhid')
                        if (iface_elt is not None and iface_elt.text == interface
                                and vhid_elt is not None and vhid_elt.text == str(params['vhid'])):
                            self.module.fail_json(msg='vhid {0} is already in use on interface {1}'.format(
                                params['vhid'], params['interface']))

                if params.get('advbase') is not None and (params['advbase'] < 1 or params['advbase'] > 254):
                    self.module.fail_json(msg='advbase must be between 1 and 254')

                if params.get('advskew') is not None and (params['advskew'] < 0 or params['advskew'] > 254):
                    self.module.fail_json(msg='advskew must be between 0 and 254')

    def _params_to_obj(self):
        """ return a dict from module params """
        params = self.params
        obj = dict()

        obj['subnet'] = params['subnet']
        if params['state'] == 'present':
            obj['mode'] = params['mode']
            obj['interface'] = self.pfsense.parse_interface(params['interface'])
            obj['subnet_bits'] = str(params['subnet_bits'])
            self._get_ansible_param(obj, 'descr')
            self._get_ansible_param(obj, 'type')

            if params.get('noexpand'):
                obj['noexpand'] = ''

            if params['mode'] == 'carp':
                self._get_ansible_param(obj, 'vhid')
                if params.get('advbase') is not None:
                    obj['advbase'] = str(params['advbase'])
                else:
                    obj['advbase'] = '1'
                if params.get('advskew') is not None:
                    obj['advskew'] = str(params['advskew'])
                else:
                    obj['advskew'] = '0'
                self._get_ansible_param(obj, 'password')

        return obj

    ##############################
    # XML processing
    #
    def _create_target(self):
        """ create the XML target_elt """
        elt = self.pfsense.new_element('vip')
        # VIPs require a uniqid, referenced as _vip<uniqid> elsewhere
        uniqid = self.pfsense.uniqid()
        elt.append(self.pfsense.new_element('uniqid', text=uniqid))
        return elt

    @staticmethod
    def _get_params_to_remove():
        """ returns the list of params to remove if they are not set """
        return ['noexpand', 'vhid', 'advbase', 'advskew', 'password']

    ##############################
    # run
    #
    def _update(self):
        """ make the target pfsense reload """
        return self.pfsense.phpshell('''
require_once("filter.inc");
require_once("interfaces.inc");
interfaces_vips_configure();
filter_configure();
clear_subsystem_dirty('vip');
''')

    ##############################
    # Logging
    #
    def _get_obj_name(self):
        """ return obj's name """
        return "'{0}'".format(self.obj['subnet'])

    def _log_fields(self, before=None):
        """ generate pseudo-CLI command fields parameters to create an obj """
        values = ''
        if before is None:
            values += self.format_cli_field(self.obj, 'descr', default='')
            values += self.format_cli_field(self.obj, 'mode')
            values += self.format_cli_field(self.params, 'interface')
            values += self.format_cli_field(self.obj, 'subnet_bits')
            values += self.format_cli_field(self.obj, 'type', default='single')
            values += self.format_cli_field(self.obj, 'noexpand')
            values += self.format_cli_field(self.obj, 'vhid')
            values += self.format_cli_field(self.obj, 'advbase')
            values += self.format_cli_field(self.obj, 'advskew')
            values += self.format_cli_field(self.obj, 'password')
        else:
            values += self.format_updated_cli_field(self.obj, before, 'descr', default='', add_comma=(values))
            values += self.format_updated_cli_field(self.obj, before, 'mode', add_comma=(values))
            values += self.format_updated_cli_field(self.params, before, 'interface', add_comma=(values))
            values += self.format_updated_cli_field(self.obj, before, 'subnet_bits', add_comma=(values))
            values += self.format_updated_cli_field(self.obj, before, 'type', default='single', add_comma=(values))
            values += self.format_updated_cli_field(self.obj, before, 'noexpand', add_comma=(values))
            values += self.format_updated_cli_field(self.obj, before, 'vhid', add_comma=(values))
            values += self.format_updated_cli_field(self.obj, before, 'advbase', add_comma=(values))
            values += self.format_updated_cli_field(self.obj, before, 'advskew', add_comma=(values))
            values += self.format_updated_cli_field(self.obj, before, 'password', add_comma=(values))

        return values
