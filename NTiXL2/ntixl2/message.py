"""The message.py module implement the command structure for the serial communication with the XL2 sound level meter.
For more information about the remote measurement option of the XL2 device see
the manual_ .

.. _manual: http://www.nti-audio.com/Portals/0/data/en/XL2-Remote-Measurement-Manual.pdf

Note
----

- There are **Query** messages by which the XL2 perform an **answers** and messages without an answers.

- There are messages with parameter and messages without parameters.

- A message has always a root message string. If the message has parameter the root string is followed by a \
  list (normally one) of parameter strings separated by spaces.

- XL2  root messages and parameter are not case sensitive

- The different types of messages are build on top of the **Basic message classes**

Warnings
-----
- Only a subset of the  XL2 messages are implemented
- Some messages are not complete
- The messages are not tested

Todo
----
- Implement all messages: Input messages
- Tests

"""

from collections import namedtuple
import itertools
import parse

############
# Parameters
############

# Categorical parameter values
ParamValue = namedtuple("ParamValue", ['value', 'description', 'requiredOption'])
ParamValue.__new__.__defaults__ = (None, '', 'BASE')




class CategoricalParam(object):
    """Serial message parameter of type categorical.

    Serial messages have often parameters of categorical type. eg. there is a finite set of allowed values.

    Note
    -----
    Repetitions are allowed

    """

    def __init__(self, description, allowedValues=None, repeatAllowed=0, options=['BASE'], delimiter=" "):
        self.description = description
        self.options = options
        self.allowedValues = self._filter(allowedValues)
        self.repeatAllowed = repeatAllowed
        self.param_list = []
        self.delimiter = delimiter

    def _filter(self, allowedValues):
        return [av for av in allowedValues if av.requiredOption in self.options]

    def _match_value(self, value):
        try:
            index = [av.value for av in self.allowedValues].index(value)
        except ValueError:
            return False
        else:
            return index

    def append_param(self, value):
        """Append parameter to parameter list."""
        if len(self.param_list) <= self.repeatAllowed:
            index = self._match_value(value)
            if type(index) == int:
                self.param_list.append(index)
            else:
                raise ValueError('Value {} is not allowed. See allowedValues attribute'.format(value))
        else:
            raise UserWarning('Max number of repeated parameter is {}'.format(self.repeatAllowed))

    def rm_param(self, last=False):
        """Remove parameters from list.

        Parameters
        ----------
        last : bool
            If  True remove last element from parameter list else remove all elements
        """
        if last:
            self.param_list = self.param_list[:-1]
        else:
            self.param_list = []

    def set_param(self, value: str):
        """ Set parameter or replace last parameter in parameter list."""
        self.rm_param(last=True)
        self.append_param(value)

    def __str__(self):
        """Translate parameter list to string for serial communication"""
        l = [self.allowedValues[i].value for i in self.param_list]
        if len(l):
            return self.delimiter.join(l)
        else:
            raise UserWarning('There are no param')

    def parameter_list(self):
        """Return list of parameter names."""
        l = [self.allowedValues[i].value for i in self.param_list]
        if len(l):
            return l
        else:
            raise UserWarning('There are no param')


class NumericalParam(object):
    """Serial message parameter of type numerical"""

    def __init__(self, description, min=None, max=None):
        self.description = description
        self.allowedValues = {'min': min, 'max': max}
        self.value = None

    def set_param(self, value):
        """Set or overwrite parameter value"""
        if value <= self.allowedValues['max'] and value >= self.allowedValues['min']:
            self.value = float(value)
        else:
            raise ValueError('Value {} is not allowed. See allowedValues attribute'.format(value))

    def rm_param(self, last=False):
        """ Remove parameter value."""
        self.value = None

    def __str__(self):
        """Translate parameter list to string for serial communication"""
        if self.value is not None:
            return str(self.value)
        else:
            raise UserWarning('There are no param')


########### Messages ##############

class Message(object):
    """Basic XL2 serial message class

    The class has methods for the creation (:meth:`to_str`) of XL2 messages and methods\
    for parsing (:meth:`parse_answers`) the relative XL2 answers.

    Note
    -----
    This class is for messages without params

    Attributes
    ----------
    GROUP : str
        Message group
    AVAILABILITY : str
        Message availability
    ROOT : str
        Message root string
    EOL : str
        Serial communication end of line
    RETURN : str
        XL2 answers string template. `None` if message has no answers

    Attributes
    ----------
    PARAM_TYPE : str
        string  describing parameter type. Should be {'categorical'|'numerical'}
    PARAM_NAME : str
        parameter name
    ALLOWED_VALUES : list
        list (of type : paramValues) values of allowed message parameter
    REPEAT_PARAM : int
        number of time which is possible to repeat parameter in a message string
    """

    # parameter Group
    GROUP = ""
    AVAILABILITY = ['always']
    # Serial message string
    ROOT = ""
    # serial message eind of line
    EOL = "\r\n"
    # return line format
    RETURN = None

    def __init__(self):
        self.params=[]

    def __str__(self):
        """Return the serial message

        Returns
        -------
        str
            serial message string

        """
        s={param : str(getattr(self, param)) for param in self.params}
        return self.ROOT.format(**s) + self.EOL

    def is_query(self):
        return self.RETURN is not None

    def return_lines(self):
        """Return the expected number of return lines of the message."""
        return 1

    def _parse(self, line):
        """Parse answers line according to RETURN  class attribute."""
        if self.RETURN is not None:
            p = parse.compile(self.RETURN + self.EOL)
            try:
                ret = p.parse(line).named
            except AttributeError as e:
                s = "not able to parse return string '{}'".format(line)
                raise AttributeError(s)
            else:
                return ret

    def parse_answers(self, lines):
        """Parse XL2 answers.

        Parameters
        ----------
        lines : list
            list containing XL2 answers lines to message

        Returns
        -------
        dict
            dict containing contents (key, value) of XL2 answers
        """
        assert len(lines) == 1
        line = lines[0]
        return self._parse(line)


########################
# Debug Mesages
class ECHO(Message):
    """Returns the 'deb' after the command including separators. It is for debugging purpose only.

    Note
    ----
    this implementation is not the same as the one in the manual_ .

    """
    GROUP = "Debug"
    ROOT = "ECHO {param_str}"
    RETURN = "{string}"


    def __init__(self, string=None):
        self.params = ["param_str"]
        self.param_str = ""
        if string is not None:
            self.param_str=string


########################
# Device Status Messages

class QUERY_IDN(Message):
    """Query the unique identification of the XL2."""

    GROUP = "DeviceStatus"
    ROOT = "*IDN?"
    RETURN = "{manufacturer},{unit},{serialNumber},{FW_Version}"

class RESET(Message):
    """ Executes a device reset.

    *The RST command:*
        -  clears the error queue
        -  stops any running measurement
        -  stops any running script
        -  exits any active profile
        -  selects the SLMeter function
        -  sets the following parameters
        -  Append mode: OFF
        -  Auto save: OFF
        -  Logging: OFF
        -  Events:  OFF
        -  Timer mode: CONTINUOUS
        -  Range: MID
        -  RMS/THDN Filter: Z-WEIGHTED
        -  Input: XLR
        -  Phantom Power:  ON
        -  RTA S- urce: LZF
        -  RTA Resolution: TERZ
        -  locks the keyboard
        -  sets the precision of queried floating-point numbers to 'LCD'

    Note
    ----
    Should be the first command when starting a remote session to ensure that all XL2 settings make sense for remote
    measuring. It is highly recommended to execute this command first to avoid unwanted side effects.

    """

    GROUP = "DeviceStatus"
    ROOT = "*RST"


##########################
# Initialization Messages

class INITIATE(Message):
    """Starts/Stops a measurement"""

    GROUP = "InitiateSubsystem"
    AVAILABILITY = ["SLM", "FFT", "1/12Oct"]
    ROOT = "INIT {param_action}"

    def __init__(self,action=None):
        self.params = ["param_action"]
        self.param_action= CategoricalParam("action",
                                            [ParamValue("START", "start a measurement", "BASE"),
                                             ParamValue("STOP", "stop a measurement", "BASE")]
                                            )
        if action is not None:
            self.param_action.set_param(action)

    @classmethod
    def START(cls):
        return cls("START")

    @classmethod
    def STOP(cls):
        return cls("STOP")


class QUERY_INITIATE_STATE(Message):
    """Queries the run status of a measurement.

    status: [STOPPED|FROZEN|SETTLING|RUNNING|PAUSED]
    """

    GROUP = "InitiateSubsystem"
    ROOT = "INIT:STATE?"
    RETURN = "{state}"


######################
# Measurement Messages



class MEASURE_FUNCTION(Message):
    """Set the active measurement function."""

    GROUP = "Measurement"
    ROOT = "MEAS:FUNCTION {param_function}"

    def __init__(self,function=None):
        functions = ["SLMeter", "FFT", "RT60", "Polarity", "Delay", "RMS/THD",
                     "N.Rating", "Scope", "1/12Oct", "STIPA", "Calibrate", "System"]

        self.params = ["param_function"]

        self.param_function= CategoricalParam("action",
                                            [ParamValue(func, '', 'BASE') for func in functions]
                                            )
        if function is not None:
            self.param_function.set_param(function)

    @classmethod
    def SLMeter(cls):
        return cls("SLMeter")

    @classmethod
    def Calibrate(cls):
        return cls("Calibrate")

    @classmethod
    def System(cls):
        return cls("System")

class QUERY_MEASURE_FUNCTION(Message):
    """Queries the active measurement function."""

    GROUP = "Measurement"
    ROOT = "MEAS:FUNCTION?"
    RETURN = "{function}"


class MEASURE_INITIATE(Message):
    """Triggers a measurement."""

    GROUP = "Measurement"
    ROOT = "MEAS:INIT"


class QUERY_MEASURE_TIMER(Message):
    """Queries the actual measurement timer value."""

    GROUP = "Measurement"
    ROOT = "MEAS:TIME?"
    RETURN = "{t:g} sec, {status}"
    AVAILABILITY = ["SLM"]


class QUERY_MEASURE_DTTIME(Message):
    """Queries the time period used for the calculation of dt values.

    The value is active as long as the measurement is RUNNING, and is reset after each INIT:MEAS or INIT START command.

    """

    GROUP = "Measurement"
    AVAILABILITY = ["runningSLM"]
    ROOT = "MEAS:DTTI?"
    RETURN = "{dt:g} sec, {status}"


# QUERY_MEAS_SLM_123 param



class QUERY_MEAS_SLM_123(Message):
    """..."""
    GROUP = "Measurement"
    AVAILABILITY = ["SLM"]
    ROOT = "MEAS:SLM:123? {param_statistic}"
    RETURN = "{level:g} dB, {status}"

    def __init__(self,statistic=None):

        STATISTICS = [['L{}S', 'Sound pressure level {} weigthed SLOW(1. sec) time average', 'BASE'],
                      ['L{}SMAX', '', 'BASE'],
                      ['L{}SMIN', '', 'BASE'],
                      ['L{}F', 'Sound pressure level {} weigthed FAST(0.125 sec) time average', 'BASE'],
                      ['L{}FMAX', '', 'BASE'],
                      ['L{}FMIN', '', 'BASE'],
                      ['L{}EQ', '', 'BASE'],
                      ['L{}PK', '', 'BASE'],
                      ['L{}PKMAX', '', 'BASE'],
                      ['L{}AEQt', '', 'BASE']]
        STATISTICS = [[s.format(w) for s in p] for p, w in itertools.product(STATISTICS, 'ACZ')] + [['k1', '', 'BASE'],
                                                                                                    ['k2', '', 'BASE']]
        self.params=['param_statistics']
        self.param_statistics=CategoricalParam("statistic",[ParamValue(*p) for p in STATISTICS])
        if statistic is not None:
            self.param_statistics.set_param(statistic)

    def return_lines(self):
        return len(self.param_statistics.parameter_list())

    def parse_answers(self, lines):
        ret = {}
        for p, line in zip(self.param_statistics.parameter_list(), lines):
            ret[p] = self._parse(line)
        return ret

################
# input messages
class INPUT_SELECT(Message):
    pass


class QUERY_INPUT_SELECT(Message):
    pass


class INPUT_RANGE(Message):
    pass


class QUERY_INPUT_RANGE(Message):
    pass


class INPUT_PHANTOM(Message):
    pass


class QUERY_INPUT_PHANTOM(Message):
    pass


####################
# calibrate messages

class QUERY_CALIBRATE_MIC_TYPE(Message):
    """Queries the microphone type recognized by the ASD system.

    Details:
    If no ASD (A Automatic S Sensor D Detection) microphone is currently connected, the command always returns noASD.
    In contrast, the command CALIB:MIC:SENS:SOURce returns the ASD microphone that
    was last connected, as long as the microphone sensitivity has not been changed
    manually or by remote command.

    """
    GROUP = "Calibrate"
    ROOT = "CALI:MIC:TYPE?"
    RETURN = "{micType}"


class QUERY_CALIBRATE_MIC_SENS_SOURCE(Message):
    """Queries the source of the sensitivity value.
    Device answer:
        micSensytivitySource:
        [PLEASE CALIBRATE|USER CALIBRATED|MANUALLY|M2210 USER|M2210 FACTORY|M2210 CAL.CENTER|
        M4260 USER|M4260 FACTORY|M4260 CAL.CENTER]

    Returns the ASD microphone that was last connected as long as the microphone
    sensitivity has not been changed manually or by remote command.
    PLEASE CALIBRATE is returned when the sensitivity has never been set since the last
    factory default setup.

    """
    GROUP = "Calibrate"
    ROOT = "CALI:MIC:SENS:SOUR?"
    RETURN = "{micSensytivitySource}"


class CALIBRATE_MIC_SENS_VALUE(Message):
    """Defines the microphone sensitivity in V/Pa.

    Details:
    Command is not accepted when an ASD microphone is connected.

    """

    GROUP = "Calibrate"
    ROOT = "CALI:MIC:SENS:VALU {param_micSensitivity}"
    PARAM_NAME = "micSensitivity"

    def __init__(self,micSensitivity=None):
        self.params=["micSensitivity"]
        self.param_micSensitivity=NumericalParam('micSensitivity',{'min': 100e-6, 'max': 9.99})
        if micSensitivity is not None:
            self.param_micSensitivity.set_param(micSensitivity)


class QUERY_CALIBRATE_MIC_SENS_VALUE(Message):
    """Queries the microphone sensitivity in V/Pa.

    Device answer is:

    V,OK  float  100e-6 to 9.99 V/Pa

    """
    GROUP = "Calibrate"
    ROOT = "CALI:MIC:SENS:VALU?"
    RETURN = "{micSensitivityValue:g} V,{status}"


##################
# System messages
class QUERY_SYSTEM_ERROR(Message):
    """Queries the error queue.

    *possible errors are:*

    - -350: "Error queue full - at least 2 errors lost",
    - -115: "Too many parameters in command",
    - -113: "Invalid command",
    - -112: "Too many characters in one of the command parts",
    - -109: "Missing command or parameter",
    - -108: "Invalid parameter",
    - 0: "no error (queue is empty)",
    - 1: "Command too long; too many characters without new line",
    - 2: "UNEXPECTED_PID",
    - 3: "DSP_TIMEOUT",
    - 4: "Changing microphone sensitivity is not possible when an ASD microphone is connected to the XL2",
    - 5: "Parameter not available, license not installed",
    - 6: "dt value does not exist for this parameter",
    - 7: "Parameter is not available in the current measurement function",
    - 8: "Unspecified DSP error",
    - 9: "Not valid, measurement is running"

    Attributes
    -----
    ERRORS : dict
        dict of errors.

    """

    GROUP = "System"
    ROOT = "SYST:ERRO?"
    RETURN = "{errList}"
    ERRORS = {
        -350: "Error queue full - at least 2 errors lost",
        -115: "Too many parameters in command",
        -113: "Invalid command",
        -112: "Too many characters in one of the command parts",
        -109: "Missing command or parameter",
        -108: "Invalid parameter",
        0: "no error (queue is empty)",
        1: "Command too long; too many characters without new line",
        2: "UNEXPECTED_PID",
        3: "DSP_TIMEOUT",
        4: "Changing microphone sensitivity is not possible when an ASD microphone is connected to the XL2",
        5: "Parameter not available, license not installed",
        6: "dt value does not exist for this parameter",
        7: "Parameter is not available in the current measurement function",
        8: "Unspecified DSP error",
        9: "Not valid, measurement is running"
    }

    def parse_answers(self, lines):
        assert len(lines) == 1
        line = lines[0]
        ret = self._parse(line)["errList"]
        err_list = [int(i.strip()) for i in ret.split(",")]
        return [(err, self.ERRORS.get(err)) for err in err_list]

class QUERY_SYSTEM_DATE(Message):
    """Queries the system Date

    Attributes
    -----
    DATE : dict
        dict of errors.

    """

    GROUP = "System"
    ROOT = "SYST:DATE?"
    RETURN = "{year:d},{month:d},{day:d}"



class QUERY_SYSTEM_TIME(Message):
    """Queries the system Date

    Attributes
    -----
    DATE : dict
        dict of errors.

    """

    GROUP = "System"
    ROOT = "SYST:TIME?"
    RETURN = "{hour:d},{minute:d},{second:d}"

class SYSTEM_KEY(Message):
    """Simulates a key stroke on the XL2"""

    GROUP = "System"
    ROOT = "SYST:KEY {param_keys}"
    RETURN = "{status}"

    def __init__(self, keys=None):
        self.params = ['param_keys']
        self.param_keys = CategoricalParam("keys", [ParamValue(key, '', 'BASE') for key in
                          ["ESC", "NEXT", "FNEXT", "PREV", "FPREV", "ENTER", "PAGE", "START",
                           "PAUSE", "SPEAKER", "LIMIT", "LIGHT"]],30)
        if keys is not None:
            for k in keys:
                self.param_keys.append_param(k)

class SYSTEM_KLOCK(Message):
    """Locks the keyboard of the XL2"""

    GROUP = "System"
    ROOT = "SYST:KLOC {param_klock}"
    PARAM_TYPE = "categorical"
    def __init__(self, klock=None):
        self.params = ['param_klock']
        self.param_klock = CategoricalParam("klock", [ParamValue("ON", "Keyboard is locked", "BASE"),
                      ParamValue("OFF", "Keyboard is unlocked", "BASE")])
        if klock is not None:
            self.param_klock.set_param(klock)

    @classmethod
    def ON(cls):
        return cls("ON")

    @classmethod
    def OFF(cls):
        return cls("OFF")


class QUERY_SYSTEM_KLOCK(Message):
    """Queries the key lock status"""
    GROUP = "System"
    ROOT = "SYST:KLOC?"
    RETURN = "{keyLock}"


class QUERY_SYSTEM_OPTIONS(Message):
    """Queries the installed options."""

    GROUP = "System"
    ROOT = "SYST:OPTI?"
    RETURN = "{optList}"

    def parse_answers(self, lines):
        assert len(lines) == 1
        line = lines[0]
        ret = self._parse(line)["optList"]
        return [i.strip() for i in ret.split(",")]


class SYSTEM_MSDMAC(Message):
    """Switches the XL2 to the USB mass storage mode for Mac and Linux.

    Use this Command on Mac and Linux instead of “SYSTem:MSD”, otherwise MSD will
    timeout after 2 minutes and the XL2 returns to COM mode.
    After sending this command, the XL2 drops the COM connection (no more remote
    commands are possible) and switches to mass storage mode. The host then has full
    access to the data stored on the SD card of the XL2.
    To return to COM mode eject the XL2 drive from the host computer.

    Note
    ----
    If you umount the XL2 drive by the host, the XL2 will not return to COM
    mode. it is necessary to eject the disk.

    """

    GROUP = "System"
    ROOT = "SYST:MSDMAC"

