try:
    from ._version import version as __version__
except ModuleNotFoundError:
    __version__ = "unknown"
