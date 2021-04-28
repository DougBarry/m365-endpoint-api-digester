from setuptools import setup, find_packages
from m365digester import APP_VERSION


def read(filename):
    with open(filename) as f:
        return f.read()


setup(
    name='m365-endpoint-api-digester',
    version=APP_VERSION,
    maintainer='dougbarry',
    maintainer_email='github@gtko.co.uk',
    description='Query the M365 API for endpoint information and generate outputs',
    long_description=read('README.md'),
    long_description_content_type='text/markdown',
    url='https://github.com/dougbarry/m365-endpoint-api-digester',
    license='MIT',
    classifiers=['Programming Language :: Python',
                 'Programming Language :: Python :: 3.6',
                 'Programming Language :: Python :: 3.7'],
    packages=find_packages(),
    scripts=['m365digester-cli'],
    install_requires=None,
    python_requires='>=3.6.2'
)
