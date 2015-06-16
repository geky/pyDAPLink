pyDAPLink
=========

pyDAPLink is an Open Source python 2.7 based library for communicating with 
ARM Cortex-M microcontrollers using CMSIS-DAP. Linux, OSX and Windows are 
supported.

Installation
------------

To install the latest development version (master branch), you can do
the following:

.. code:: shell

    $ pip install --pre -U https://github.com/mbedmicro/pyDAPLink/archive/master.zip

Note that you may run into permissions issues running these commands.
You have a few options here:

#. Run with ``sudo -H`` to install pyDAPLink and dependencies globally
#. Specify the ``--user`` option to install local to your user
#. Run the command in a `virtualenv <https://virtualenv.pypa.io/en/latest/>`__ 
   local to a specific project working set.

You can also install from source by cloning the git repository and running

.. code:: shell

    python setup.py install

Development Setup
-----------------

PyDAPLink developers are recommended to setup a working environment using
`virtualenv <https://virtualenv.pypa.io/en/latest/>`__. After cloning
the code, you can setup a virtualenv and install the PyDAPLink
dependencies for the current platform by doing the following:

.. code:: console

    $ virtualenv env
    $ source env/bin/activate
    $ pip install -r dev-requirements.txt

On Windows, the virtualenv would be activated by executing
``env\Scripts\activate``.

