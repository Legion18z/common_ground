from setuptools import setup


def find_required() -> list[str]:
    with open("requirements.txt") as f:
        return f.read().splitlines()


def get_version(filename='common_ground/version') -> str:
    return open(filename, "r").read().strip()


setup(
    name="common_ground",
    version=get_version(),
    description="Library for generating d42 schema builders from OpenAPI specifications",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="Andrey Maslov",
    author_email="legionus18z@gmail.com",
    python_requires=">=3.7",
    url="https://github.com/Legion18z/common_ground",
    license="Apache-2.0",
    packages=['common_ground'],
    install_requires=find_required(),
    classifiers=[
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 3.10",
        "Typing :: Typed",
    ],
    package_data={
        'common_ground': ['version'],
    },
)
