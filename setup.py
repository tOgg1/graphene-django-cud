import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="graphene-django-cud",
    version="0.0.7",
    author="Tormod Haugland",
    author_email="tormod.haugland@gmail.com",
    description="Create, update and delete mutations for graphene-django",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://gitlab.com/t.-haugland-consulting-as/graphene-django-cud",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent"
    ]
)
