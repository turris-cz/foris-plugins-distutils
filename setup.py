#!/usr/bin/env python

from setuptools import setup

setup(
    name="Foris Plugins Distutils",
    version="0.3",
    description="Distutils patches to add commands for foris plugin handling",
    author="CZ.NIC, z. s. p. o.",
    author_email="stepan.henek@nic.cz",
    url="https://gitlab.labs.nic.cz/turris/foris-plugins-distutils/",
    license="GPL-3.0",
    requires=[],
    install_requires=["babel", "jinja2", "libsass"],
    provides=["foris_plugins_distutils"],
    packages=["foris_plugins_distutils"],
    entry_points={
        "distutils.commands": [
            "foris_make_messages = foris_plugins_distutils:make_messages",
            "foris_clean = foris_plugins_distutils:clean",
            "foris_build = foris_plugins_distutils:build",
        ]
    },
)
