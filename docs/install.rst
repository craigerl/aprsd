APRSD installation
==================

Install info in a nutshell
--------------------------

**Pythons**: Python 3.6 or later

**Operating systems**: Linux, OSX, Unix

**Installer Requirements**: setuptools_

**License**: Apache license

**git repository**: https://github.com/craigerl/aprsd

Installation with pip
--------------------------------------

Use the following command:

.. code-block:: shell

   pip install aprsd

It is fine to install ``aprsd`` itself into a virtualenv_ environment.

Install from clone
-------------------------

Consult the GitHub page how to clone the git repository:

    https://github.com/craigerl/aprsd

and then install in your environment with something like:

.. code-block:: shell

    $ cd <path/to/clone>
    $ pip install .

or install it `editable <https://pip.pypa.io/en/stable/reference/pip_install/#editable-installs>`_ if you want code changes to propagate automatically:

.. code-block:: shell

    $ cd <path/to/clone>
    $ pip install --editable .

so that you can do changes and submit patches.


Install for development
----------------------------

For developers you should clone the repo from github, then use the Makefile

.. code-block:: shell

   $ cd <path/to/clone>
   $ make

This creates a virtualenv_ directory, install all the requirements for
development as well as aprsd in `editable <https://pip.pypa.io/en/stable/reference/pip_install/#editable-installs>`_ mode.
It will install all of the pre-commit git hooks required to test prior to committing code.


.. include:: links.rst
