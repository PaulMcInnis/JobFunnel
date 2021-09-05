from pathlib import Path
from setuptools import setup, find_packages

from jobfunnel import __version__ as version


description = 'Automated tool for scraping job postings.'
url = 'https://github.com/PaulMcInnis/JobFunnel'
with open("requirements.txt") as req:
    requires = [line.strip() for line in req if line and "#" not in line]
here = Path(__file__).parent
readme = (here / "readme.md").read_text()

setup(
    name='JobFunnel',
    version=version,
    description=description,
    long_description=readme,
    long_description_content_type='text/markdown',
    author='Paul McInnis, Bradley Kohler, Jose Alarcon, Erich Mengore, '
    'Mark van der Broek',
    author_email='paulmcinnis99@gmail.com',
    url=url,
    license='MIT License',
    python_requires='>=3.9.0',
    install_requires=requires,
    packages=find_packages(exclude=('tests', 'docs', 'images')),
    include_package_data=True,
    entry_points={'console_scripts': ['funnel = jobfunnel.__main__:main']},
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
    ],
)
