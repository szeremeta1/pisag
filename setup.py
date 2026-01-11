from setuptools import find_packages, setup

setup(
    name='pisag',
    version='0.1.0',
    description='POCSAG Pager Server for HackRF',
    author='PISAG Project',
    packages=find_packages(),
    install_requires=[
        'Flask>=3.0.0',
        'Flask-SocketIO>=5.3.5',
        'Flask-SQLAlchemy>=3.1.1',
        'Flask-CORS>=4.0.0',
        'SQLAlchemy>=2.0.23',
        'alembic>=1.13.0',
        'numpy>=1.24.3',
        'eventlet>=0.33.3',
        'python-dotenv>=1.0.0',
        'bitstring>=4.1.4',
    ],
    python_requires='>=3.9',
    entry_points={
        'console_scripts': [
            'pisag=pisag.app:main',
        ],
    },
)
