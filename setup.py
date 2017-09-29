#!/usr/bin/env python2

# python setup.py sdist --format=zip,gztar

from setuptools import setup
import os
import sys
import platform
import imp
import argparse

version = imp.load_source('version', 'lib/version.py')

if sys.version_info[:3] < (2, 7, 0):
    sys.exit("Error: Electrum requires Python version >= 2.7.0...")

data_files = []

if platform.system() in ['Linux', 'FreeBSD', 'DragonFly']:
    parser = argparse.ArgumentParser()
    parser.add_argument('--root=', dest='root_path', metavar='dir', default='/')
    opts, _ = parser.parse_known_args(sys.argv[1:])
    usr_share = os.path.join(sys.prefix, "share")
    if not os.access(opts.root_path + usr_share, os.W_OK) and \
       not os.access(opts.root_path, os.W_OK):
        if 'XDG_DATA_HOME' in os.environ.keys():
            usr_share = os.environ['XDG_DATA_HOME']
        else:
            usr_share = os.path.expanduser('~/.local/share')
    data_files += [
        (os.path.join(usr_share, 'applications/'), ['electrum-rubycoin.desktop']),
        (os.path.join(usr_share, 'pixmaps/'), ['icons/electrum-rubycoin.png'])
    ]

setup(
    name="Electrum-Rubycoin",
    version=version.ELECTRUM_VERSION,
    install_requires=[
        'slowaes>=0.1a1',
        'ecdsa>=0.9',
        'pbkdf2',
        'requests',
        'qrcode',
        'protobuf',
        'dnspython',
        'jsonrpclib',
    ],
    packages=[
        'electrum_rubycoin',
        'electrum_rubycoin_gui',
        'electrum_rubycoin_gui.qt',
        'electrum_rubycoin_plugins',
        'electrum_rubycoin_plugins.audio_modem',
        'electrum_rubycoin_plugins.cosigner_pool',
        'electrum_rubycoin_plugins.email_requests',
        'electrum_rubycoin_plugins.exchange_rate',
        'electrum_rubycoin_plugins.hw_wallet',
        'electrum_rubycoin_plugins.keepkey',
        'electrum_rubycoin_plugins.labels',
        'electrum_rubycoin_plugins.ledger',
        'electrum_rubycoin_plugins.plot',
        'electrum_rubycoin_plugins.trezor',
        'electrum_rubycoin_plugins.virtualkeyboard',
    ],
    package_dir={
        'electrum_rubycoin': 'lib',
        'electrum_rubycoin_gui': 'gui',
        'electrum_rubycoin_plugins': 'plugins',
    },
    package_data={
        'electrum_rubycoin': [
            'www/index.html',
            'wordlist/*.txt',
            'locale/*/LC_MESSAGES/electrum.mo',
        ]
    },
    scripts=['electrum-rubycoin'],
    data_files=data_files,
    description="Lightweight rubycoin Wallet",
    author="dev0tion",
    license="MIT Licence",
    url="http://www.rubycoin.org",
    long_description="""Lightweight rubycoin Wallet"""
)
