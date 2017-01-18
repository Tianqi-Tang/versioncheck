from __future__ import unicode_literals

from setuptools import setup, find_packages


def read_requirements(filename):
    with open(filename) as f:
        return f.read().splitlines()


def readme():
    open('README.rst').read()

setup(
    name='versioncheck',
    version='0.0.1',
    author="Tina Tang",
    author_email="tina.tang@emc.com",
    description="Version check decorator",
    license="Apache Software License",
    keywords="version checker",
    long_description=readme(),
    packages=find_packages(),
    platforms=['any'],
    classifiers=[
        "Programming Language :: Python",
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        "Natural Language :: English",
        "Intended Audience :: Developers",
        "Operating System :: OS Independent",
        "Development Status :: 4 - Beta",
        "Topic :: Utilities",
        "License :: OSI Approved :: Apache Software License",
    ],
    install_requires=read_requirements('requirements.txt'),
    tests_require=read_requirements('test-requirements.txt')
)