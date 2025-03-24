from setuptools import setup, find_packages

setup(
    name="minecraft-telegram-bot",
    version="0.1.0",
    packages=find_packages(),
    py_modules=["bot"],
    entry_points={
        "console_scripts": [
            "minecraft-telegram-bot=bot:main",
        ],
    },
)