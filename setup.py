"""
This project bridges PyXLL and Jupyter Notebooks.

It enables Excel add-ins to be written in Python using PyXLL, but
for the Python code to be executed in an IPython kernel running
on a Jupyter Notebook server.

For details about PyXLL, see https://www.pyxll.com.
"""
import setuptools

setuptools.setup(
    name="pyxll-notebook",
    version="0.1",
    author="PyXLL Ltd",
    author_email="info@pyxll.com",
    long_description=open("README.md").read(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    packages=setuptools.find_packages(),
    include_package_data=True,
    zip_safe=False,
    package_data={
        "": ["*.cfg", "*.xml", "*.png"],
    },
    extras_require={
        "client":  ["websockets", "aiohttp"],
        "server": ["ipykernel"],
    }
)
