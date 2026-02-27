from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="amazon-catalog-cli",
    version="1.2.0",
    author="Brett Bohannon",
    description="Catalog CLI Light - Free CLI for querying Amazon Category Listing Reports",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/BWB03/amazon-catalog-cli",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
    python_requires=">=3.7",
    install_requires=[
        "openpyxl>=3.0.0",
        "click>=8.0.0",
        "rich>=13.0.0",
    ],
    entry_points={
        "console_scripts": [
            "catalog=catalog.cli:cli",
        ],
    },
)
