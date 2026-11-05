"""Auto Docs Editor - Apply Google Style Guide to markdown documents."""

from importlib.metadata import version

from beartype import BeartypeConf
from beartype.claw import beartype_this_package

beartype_this_package(conf=BeartypeConf(claw_is_pep526=False))

__version__ = version("docs-style")
