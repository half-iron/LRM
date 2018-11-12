message module
==============

.. automodule:: message

Basic message classes
*********************

.. autoclass:: Message
    :members:

.. autoclass:: MessageWithParam
    :show-inheritance:
    :members:

.. autoclass:: MessageWithParams
    :show-inheritance:
    :members:

Xl2 Messages
************

Debug
+++++

.. autoclass:: ECHO
    :show-inheritance:

Device Status
+++++++++++++

.. autoclass:: QUERY_IDN
    :show-inheritance:

.. autoclass:: RESET
    :show-inheritance:

Initiate
++++++++

.. autoclass:: INITIATE
    :show-inheritance:

.. autoclass:: QUERY_INITIATE_STATE
    :show-inheritance:

Measurement
+++++++++++

.. autoclass:: MEASURE_FUNCTION
    :show-inheritance:

.. autoclass:: QUERY_MEASURE_FUNCTION
    :show-inheritance:

.. autoclass:: MEASURE_INITIATE
    :show-inheritance:

.. autoclass:: QUERY_MEAS_SLM_123
    :show-inheritance:


Input
+++++

.. autoclass:: INPUT_SELECT
    :show-inheritance:

.. autoclass:: QUERY_INPUT_SELECT
    :show-inheritance:

.. autoclass:: INPUT_RANGE
    :show-inheritance:

.. autoclass:: QUERY_INPUT_RANGE
    :show-inheritance:

.. .. autoclass:: INPUT_PHANTOM
    :show-inheritance:
.. .. autoclass:: QUERY_INPUT_PHANTOM
    :show-inheritance:

Calibrate
+++++++++

.. .. autoclass:: CALIBRATE_MIC_SENS_VALUE
    :show-inheritance:
.. .. autoclass:: QUERY_CALIBRATE_MIC_SENS_SOURCE
    :show-inheritance:

System
++++++

.. autoclass:: QUERY_SYSTEM_ERROR
    :show-inheritance:

.. autoclass:: SYSTEM_KEY
    :show-inheritance:

.. autoclass:: SYSTEM_KLOCK
    :show-inheritance:

.. autoclass:: QUERY_SYSTEM_KLOCK
    :show-inheritance:

.. autoclass:: QUERY_SYSTEM_OPTIONS
    :show-inheritance:

.. autoclass:: SYSTEM_MSDMAC
    :show-inheritance:

