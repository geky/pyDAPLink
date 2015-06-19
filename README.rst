pyDAPLink
=========

pyDAPLink is an Open Source python 2.7 library for communicating with 
ARM Cortex-M microcontrollers through `CMSIS-DAP <https://github.com/ARMmbed/CMSIS-DAP>`__
over USB. Currently Linux, OSX, and Windows are supported.

| For more information on CMSIS-DAP you can find the official standard:
| https://silver.arm.com/browse/CMSISDAP

Installation
------------

To install the latest development version (master branch), you can do
the following:

.. code:: shell

    $ pip install --pre -U https://github.com/<user>/pyDAPLink/archive/master.zip

| Note that you may run into permissions issues running these commands.
| You have a few options here:

#. Run with ``sudo -H`` to install pyDAPLink and dependencies globally
#. Specify the ``--user`` option to install local to your user
#. Run the command in a `virtualenv <https://virtualenv.pypa.io/en/latest/>`__ 
   local to a specific project working set.

You can also install from source by cloning the git repository and running

.. code:: shell

    $ python setup.py install

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

Examples
--------

| For a more in depth example you can look into pyDAPLink's usage in pyOCD:
| https://github.com/<user>/pyOCD

Hello World example program
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code:: python

    from pyDAPLink import DAPLink
    from pyDAPLink import AP_REG, DP_REG

    # Some device specific definitions are needed
    MBED_VID = 0x0d28
    MBED_PID = 0x0204
    CORTEXM_DHCSR = 0xE000EDF0
    CORTEXM_DCRSR = 0xE000EDF4
    CORTEXM_DCRDR = 0xE000EDF8
    DBG_KEY = 0xA05F0000
    DBG_ENABLE = 0x1
    DBG_HALT = 0x2

    # Find all connected devices
    interfaces = DAPLink.getConnectedInterfaces(MBED_VID, MBED_PID)

    for interface in interfaces:
        # Create a CMSIS-DAP connection
        dap = DAPLink(interface)
        dap.init()

        # Read ID code
        print 'ID: 0x%08x' % dap.readAP(AP_REG['IDR'])

        # Halt a Cortex-M
        dap.writeMem(CORTEXM_DHCSR, DBG_KEY | DBG_ENABLE | DBG_HALT)

        # Read a Cortex-M's PC
        dap.writeMem(CORTEXM_DCRSR, 15)
        print 'PC: 0x%08x' % dap.readMem(CORTEXM_DCRDR)

        dap.uninit()
