Rackspace Intelligence Integration
========================

Iris can easily be integrated into an existing Rackspace implementation.

==================
Iris Configuration
==================

Enable the builtin Alertmanager webhook in Iris' configuration.

Configuration::

    webhooks:
      - rackspace

Then create an application using the UI. In this example let's use the name 'rackspace'.
Once you've created the application you'll be able to retrieve the application's key.
Here we'll use "abc".

==========================
Rackspace Configuration
==========================

In rackspace, you can configure a notification that posts to Iris as a receiver, using the application and it's key
as parameters.

Configuration is done via the rackspace api:
https://developer.rackspace.com/docs/rackspace-monitoring/v1/api-reference/notifications-operations/

An example request to configure a notification that alerts Iris would look like::

    {
      "label": "my webhook #1",
      "type": "webhook",
      "details": {
        "url": "http://iris:16649/v0/webhooks/alertmanager?application=rackspace&key=abc"
      }
      "metadata": {
        "iris_plan": "teamA"
      }
    }

The key "iris_plan" will point to a plan you created in Iris.

