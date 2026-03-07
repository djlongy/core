#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2024, Long Nguyen
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

ANSIBLE_METADATA = {'metadata_version': '1.1',
                    'status': ['preview'],
                    'supported_by': 'community'}

DOCUMENTATION = """
---
module: pfsense_haproxy_frontend
version_added: 0.7.0
author: Long Nguyen (@djlongy)
short_description: Manage pfSense HAProxy frontends
description:
  - Manage pfSense HAProxy frontend (listen) entries.
  - Requires the haproxy pfSense package to be installed.
notes:
options:
  name:
    description: The frontend name.
    required: true
    type: str
  status:
    description: Frontend status.
    required: false
    type: str
    choices: ['active', 'disabled']
    default: 'active'
  type:
    description: Frontend type (protocol mode).
    required: false
    type: str
    choices: ['tcp', 'http', 'ssl']
    default: 'tcp'
  backend:
    description: Default backend pool name.
    required: false
    type: str
  extaddrs:
    description:
      - List of external address bindings.
      - Each entry binds a VIP address and port to this frontend.
    required: false
    type: list
    elements: dict
    suboptions:
      address:
        description: VIP IP address (will be formatted as '{ip}_ipv4' for pfSense).
        required: true
        type: str
      port:
        description: Listen port number.
        required: true
        type: str
      ssl:
        description: SSL/TLS offloading setting (leave empty for none).
        required: false
        default: ''
        type: str
  dontlognull:
    description: Don't log connections with no data.
    default: true
    type: bool
  dontlog_normal:
    description: Don't log normal connections.
    default: true
    type: bool
  socket_stats:
    description: Enable stats socket.
    default: true
    type: bool
  max_connections:
    description: Maximum number of concurrent connections.
    required: false
    type: int
  client_timeout:
    description: Client timeout in milliseconds.
    required: false
    type: int
  state:
    description: State in which to leave the frontend.
    choices: [ "present", "absent" ]
    default: present
    type: str
"""

EXAMPLES = """
- name: Add HAProxy frontend
  pfsense_haproxy_frontend:
    name: fe_vault_8200
    type: tcp
    backend: be_vault_8200
    extaddrs:
      - address: 192.168.20.50
        port: '8200'
    state: present

- name: Remove HAProxy frontend
  pfsense_haproxy_frontend:
    name: fe_vault_8200
    state: absent
"""

RETURN = """
commands:
    description: the set of commands that would be pushed to the remote device (if pfSense had a CLI)
    returned: always
    type: list
    sample: ["create haproxy_frontend 'fe_vault_8200', backend='be_vault_8200', listen=192.168.20.50_ipv4:8200"]
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.pfsensible.core.plugins.module_utils.haproxy_frontend import (
    PFSenseHaproxyFrontendModule, HAPROXY_FRONTEND_ARGUMENT_SPEC, HAPROXY_FRONTEND_REQUIRED_IF
)


def main():
    module = AnsibleModule(
        argument_spec=HAPROXY_FRONTEND_ARGUMENT_SPEC,
        required_if=HAPROXY_FRONTEND_REQUIRED_IF,
        supports_check_mode=True)

    pfmodule = PFSenseHaproxyFrontendModule(module)
    pfmodule.run(module.params)
    pfmodule.commit_changes()


if __name__ == '__main__':
    main()
