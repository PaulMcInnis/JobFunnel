from setuptools import setup, find_packages
from pipenv.project import Project
from pipenv.utils import convert_deps_to_pip

from jobfunnel import __version__ as version

description = 'Automated tool for scraping job postings.'
url = 'https://github.com/PaulMcInnis/JobFunnel'
pfile = Project(chdir=False).parsed_pipfile
requires = convert_deps_to_pip(pfile['packages'], r=False)
dev_requires = convert_deps_to_pip(pfile['dev-packages'], r=False)

with open('readme.md', 'r') as f:
    readme = f.read()

setup(
    name             = 'JobFunnel',
    version          = version,
    description      = description,
    long_description = readme,
    author           = 'Paul McInnis, Bradley Kohler, Jose Alarcon',
    author_email     = 'paulmcinnis99@gmail.com',
    url              = url,
    license          = 'MIT License',
    python_requires  = '>=3.6.0',
    install_requires = requires,
    packages         = find_packages(exclude=('demo',)),
    entry_points     = {'console_scripts': ['funnel = jobfunnel.__main__:main']})
