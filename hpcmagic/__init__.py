"""Cell Magics for High Performance Computing languages"""
__version__ =  "1.0"

from .hpcmagic import HPCMagics

def load_ipython_extension(ipython):
    """
    Any module file that define a function named `load_ipython_extension`
    can be loaded via `%load_ext module.path` or be configured to be
    autoloaded by IPython at startup time.
    """
    hpcmagics = HPCMagics(ipython)
    ipython.register_magics(hpcmagics)
