import os
from distutils.core import setup

setup(
    name = "mhub",
    version = "0.04",
    author = "JingleManSweep",
    author_email = "jinglemansweep@gmail.com",
    description = "AMQP Based Home Automation Framework",
    url = "http://github.com/jingleman/MHub",
    packages = ["mhub", "mhub.plugins", "twisted.plugins"],
    scripts = []
)
