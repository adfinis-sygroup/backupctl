#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""Test for class backupctl"""

import os

import pytest

from backupctl import backupctl, history


@pytest.fixture(autouse=True)
def hist():
    hist_obj = history.History(os.path.join(
        os.sep,
        'tmp',
        'backupctl',
        'backupctl.db',
    ))
    return hist_obj


mock_data = {
    'zfs-create':   (0, '', ''),
    'zfs-resize':   (0, '', ''),
    'zfs-destroy':  (0, '', ''),
    'zfs-get':      (0, '0', ''),
    'zfs-set':      (0, '', ''),
}


@pytest.fixture()
def mock_zfs(mocker):
    commands = []

    def mocked(cmd):
        commands.append(cmd)
        return mock_data['-'.join(cmd[:2])]
    mocker.patch('backupctl.zfs.execute_cmd', mocked)
    yield commands


@pytest.mark.parametrize("parameters, exit_code", [
    ([],                                                                    2),
    (['new'],                                                               1),
    (['new', '-n', 'customer1'],                                            1),
    (['new', '-n', 'customer1', '-s', '10M'],                               0),
    (['new', '-n', 'customer1', '-v', 'www.example.com'],                   0),
    (['new', '-n', 'customer1', '-v', 'www.example.com', '-s', '10M'],      0),
    (['resize'],                                                            1),
    (['resize', '-n', 'customer1'],                                         1),
    (['resize', '-n', 'customer1', '-s', '10M'],                            0),
    (['resize', '-n', 'customer1', '-v', 'www.example.com'],                1),
    (['resize', '-n', 'customer1', '-v', 'www.example.com', '-s', '10M'],   0),
    (['remove'],                                                            1),
    (['remove', '-n', 'customer1'],                                         0),
    (['remove', '-n', 'customer1', '-v', 'www.example.com'],                0),
    (['log'],                                                               0),
    (['test'],                                                              1),
])
def test_main(parameters, exit_code, mocker, mock_zfs):
    mocker.patch('sys.argv', [
        'backupctl.py',
    ] + parameters)

    def mocked():
        import configparser
        cfg = configparser.ConfigParser()
        cfg['database'] = {
            'path': os.path.join(
                os.sep,
                'tmp',
                'backupctl',
                'backupctl.db',
            )
        }
        cfg['zfs'] = {
            'pool': 'backup',
            'root': os.path.join(
                os.sep,
                'tmp',
                'backupctl',
                'backup',
            )
        }
        return cfg

    mocker.patch('backupctl.backupctl.config', mocked)
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        backupctl.main()
    assert pytest_wrapped_e.type == SystemExit
    assert pytest_wrapped_e.value.code == exit_code


def test_config():
    cfg = backupctl.config()
    import configparser
    assert type(cfg) == configparser.ConfigParser
    assert type(cfg['database']['path']) == str
    assert type(cfg['zfs']['pool']) == str
    assert type(cfg['zfs']['root']) == str


def test_customer(mock_zfs):
    backupctl.new(
        hist(),
        pool='backup',
        root=os.path.join(os.sep, 'tmp', 'backupctl', 'backup'),
        customer='customer1',
        size='1G',
        client=None,
    )
    backupctl.resize(
        hist(),
        pool='backup',
        customer='customer1',
        size='2G',
    )
    backupctl.remove(
        hist(),
        pool='backup',
        customer='customer1',
    )
    assert mock_zfs == [
        [
            'zfs',
            'create',
            '-o',
            'compression=on',
            '-o',
            'dedup=off',
            '-o',
            'quota=1G',
            '-o',
            'mountpoint={0}'.format(os.path.join(
                os.sep,
                'tmp',
                'backupctl',
                'backup',
                'customer1',
            )),
            'backup/customer1',
        ],
        [
            'zfs',
            'get',
            '-H',
            '-o',
            'value',
            '-p',
            'used',
            'backup/customer1',
        ],
        [
            'zfs',
            'set',
            'quota=2G',
            'backup/customer1',
        ],
        [
            'zfs',
            'set',
            'mountpoint=none',
            'backup/customer1',
        ],
        [
            'zfs',
            'destroy',
            '-r',
            '-f',
            'backup/customer1',
        ],
    ]


def test_vault(mock_zfs):
    backupctl.new(
        hist(),
        pool='backup',
        root=os.path.join(os.sep, 'tmp', 'backupctl', 'backup'),
        customer='customer1',
        size='1G',
        client=None,
    )
    backupctl.new(
        hist(),
        pool='backup',
        root=os.path.join(os.sep, 'tmp', 'backupctl', 'backup'),
        customer='customer1',
        vault='www.example.com',
        size='500M',
        client=None,
    )
    backupctl.new(
        hist(),
        pool='backup',
        root=os.path.join(os.sep, 'tmp', 'backupctl', 'backup'),
        customer='customer1',
        vault='mail.example.com',
        size='500M',
        client='192.0.2.1',
    )
    backupctl.resize(
        hist(),
        pool='backup',
        customer='customer1',
        vault='mail.example.com',
        size='200M',
    )
    backupctl.remove(
        hist(),
        pool='backup',
        customer='customer1',
        vault='mail.example.com',
    )
    backupctl.remove(
        hist(),
        pool='backup',
        customer='customer1',
    )
    assert mock_zfs == [
        [
            'zfs',
            'create',
            '-o',
            'compression=on',
            '-o',
            'dedup=off',
            '-o',
            'quota=1G',
            '-o',
            'mountpoint={0}'.format(os.path.join(
                os.sep,
                'tmp',
                'backupctl',
                'backup',
                'customer1',
            )),
            'backup/customer1',
        ],
        [
            'zfs',
            'create',
            '-o',
            'compression=on',
            '-o',
            'dedup=off',
            '-o',
            'quota=500M',
            '-o',
            'mountpoint={0}'.format(os.path.join(
                os.sep,
                'tmp',
                'backupctl',
                'backup',
                'customer1',
                'www.example.com',
            )),
            'backup/customer1/www.example.com',
        ],
        [
            'zfs',
            'create',
            '-o',
            'compression=on',
            '-o',
            'dedup=off',
            '-o',
            'quota=500M',
            '-o',
            'mountpoint={0}'.format(os.path.join(
                os.sep,
                'tmp',
                'backupctl',
                'backup',
                'customer1',
                'mail.example.com',
            )),
            'backup/customer1/mail.example.com',
        ],
        [
            'zfs',
            'get',
            '-H',
            '-o',
            'value',
            '-p',
            'used',
            'backup/customer1/mail.example.com',
        ],
        [
            'zfs',
            'set',
            'quota=200M',
            'backup/customer1/mail.example.com',
        ],
        [
            'zfs',
            'set',
            'mountpoint=none',
            'backup/customer1/mail.example.com',
        ],
        [
            'zfs',
            'destroy',
            '-r',
            '-f',
            'backup/customer1/mail.example.com',
        ],
        [
            'zfs',
            'set',
            'mountpoint=none',
            'backup/customer1',
        ],
        [
            'zfs',
            'destroy',
            '-r',
            '-f',
            'backup/customer1',
        ],
    ]


@pytest.mark.xfail
def test_new_no_customer():
    backupctl.new(
        hist(),
        customer=None,
        vault=None,
        size=None,
        client=None,
    )


@pytest.mark.xfail
def test_new_no_vault_or_size():
    backupctl.new(
        hist(),
        customer='customer1',
        vault=None,
        size=None,
        client=None,
    )


@pytest.mark.xfail
def test_resize_no_customer():
    backupctl.resize(
        hist(),
        customer=None,
        vault=None,
        size=None,
    )


@pytest.mark.xfail
def test_resize_no_size():
    backupctl.resize(
        hist(),
        customer='customer1',
        vault=None,
        size=None,
    )


@pytest.mark.xfail
def test_remove_no_customer():
    backupctl.remove(
        hist(),
        customer=None,
        vault=None,
    )


def test_history_show():
    backupctl.history_show(hist())
