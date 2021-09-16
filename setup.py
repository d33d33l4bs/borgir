import setuptools

from pathlib import Path


def read_file(relative_path):
    abs_path = Path(__file__).parent.joinpath(relative_path)
    return abs_path.read_text()


setuptools.setup(
    name="borgir",
    version=read_file("version"),
    author="Borgir",
    description="A dummy Discord bot",
    package_dir={"": "src"},
    packages=setuptools.find_packages(where="src"),
    install_requires=[
        "youtube-dl==2021.6.6",
        "discord.py==1.7.3"
    ],
    entry_points={
        'console_scripts': [
            'borgir = borgir.__main__:main',
        ],
    },
)