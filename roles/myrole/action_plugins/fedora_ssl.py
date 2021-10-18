#!/usr/bin/python
# Make coding more python3-ish, this is required for contributions to Ansible
from pathlib import Path

from ansible.plugins.action import ActionBase


class ActionModule(ActionBase):
    def run(self, tmp=None, task_vars=None):
        super(ActionModule, self).run(tmp, task_vars)

        output = {
            'changed': False,
            'failed': False,
            'skipped': False,
            'msg': ''
        }

        module_args = self._task.args.copy()
        key_size = module_args.get('key_size', 4098)
        cn = module_args.get('cn', 'getfedora.org')
        dest = module_args.get('dest')

        # run setup module to gather ansible play variables
        self._execute_module(
            module_name='setup',
            module_args=module_args,
            task_vars=task_vars, tmp=tmp
        )

        tmpdir = self._connection._shell.tmpdir
        basedir = f'{tmpdir}certs'
        Path(basedir).mkdir(parents=True, exist_ok=True)
        Path(dest).mkdir(parents=True, exist_ok=True)

        pkey = self._execute_module(
            'ansible.builtin.openssl_privatekey',
            module_args=dict(
                path=f'{basedir}/key.pem',
                size=key_size
            ),
            task_vars=task_vars
        )
        if pkey.get('failed') is True:
            return pkey

        csr = self._execute_module(
        'ansible.builtin.openssl_csr',
            module_args=dict(
                path=f'{basedir}/request.csr',
                privatekey_path=pkey['filename'],
                common_name=cn
            ),
            task_vars=task_vars
        )
        if csr.get('failed') is True:
            return csr

        cert = self._execute_module(
            'ansible.builtin.openssl_certificate',
            module_args=dict(
                path=f'{basedir}/cert.pem',
                csr_path=csr['filename'],
                privatekey_path=pkey['filename'],
                provider='selfsigned'
            ),
            task_vars=task_vars
        )
        
        if cert.get('failed') is True:
            return cert

        for item in [pkey, csr, cert]:
            fname = item['filename'].split('/')[-1]
            cp = self._execute_module(
                'ansible.builtin.copy',
                module_args=dict(
                    src=item['filename'],
                    dest=f'{dest}/{fname}'
                ),
                task_vars=task_vars
            )
            if cp.get('failed') is True:
                return cp
                
        output['changed'] = True
        output['msg'] = 'Success'
        output['result'] = {
            'pkey': pkey,
            'csr': csr,
            'cert': cert,
            'dest': dest
        }
        
        return output

