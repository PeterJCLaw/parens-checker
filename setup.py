from pathlib import Path

from setuptools import setup, find_packages  # type: ignore[import]

long_description = (Path(__file__).parent / 'README.md').read_text()

setup(
    name='parens-checker',
    version='0.1.2',
    url='https://github.com/PeterJCLaw/parens-checker',
    project_urls={
        'Issue tracker': 'https://github.com/PeterJCLaw/parens-checker/issues',
    },
    description="A tool for detecting badly wrapped bracketed blocks in Python",
    long_description=long_description,
    long_description_content_type='text/markdown',

    packages=find_packages(exclude=['tests']),

    author="Peter Law",
    author_email="PeterJCLaw@gmail.com",

    classifiers=(
        'Development Status :: 2 - Pre-Alpha',
        'Environment :: Console',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Topic :: Software Development',
    ),
)
