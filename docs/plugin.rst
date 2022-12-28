APRSD Command Plugin Development
================================

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
