#!/usr/bin/env python

"""setuptools module for contract_wrappers package."""

import subprocess  # nosec
from shutil import copy, rmtree
from os import environ, path, remove
from pathlib import Path
from sys import argv
from importlib.util import find_spec

from distutils.command.clean import clean
import distutils.command.build_py
from setuptools import find_packages, setup
from setuptools.command.test import test as TestCommand


BLACK_COMMAND = "black --line-length 79 "


CONTRACTS_TO_BE_WRAPPED = [
    "asset_proxy_owner",
    "coordinator",
    "coordinator_registry",
    "dummy_erc20_token",
    "dummy_erc721_token",
    "dutch_auction",
    "erc20_proxy",
    "erc20_token",
    "erc721_proxy",
    "erc721_token",
    "eth_balance_checker",
    "exchange",
    "forwarder",
    "i_asset_proxy",
    "i_validator",
    "i_wallet",
    "multi_asset_proxy",
    "order_validator",
    "weth9",
    "zrx_token",
]


class PreInstallCommand(distutils.command.build_py.build_py):
    """Custom setuptools command class for pulling in generated code."""

    description = "Pull in code generated by TypeScript"

    def run(self):
        """Copy files from TS build area to local src, & `black` them."""
        pkgdir = path.dirname(path.realpath(argv[0]))
        for contract in CONTRACTS_TO_BE_WRAPPED:
            copy(
                path.join(
                    pkgdir,
                    "..",
                    "..",
                    "packages",
                    "python-contract-wrappers",
                    "generated",
                    contract,
                    "__init__.py",
                ),
                path.join(
                    pkgdir, "src", "zero_ex", "contract_wrappers", contract
                ),
            )
            copy(
                path.join(
                    pkgdir,
                    "..",
                    "..",
                    "packages",
                    "python-contract-wrappers",
                    "generated",
                    contract,
                    "__init__.py",
                ),
                path.join(
                    pkgdir, "src", "zero_ex", "contract_wrappers", contract
                ),
            )
        if find_spec("black") is None:
            subprocess.check_call("pip install black".split())  # nosec
        black_command = BLACK_COMMAND + " ".join(
            [
                f"src/zero_ex/contract_wrappers/{contract}/__init__.py"
                for contract in CONTRACTS_TO_BE_WRAPPED
            ]
        )
        print(f"Running command `{black_command}`...")
        subprocess.check_call(black_command.split())  # nosec


class TestCommandExtension(TestCommand):
    """Run pytest tests."""

    def run_tests(self):
        """Invoke pytest."""
        import pytest

        exit(pytest.main(["--doctest-modules", "-rapP"]))
        #        show short test summary at end ^


class LintCommand(distutils.command.build_py.build_py):
    """Custom setuptools command class for running linters."""

    description = "Run linters"

    def run(self):
        """Run linter shell commands."""
        lint_commands = [
            # formatter:
            (BLACK_COMMAND + " --check --diff src test setup.py").split(),
            # style guide checker (formerly pep8):
            "pycodestyle src test setup.py".split(),
            # docstring style checker:
            "pydocstyle src test setup.py".split(),
            # static type checker:
            "mypy src test setup.py".split(),
            # security issue checker:
            "bandit -r src ./setup.py".split(),
            # general linter:
            "pylint src test setup.py".split(),
            # pylint takes relatively long to run, so it runs last, to enable
            # fast failures.
        ]

        # tell mypy where to find interface stubs for 3rd party libs
        environ["MYPYPATH"] = path.join(
            path.dirname(path.realpath(argv[0])), "stubs"
        )

        # HACK(gene): until eth_utils fixes
        # https://github.com/ethereum/eth-utils/issues/140 , we need to simply
        # create an empty file `py.typed` in the eth_abi package directory.
        import eth_utils

        eth_utils_dir = path.dirname(path.realpath(eth_utils.__file__))
        Path(path.join(eth_utils_dir, "py.typed")).touch()

        for lint_command in lint_commands:
            print(
                "Running lint command `", " ".join(lint_command).strip(), "`"
            )
            subprocess.check_call(lint_command)  # nosec


class CleanCommandExtension(clean):
    """Custom command to do custom cleanup."""

    def run(self):
        """Run the regular clean, followed by our custom commands."""
        super().run()
        rmtree("dist", ignore_errors=True)
        rmtree(".mypy_cache", ignore_errors=True)
        rmtree(".tox", ignore_errors=True)
        rmtree(".pytest_cache", ignore_errors=True)
        rmtree("src/0x_contract_wrappers.egg-info", ignore_errors=True)
        # generated files:
        for contract in CONTRACTS_TO_BE_WRAPPED:
            try:
                remove(f"src/zero_ex/contract_wrappers/{contract}/__init__.py")
            except FileNotFoundError:
                pass


class TestPublishCommand(distutils.command.build_py.build_py):
    """Custom command to publish to test.pypi.org."""

    description = (
        "Publish dist/* to test.pypi.org. Run sdist & bdist_wheel first."
    )

    def run(self):
        """Run twine to upload to test.pypi.org."""
        subprocess.check_call(  # nosec
            (
                "twine upload --repository-url https://test.pypi.org/legacy/"
                + " --verbose dist/*"
            ).split()
        )


class PublishCommand(distutils.command.build_py.build_py):
    """Custom command to publish to pypi.org."""

    description = "Publish dist/* to pypi.org. Run sdist & bdist_wheel first."

    def run(self):
        """Run twine to upload to pypi.org."""
        subprocess.check_call("twine upload dist/*".split())  # nosec


class PublishDocsCommand(distutils.command.build_py.build_py):
    """Custom command to publish docs to S3."""

    description = (
        "Publish docs to "
        + "http://0x-contract-wrappers-py.s3-website-us-east-1.amazonaws.com/"
    )

    def run(self):
        """Run npm package `discharge` to build & upload docs."""
        subprocess.check_call("discharge deploy".split())  # nosec


class GanacheCommand(distutils.command.build_py.build_py):
    """Custom command to publish to pypi.org."""

    description = "Run ganache daemon to support tests."

    def run(self):
        """Run ganache."""
        cmd_line = (
            "docker run -d -p 8545:8545 0xorg/ganache-cli:2.2.2"
        ).split()
        subprocess.call(cmd_line)  # nosec


with open("README.md", "r") as file_handle:
    README_MD = file_handle.read()


setup(
    name="0x-contract-wrappers",
    version="1.0.3",
    description="Python wrappers for 0x smart contracts",
    long_description=README_MD,
    long_description_content_type="text/markdown",
    url=(
        "https://github.com/0xproject/0x-monorepo/tree/development"
        + "/python-packages/contract_wrappers"
    ),
    author="F. Eugene Aumson",
    author_email="feuGeneA@users.noreply.github.com",
    cmdclass={
        "clean": CleanCommandExtension,
        "pre_install": PreInstallCommand,
        "lint": LintCommand,
        "test": TestCommandExtension,
        "test_publish": TestPublishCommand,
        "publish": PublishCommand,
        "publish_docs": PublishDocsCommand,
        "ganache": GanacheCommand,
    },
    install_requires=[
        "0x-contract-addresses",
        "0x-contract-artifacts",
        "0x-json-schemas",
        "0x-order-utils",
        "web3",
        "attrs",
        "eth_utils",
        "mypy_extensions",
    ],
    extras_require={
        "dev": [
            "bandit",
            "black",
            "coverage",
            "coveralls",
            "mypy",
            "mypy_extensions",
            "pycodestyle",
            "pydocstyle",
            "pylint",
            "pytest",
            "sphinx",
            "sphinx-autodoc-typehints",
            "tox",
            "twine",
        ]
    },
    python_requires=">=3.6, <4",
    package_data={"zero_ex.contract_wrappers": ["py.typed"]},
    package_dir={"": "src"},
    license="Apache 2.0",
    keywords=(
        "ethereum cryptocurrency 0x decentralized blockchain dex exchange"
    ),
    namespace_packages=["zero_ex"],
    packages=find_packages("src"),
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Intended Audience :: Developers",
        "Intended Audience :: Financial and Insurance Industry",
        "License :: OSI Approved :: Apache Software License",
        "Natural Language :: English",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Office/Business :: Financial",
        "Topic :: Other/Nonlisted Topic",
        "Topic :: Security :: Cryptography",
        "Topic :: Software Development :: Libraries",
        "Topic :: Utilities",
    ],
    zip_safe=False,  # required per mypy
    command_options={
        "build_sphinx": {
            "source_dir": ("setup.py", "src"),
            "build_dir": ("setup.py", "build/docs"),
            "warning_is_error": ("setup.py", "true"),
        }
    },
)
