import os.path
from setuptools import setup, find_packages


def read(*parts):
    with open(os.path.join(*parts), 'rt') as f:
        return f.read().strip()


classifiers = [
    'License :: OSI Approved :: MIT License',
    'Development Status :: 3 - Alpha',
    'Programming Language :: Python',
    'Programming Language :: Python :: 3',
    'Programming Language :: Python :: 3.7',
    'Programming Language :: Python :: 3 :: Only',
    'Operating System :: OS Independent',
    'Intended Audience :: Developers',
    'Topic :: Software Development',
    'Topic :: Software Development :: Libraries',
    'Framework :: AsyncIO',
]

setup(
    name='asyncio_iter_tools',
    version='0.0.1',
    description="Asyncio tools for working with async-iterators.",
    long_description='\n\n'.join(read('README.rst'),),
    classifiers=classifiers,
    author="Alexey Popravka",
    author_email="alexey.popravka@horsedevel.com",
    url="https://github.com/popravich/asyncio_iter_tools",
    license="MIT",
    packages=find_packages(exclude=["tests"]),
)
