from setuptools import setup, find_packages
from flask_websub import __version__

with open('README.md', encoding='UTF-8') as f:
    description = f.read()

setup(
    name='Flask-WebSub',
    version=__version__,
    url='https://github.com/marten-de-vries/Flask-WebSub',
    license='ISC',
    author='Marten de Vries',
    author_email='m@rtendevri.es',
    description='A WebSub hub, publisher and subscriber using Flask',
    long_description=description,
    packages=find_packages(),
    zip_safe=False,
    platforms='any',
    install_requires=['Flask', 'requests'],
    extras_require={
        'celery': ['celery'],
        'redis': ['redis'],
        'dev': [
            'flake8',
            'pytest-cov',
            'pytest',
            'Sphinx-PyPI-upload',
            'Sphinx',
        ],
    },
    classifiers=[
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: ISC License (ISCL)',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ]
)
