# compiler_magic
Compiler magics for use with Jupyter notebooks.

# Installation

1. Enter the directory you downloaded this file in
2. run python setup.py install
3. Append the contents of hpcmagic/custom.js to ~/.jupyter/custom/custom.js
4. Copy hpcmagic/hpcmagic.ini to ~/.local/hpcmagic/hpcmagic.ini
5. Append the contents of hpcmagic/ipython_config.py to ~/.ipython/profile_default/ipython_config.py

# Use

Edit the contents of ~/.local/hpcmagic/hpcmagic.ini to suit your Linux/Unix development environment. Or define environment variables with the same name as the defaults in ~/.local/hpcmagic/hpcmagic.ini.

There are three cell magics available

1. %%CPP

1. %%C

1. %%FORTRAN



