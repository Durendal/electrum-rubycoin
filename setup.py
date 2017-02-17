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
        (os.path.join(usr_share, 'applications/'), ['electrum-stratis.desktop']),
        (os.path.join(usr_share, 'pixmaps/'), ['icons/electrum-stratis.png'])
    ]

setup(
    name="Electrum-Stratis",
    version=version.ELECTRUM_VERSION,
    install_requires=[
        'pyaes',
        'ecdsa>=0.9',
        'pbkdf2',
        'requests',
        'qrcode',
        'protobuf',
        'dnspython',
        'jsonrpclib',
    ],
    packages=[
        'electrum_stratis',
        'electrum_stratis_gui',
        'electrum_stratis_gui.qt',
        'electrum_stratis_plugins',
        'electrum_stratis_plugins.audio_modem',
        'electrum_stratis_plugins.cosigner_pool',
        'electrum_stratis_plugins.email_requests',
        'electrum_stratis_plugins.exchange_rate',
        'electrum_stratis_plugins.hw_wallet',
        'electrum_stratis_plugins.keepkey',
        'electrum_stratis_plugins.labels',
        'electrum_stratis_plugins.ledger',
        'electrum_stratis_plugins.plot',
        'electrum_stratis_plugins.trezor',
        'electrum_stratis_plugins.digitalbitbox',
        'electrum_stratis_plugins.virtualkeyboard',
    ],
    package_dir={
        'electrum_stratis': 'lib',
        'electrum_stratis_gui': 'gui',
        'electrum_stratis_plugins': 'plugins',
    },
    package_data={
        'electrum_stratis': [
            'currencies.json',
            'www/index.html',
            'wordlist/*.txt',
            'locale/*/LC_MESSAGES/electrum.mo',
        ]
    },
    scripts=['electrum-stratis'],
    data_files=data_files,
    description="Lightweight Stratis Wallet",
    author="dev0tion",
    license="MIT Licence",
    url="http://www.stratisplatform.com",
    long_description="""Lightweight Stratis Wallet"""
)
