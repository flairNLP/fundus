from setuptools import find_packages, setup

with open("requirements.txt") as f:
    required = f.read().splitlines()

setup(
    name="fundus",
    version="0.0.1",
    description="A very simple news crawler",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    author="Max Dallabetta",
    author_email="max.dallabetta@gmail.com",
    url="https://github.com/flairNLP/fundus",
    packages=find_packages(where="src"),  # same as name
    package_dir={"": "src"},
    include_package_data=True,
    license="MIT",
    install_requires=required,
    python_requires=">=3.8",
)
