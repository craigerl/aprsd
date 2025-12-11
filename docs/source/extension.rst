APRSD Extension Development
============================

APRSD extensions are more comprehensive than plugins and can add new functionality
to the APRSD daemon beyond simple command plugins. Extensions can include:

* New command-line commands
* Configuration options
* Background threads
* Statistics collectors
* Custom packet processors
* And more

Creating an Extension Project
-------------------------------

The recommended way to create a new APRSD extension project is to use the
`cookiecutter-aprsd-extension`_ template. This template provides a complete project
structure with all the necessary files, testing infrastructure, and documentation setup.

Installation
~~~~~~~~~~~~

First, install cookiecutter if you haven't already::

    pip install cookiecutter

Creating a New Extension Project
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Run cookiecutter with the APRSD extension template::

    cookiecutter gh:hemna/cookiecutter-aprsd-extension

Cookiecutter will prompt you for several pieces of information:

* **extension_name**: The name of your extension (e.g., ``aprsd-my-extension``)
* **extension_module_name**: The Python module name (e.g., ``aprsd_my_extension``)
* **author_name**: Your name or organization name
* **author_email**: Your email address
* **description**: A brief description of your extension
* **version**: Initial version (default: ``0.1.0``)

Project Structure
~~~~~~~~~~~~~~~~~

The cookiecutter template creates a complete project structure including:

* **Test automation** with Tox
* **Linting** with pre-commit and Flake8
* **Continuous integration** with GitHub Actions
* **Documentation** with Sphinx and Read the Docs
* **Automated uploads** to PyPI and TestPyPI
* **Automated dependency updates** with Dependabot
* **Code formatting** with Gray
* **Testing** with pytest
* **Code coverage** with Coverage.py
* **Coverage reporting** with Codecov

The generated project follows Python packaging best practices and includes:

* Proper ``setup.py`` and ``pyproject.toml`` configuration
* Entry point registration for APRSD extension discovery (``aprsd.extension``)
* Configuration entry points for oslo.config (``oslo.config.opts``)
* Test suite structure
* Documentation templates
* CI/CD pipeline configuration

Extension Registration
~~~~~~~~~~~~~~~~~~~~~~

Extensions are registered using Python entry points in your ``pyproject.toml`` or
``setup.py`` file. The entry point group is ``aprsd.extension``::

    [project.entry-points."aprsd.extension"]
        "my_extension" = "aprsd_my_extension.extension"

Configuration Options
~~~~~~~~~~~~~~~~~~~~~

Extensions can add their own configuration options using oslo.config. Register
your configuration options using the ``oslo.config.opts`` entry point::

    [project.entry-points."oslo.config.opts"]
        "aprsd_my_extension.conf" = "aprsd_my_extension.conf.opts:list_opts"

Example Extension Structure
~~~~~~~~~~~~~~~~~~~~~~~~~~~

A typical extension project structure looks like this::

    aprsd-my-extension/
    ├── aprsd_my_extension/
    │   ├── __init__.py
    │   ├── extension.py          # Main extension entry point
    │   ├── cmds/                 # Command-line commands
    │   │   ├── __init__.py
    │   │   └── show.py
    │   ├── conf/                 # Configuration options
    │   │   ├── __init__.py
    │   │   ├── opts.py
    │   │   └── main.py
    │   ├── threads/              # Background threads
    │   │   ├── __init__.py
    │   │   └── MyThread.py
    │   └── stats.py              # Statistics collectors
    ├── tests/
    ├── docs/
    ├── pyproject.toml
    ├── setup.py
    └── README.md

Example Extension: WebChat
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The `aprsd-webchat-extension`_ is a real-world example of an APRSD extension that
adds a web-based chat interface to APRSD. Let's examine how it's structured:

Entry Point Registration
^^^^^^^^^^^^^^^^^^^^^^^^^

In ``pyproject.toml``, the extension registers itself::

    [project.entry-points."aprsd.extension"]
        "webchat" = "aprsd_webchat_extension.extension"

    [project.entry-points."oslo.config.opts"]
        "aprsd_webchat_extension.conf" = "aprsd_webchat_extension.conf.opts:list_opts"

Extension Entry Point
^^^^^^^^^^^^^^^^^^^^^^

The ``extension.py`` file imports the command module to register it::

    from aprsd_webchat_extension.cmds import webchat  # noqa: F401

This import causes the command to be registered with APRSD's CLI system.

Command Implementation
^^^^^^^^^^^^^^^^^^^^^^

The webchat extension adds a new command ``aprsd webchat`` that starts a Flask-based
web server. The command is implemented in ``cmds/webchat.py`` and uses Click for
command-line interface::

    import click
    from aprsd.main import cli

    @cli.command()
    @click.option('--host', default='0.0.0.0', help='Host to bind to')
    @click.option('--port', default=8080, help='Port to bind to')
    def webchat(host, port):
        """Start the webchat interface."""
        # Implementation here
        pass

WebChat Configuration Options
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The extension adds configuration options through ``conf/opts.py``::

    from oslo_config import cfg

    webchat_group = cfg.OptGroup(name='webchat',
                                  title='WebChat Options')

    webchat_opts = [
        cfg.StrOpt('host',
                   default='0.0.0.0',
                   help='WebChat server host'),
        cfg.IntOpt('port',
                   default=8080,
                   help='WebChat server port'),
    ]

    def list_opts():
        return [
            (webchat_group, webchat_opts),
        ]

The configuration can then be used in the extension code::

    from oslo_config import cfg

    CONF = cfg.CONF
    host = CONF.webchat.host
    port = CONF.webchat.port

WebChat Project Structure
^^^^^^^^^^^^^^^^^^^^^^^^^

The webchat extension has the following structure::

    aprsd-webchat-extension/
    ├── aprsd_webchat_extension/
    │   ├── __init__.py
    │   ├── extension.py          # Entry point that imports commands
    │   ├── cmds/
    │   │   ├── __init__.py
    │   │   └── webchat.py         # Command implementation
    │   ├── conf/
    │   │   ├── __init__.py
    │   │   ├── opts.py            # Configuration option definitions
    │   │   └── main.py            # Configuration group definitions
    │   ├── web/                   # Web assets (HTML, CSS, JS)
    │   │   └── chat/
    │   │       ├── static/
    │   │       └── templates/
    │   └── utils.py               # Utility functions
    ├── tests/
    ├── docs/
    ├── pyproject.toml
    └── README.md

Usage
^^^^^

Once installed, users can run the webchat command::

    $ aprsd webchat --loglevel DEBUG

This demonstrates how extensions can add new functionality beyond simple plugins,
including web interfaces, background services, and complex integrations.

For more information about the cookiecutter template, visit the
`cookiecutter-aprsd-extension repository`_.

For the complete source code of the webchat extension, see the
`aprsd-webchat-extension repository`_.

.. _cookiecutter-aprsd-extension: https://github.com/hemna/cookiecutter-aprsd-extension
.. _cookiecutter-aprsd-extension repository: https://github.com/hemna/cookiecutter-aprsd-extension
.. _aprsd-webchat-extension: https://github.com/hemna/aprsd-webchat-extension
.. _aprsd-webchat-extension repository: https://github.com/hemna/aprsd-webchat-extension
