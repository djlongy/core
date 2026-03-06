# -*- coding: utf-8 -*-

# Copyright: (c) 2024, Long Nguyen
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type
import re
from ansible_collections.pfsensible.core.plugins.module_utils.module_base import PFSenseModuleBase

HAPROXY_FRONTEND_ARGUMENT_SPEC = dict(
    state=dict(default='present', choices=['present', 'absent']),
    name=dict(required=True, type='str'),
    status=dict(default='active', choices=['active', 'disabled']),
    type=dict(default='tcp', choices=['tcp', 'http', 'ssl']),
    backend=dict(required=False, type='str'),
    extaddrs=dict(required=False, type='list', elements='dict', options=dict(
        address=dict(required=True, type='str'),
        port=dict(required=True, type='str'),
        ssl=dict(default='', type='str'),
    )),
    dontlognull=dict(default=True, type='bool'),
    dontlog_normal=dict(default=True, type='bool'),
    socket_stats=dict(default=True, type='bool'),
    max_connections=dict(required=False, type='int'),
    client_timeout=dict(required=False, type='int'),
)

HAPROXY_FRONTEND_REQUIRED_IF = [
    ["state", "present", ["backend", "extaddrs"]],
]


class PFSenseHaproxyFrontendModule(PFSenseModuleBase):
    """ module managing pfsense haproxy frontends """

    @staticmethod
    def get_argument_spec():
        """ return argument spec """
        return HAPROXY_FRONTEND_ARGUMENT_SPEC

    ##############################
    # init
    #
    def __init__(self, module, pfsense=None):
        super(PFSenseHaproxyFrontendModule, self).__init__(module, pfsense)
        self.name = "pfsense_haproxy_frontend"
        self.obj = dict()

        pkgs_elt = self.pfsense.get_element('installedpackages')
        self.haproxy = pkgs_elt.find('haproxy') if pkgs_elt is not None else None
        self.root_elt = self.haproxy.find('ha_backends') if self.haproxy is not None else None
        if self.root_elt is None:
            self.module.fail_json(msg='Unable to find frontends XML configuration entry. Are you sure haproxy is installed?')

    ##############################
    # params processing
    #
    def _validate_params(self):
        """ do some extra checks on input parameters """
        if re.search(r'[^a-zA-Z0-9\.\-_]', self.params['name']) is not None:
            self.module.fail_json(msg="The field 'name' contains invalid characters.")

        if self.params['state'] == 'present':
            # validate backend exists
            ha_pools = self.haproxy.find('ha_pools') if self.haproxy is not None else None
            if ha_pools is not None:
                found = False
                for item_elt in ha_pools:
                    if item_elt.tag != 'item':
                        continue
                    name_elt = item_elt.find('name')
                    if name_elt is not None and name_elt.text == self.params['backend']:
                        found = True
                        break
                if not found:
                    self.module.fail_json(msg="Backend '{0}' not found. Create it first.".format(self.params['backend']))

    def _params_to_obj(self):
        """ return a frontend dict from module params """
        obj = dict()
        obj['name'] = self.params['name']
        if self.params['state'] == 'present':
            obj['status'] = self.params['status']
            obj['type'] = self.params['type']
            obj['backend_serverpool'] = self.params['backend']

            # Build extaddr structure
            # pfSense format: a_extaddr contains item entries
            # extaddr value is '{ip}_ipv4' referencing a VIP
            extaddr_items = []
            for addr in self.params['extaddrs']:
                extaddr_items.append(dict(
                    extaddr=addr['address'] + '_ipv4',
                    extaddr_port=str(addr['port']),
                    extaddr_ssl=addr.get('ssl', ''),
                ))
            obj['a_extaddr'] = dict(item=extaddr_items)

            # Empty required arrays
            obj['ha_acls'] = ''
            obj['a_actionitems'] = ''

            # Optional bool fields (pfSense uses empty string for true, absent for false)
            self._get_ansible_param_bool(obj, 'dontlognull', value='')
            self._get_ansible_param_bool(obj, 'dontlog_normal', value='')
            self._get_ansible_param_bool(obj, 'socket_stats', value='')

            self._get_ansible_param(obj, 'max_connections', fname='max_connections')
            self._get_ansible_param(obj, 'client_timeout')

        return obj

    ##############################
    # XML processing
    #
    def _create_target(self):
        """ create the XML target_elt """
        elt = self.pfsense.new_element('item')
        self.obj['id'] = self._get_next_id()
        return elt

    def _find_target(self):
        """ find the XML target_elt """
        for item_elt in self.root_elt:
            if item_elt.tag != 'item':
                continue
            name_elt = item_elt.find('name')
            if name_elt is not None and name_elt.text == self.obj['name']:
                return item_elt
        return None

    def _get_next_id(self):
        """ get next free haproxy id """
        max_id = 99
        id_elts = self.haproxy.findall('.//id')
        for id_elt in id_elts:
            if id_elt.text is None:
                continue
            ha_id = int(id_elt.text)
            if ha_id > max_id:
                max_id = ha_id
        return str(max_id + 1)

    @staticmethod
    def _get_params_to_remove():
        """ returns the list of params to remove if they are not set """
        return ['dontlognull', 'dontlog_normal', 'socket_stats', 'max_connections', 'client_timeout']

    ##############################
    # run
    #
    def _update(self):
        """ make the target pfsense reload haproxy """
        return self.pfsense.phpshell('''require_once("haproxy/haproxy.inc");
$result = haproxy_check_and_run($savemsg, true); if ($result) unlink_if_exists($d_haproxyconfdirty_path);''')

    ##############################
    # Logging
    #
    def _get_obj_name(self):
        """ return obj's name """
        return "'{0}'".format(self.obj['name'])

    def _log_fields(self, before=None):
        """ generate pseudo-CLI command fields parameters to create an obj """
        values = ''
        if before is None:
            values += self.format_cli_field(self.obj, 'status', default='active')
            values += self.format_cli_field(self.obj, 'type', default='tcp')
            values += self.format_cli_field(self.obj, 'backend_serverpool', fname='backend')
            # Log extaddrs as a summary
            if 'a_extaddr' in self.obj and 'item' in self.obj['a_extaddr']:
                for item in self.obj['a_extaddr']['item']:
                    values += ", listen={0}:{1}".format(item['extaddr'], item['extaddr_port'])
        else:
            values += self.format_updated_cli_field(self.obj, before, 'status', default='active', add_comma=(values))
            values += self.format_updated_cli_field(self.obj, before, 'type', default='tcp', add_comma=(values))
            values += self.format_updated_cli_field(self.obj, before, 'backend_serverpool', add_comma=(values), fname='backend')

        return values
