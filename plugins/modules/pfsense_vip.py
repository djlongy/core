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
module: pfsense_vip
version_added: 0.7.0
author: Long Nguyen
short_description: Manage pfSense virtual IPs
description:
  - Manage pfSense virtual IPs (ipalias, carp, proxyarp, other)
notes:
options:
  subnet:
    description: Virtual IP address. Used as the unique identifier.
    required: true
    type: str
  subnet_bits:
    description: CIDR prefix length.
    required: false
    type: int
  descr:
    description: Virtual IP description.
    required: false
    default: ''
    type: str
  mode:
    description: Virtual IP mode.
    required: false
    choices: [ "ipalias", "carp", "proxyarp", "other" ]
    type: str
  interface:
    description: Interface for the virtual IP.
    required: false
    type: str
  type:
    description: Address type.
    required: false
    choices: [ "single", "network" ]
    default: single
    type: str
  noexpand:
    description: Disable expansion of this entry into IPs on NAT lists.
    required: false
    type: bool
  vhid:
    description: VHID group (1-255). Required for CARP mode. Must be unique per interface.
    required: false
    type: int
  advbase:
    description: CARP advertising frequency base (1-254 seconds).
    required: false
    type: int
  advskew:
    description: CARP advertising frequency skew (0-254).
    required: false
    type: int
  password:
    description: CARP virtual IP password. Required for CARP mode.
    required: false
    type: str
  state:
    description: State in which to leave the virtual IP.
    choices: [ "present", "absent" ]
    default: present
    type: str
"""

EXAMPLES = """
- name: Add IP alias VIP
  pfsense_vip:
    subnet: 192.168.1.100
    subnet_bits: 32
    descr: webserver_vip
    mode: ipalias
    interface: lan
    state: present

- name: Add CARP VIP
  pfsense_vip:
    subnet: 10.0.0.100
    subnet_bits: 32
    descr: ha_vip
    mode: carp
    interface: wan
    vhid: 1
    advbase: 1
    advskew: 0
    password: carppass
    state: present

- name: Remove VIP
  pfsense_vip:
    subnet: 192.168.1.100
    state: absent
"""

RETURN = """
commands:
    description: the set of commands that would be pushed to the remote device (if pfSense had a CLI)
    returned: always
    type: list
    sample: ["create vip '192.168.1.100', mode='ipalias', interface='lan', subnet_bits='32'"]
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.pfsensible.core.plugins.module_utils.vip import PFSenseVIPModule, VIP_ARGUMENT_SPEC, VIP_REQUIRED_IF


def main():
    module = AnsibleModule(
        argument_spec=VIP_ARGUMENT_SPEC,
        required_if=VIP_REQUIRED_IF,
        supports_check_mode=True)

    pfmodule = PFSenseVIPModule(module)
    pfmodule.run(module.params)
    pfmodule.commit_changes()


if __name__ == '__main__':
    main()
