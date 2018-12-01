import datetime
import json

class TrainPassby(object):
    DICT_KEYS=set(["stop_rec","start_rec","ax_data", "trigger",'sync_time'])
    def __init__(self,axle_sensors_names, stop_delay=10, ax_counter_low_err=4):
        self.ax_names= axle_sensors_names
        self._ax_counter={name:0 for name in self.ax_names}
        self._ax_data =[]# {name: {} for name in self.ax_names}
        #
        self.stop_delay=datetime.timedelta(seconds=stop_delay)
        self._stopped=False
        self._start_after_ax=2
        #
        self._ax_counter_low_err=ax_counter_low_err
        self.errors=[]
        self._d = {
                   "trigger": None,
                   "start_rec":None,
                   "stop_delay":stop_delay,
                   "start_after_ax":self._start_after_ax,
                   }
        #'dict' object has no attribute 'append'.

        self._start_time=None
        self._last_ax_timestamp=None
        self._ax_trigger=None

    @property
    def is_complete(self):
        return set(self._d.keys()).issubset(TrainPassby.DICT_KEYS)

    @property
    def is_error(self):
        return len(self.errors)>0

    def rec(self):
        pass

    @property
    def _name(self):
        try:
            name= "{start_rec:%Y_%m_%d_%Hh%Mm%Ss}_passby".format(**self._d)
        except TypeError:
            name = "{:%Y_%m_%d_%Hh%Mm%Ss}_passby_no_start".format(self._now())
        if len(self.errors):
            name = name + "_ERR"
        return name

    def add_axle_data(self,ax_name,header, time_wheel_on, time_wheel_off, timestamp,**kwargs):
        self._ax_counter[ax_name]+=1
        self._ax_data.append([timestamp, self._ax_counter[ax_name], ax_name,time_wheel_off, time_wheel_on, header])
        self._last_ax_timestamp=timestamp

        if header=="MSG_HEADER_AXLE_ERROR":
            self.errors.append((ax_name,timestamp))

    def add_error(self,err="timeout"):
        self.errors.append((err,self._now()))

    def set_rec_stop_time(self):
        self._d['stop_rec']= self._now()
    def set_rec_start_time(self):
        self._d['start_rec']= self._now()

    def set_xl2_BBG_sync_time(self, xl2time):
        self._d['sync_time']= {"xl2":xl2time,"BBG":self._now()}

    def _now(self):
        return datetime.datetime.now()

    def export(self,path):
        filePath = path.joinpath(self._name+".json")
        self._d['errors']=self.errors
        self._d['ax_data'] = self._ax_data
        self._d['trigger'] = self._ax_trigger
        self._d['ax_counts'] = self._ax_counter
        with filePath.open('w') as f:
            json.dump(self._d, f,indent=2,sort_keys=True,default=str)


def sync_str_to_datetime(s):
    try:
        t = datetime.datetime.strptime(s, "%Y-%m-%d %H:%M:%S.%f")
    except ValueError:
        t = datetime.datetime.strptime(s, "%Y-%m-%d %H:%M:%S")
    return t

def xl2_time_correction(passby):
    """
    Berechnet zeitkorrektur für xl2

    xl2_start_uncorrected  ist nur für achsdaten ohne syncronisierung nötig
    """
    sync = passby["sync_time"]
    return sync_str_to_datetime(sync['BBG']) - sync_str_to_datetime(sync['xl2'])



