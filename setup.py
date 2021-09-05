import setuptools

ver_globals = {}
with open("coups/version.py") as fp:
    exec(fp.read(), ver_globals)
version = ver_globals["version"]

setuptools.setup(
    name="coups",
    version=version,
    author="Brett Viren",
    author_email="brett.viren@gmail.com",
    description="Containers of UPS Products",
    url="https://brettviren.github.io/coups",
    packages=setuptools.find_packages(),
    python_requires='>=3.5',    # use of typing probably drive this
    install_requires=[
        "click",
        "networkx",
        "matplotlib",
        "sqlalchemy",
        "requests",
        "bs4",
    ],
    entry_points = dict(
        console_scripts = [
            'coups = coups.__main__:main',
        ]
    ),
    include_package_data=True,
)
