APRSD Command Plugin Development
================================

Creating a Plugin Project
-------------------------

The recommended way to create a new APRSD plugin project is to use the `cookiecutter-aprsd-plugin`_ template. This template provides a complete project structure with all the necessary files, testing infrastructure, and documentation setup.

Installation
~~~~~~~~~~~~

First, install cookiecutter if you haven't already::

    pip install cookiecutter

Creating a New Plugin Project
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Run cookiecutter with the APRSD plugin template::

    cookiecutter gh:hemna/cookiecutter-aprsd-plugin

Cookiecutter will prompt you for several pieces of information:

* **plugin_name**: The name of your plugin (e.g., ``aprsd-my-plugin``)
* **plugin_module_name**: The Python module name (e.g., ``aprsd_my_plugin``)
* **author_name**: Your name or organization name
* **author_email**: Your email address
* **description**: A brief description of your plugin
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
* Entry point registration for APRSD plugin discovery
* Test suite structure
* Documentation templates
* CI/CD pipeline configuration

For more information about the cookiecutter template, visit the `cookiecutter-aprsd-plugin repository`_.

.. _cookiecutter-aprsd-plugin: https://github.com/hemna/cookiecutter-aprsd-plugin
.. _cookiecutter-aprsd-plugin repository: https://github.com/hemna/cookiecutter-aprsd-plugin

APRSDPluginBase
------------------------

Plugins are written as python objects that extend the APRSDPluginBase class.
This is an abstract class that has several properties and a method that must be implemented
by your subclass.

Properties
----------

* name - the Command name
* regex - The regular expression that if matched against the incoming APRS message,
          will cause your plugin to be called.

Methods
-------

* command - This method is called when the regex matches the incoming message from APRS.
            If you want to send a message back to the sending, just return a string
            in your method implementation.  If you get called and don't want to reply, then
            you should return a messaging.NULL_MESSAGE to signal to the plugin processor
            that you got called and processed the message correctly.  Otherwise a usage
            string may get returned to the sender.


Example Plugin
--------------

There is an example plugin in the aprsd source code here:
aprsd/examples/plugins/example_plugin.py

.. code-block:: python

    import logging

    from aprsd import plugin

    LOG = logging.getLogger("APRSD")


    class HelloPlugin(plugin.APRSDRegexCommandPluginBase):
        """Hello World."""

        version = "1.0"
        # matches any string starting with h or H
        command_regex = "^[hH]"
        command_name = "hello"

        def process(self, packet):
            LOG.info("HelloPlugin")
            reply = "Hello '{}'".format(packet.from_call)
            return reply
