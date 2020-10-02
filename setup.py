from pathlib import Path
from setuptools import setup, find_packages

from jobfunnel import __version__ as version


description = 'Automated tool for scraping job postings.'
url = 'https://github.com/PaulMcInnis/JobFunnel'
requires = [
    'beautifulsoup4>=4.6.3',
    'lxml>=4.2.4',
    'requests>=2.19.1',
    'python-dateutil>=2.8.0',
    'PyYAML>=5.1',
    'scikit-learn>=0.21.2',
    'nltk>=3.4.1',
    'scipy>=1.4.1',
    'pytest>=5.3.1',
    'pytest-mock>=3.1.1',
    'selenium>=3.141.0',
    'webdriver-manager>=2.4.0',
    'Cerberus>=1.3.2',
    'tqdm>=4.47.0',
]
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
    python_requires='>=3.8.0',
    install_requires=requires,
    packages=find_packages(exclude=('tests', 'docs', 'images')),
    include_package_data=True,
    entry_points={'console_scripts': ['funnel = jobfunnel.__main__:main']},
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
    ],
)
