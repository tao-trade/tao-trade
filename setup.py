from setuptools import setup, find_packages

setup(
    name="taotrade",
    version="0.1.0",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "ariadne>=0.23.0",
        "fastapi>=0.115.4",
        "flask>=3.0.3",
        "matplotlib>=3.9.2",
        "numpy>=2.1.3",
        "pandas>=2.2.3",
        "pillow>=11.0.0",
        "pydantic>=2.9.2",
        "strawberry-graphql>=0.248.1",
        "uvicorn>=0.32.0",
    ],
    entry_points={
        "console_scripts": [
            "taotrade=taotrade.cli:main",
        ],
    },
)
