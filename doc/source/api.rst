The :mod:`aodhclient` Python API
================================

.. module:: aodhclient
   :synopsis: A client for the Aodh API.

.. currentmodule:: aodhclient

Usage
-----

To use aodhclient in a project::

    >>> from aodhclient.v1 import client
    >>> aodh = client.Client(...)
    >>> aodh.alarm.list("alarm")

Reference
---------

For more information, see the reference:

.. toctree::
   :maxdepth: 2 

   ref/v1/index

