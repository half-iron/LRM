import json
from ntixl2.xl2parser import parse_broadband_file
import datetime
import numpy as np


import pandas as pd



def str_to_datetime(s):
    try:
        t = datetime.datetime.strptime(s, "%Y-%m-%d %H:%M:%S.%f")
    except ValueError:
        t = datetime.datetime.strptime(s, "%Y-%m-%d %H:%M:%S")

    return t

def load_achs_data_from_Measurement_dir(d, logger):
    Messungen = []
    if "bemerkung.json" in [f.name for f in d.iterdir()]:
        with d.joinpath("bemerkung.json").open('r+') as file:
            bem_d = json.load(file)

        ## bemerkung bearbeitung
        td = bem_d.get('timedelta', None)
        if (td != "sync") and (td != None):
            h, m, s = td
            td = datetime.timedelta(hours=h, minutes=m, seconds=s)

        ##load or skip achs_data
        skip = bem_d.get('skip', [])
        if skip == "all":
            logger.info("Bemerkung file found -> Skip all files.")
            return bem_d, Messungen
        elif type(skip) == list:
            logger.info("Bemerkung file found -> Load achs_data.")
            for f in d.joinpath('passby').iterdir():
                if f.match("*.json"):
                    with f.open('r+') as file:
                        achs_data = json.load(file)
                    ##skip single files
                    if achs_data["rec_n"] not in skip:
                        achs_data['path'] = f
                        if td == "sync":
                            BBG_t = achs_data["sync_time"]['BBG']
                            xl2_t = achs_data["sync_time"]['xl2']
                            achs_data['timedelta'] = str_to_datetime(xl2_t) - str_to_datetime(BBG_t)
                        else:
                            achs_data['timedelta'] = td
                        Messungen.append({k: achs_data[k] for k in ['path', 'start_rec', 'stop_rec', 'timedelta']})
                    else:
                        logger.info("Skip n_rec {}.".format(achs_data["n_rec"]))
                        # return
            return bem_d, Messungen
        else:
            raise TypeError("skip has to be a list or \"all\".")
    else:
        logger.info("Bemerkung file not found, skip directory.")
        return None, Messungen

def load_xl2logs_infos(d,logger):
    #Iterate XL2  log data rec_found= [(path, logdict),...]
    rec_found=[]
    logger.info("Directory: {}.".format(d))
    for f in d.iterdir():
        if f.match("*123_Log.txt"):
            log_data=parse_broadband_file(f)['Measurement']
            log_data['path']=f
            #
            rec_found.append(log_data)
    logger.info("number of rec: {}.".format(len(rec_found)))
    return rec_found

def has_overlap(A_start, A_end, B_start, B_end):
    latest_start = max(A_start, B_start)
    earliest_end = min(A_end, B_end)
    return latest_start <= earliest_end

def assign_xl2rec_to_measurement(start_rec,stop_rec, timedelta, records, pop = False,**kwargs):
    l=[]
    dt = datetime.timedelta(seconds=2)
    start = str_to_datetime(start_rec)-dt+timedelta
    stop=str_to_datetime(stop_rec)+dt+timedelta
    for r in records:
        if has_overlap(start,stop,r['Start'],r['End']):
            l.append(r['path'])
            if pop:
                records.pop(r)
    return l



###############################

##############################

def correct_doppelte_axle(achs_times):
    """
    eliminiert doppelte achsen
    """
    try:
        error = []
        T_MIN_RAD = 0.01  # distanza minima tra due segnali per riconoscerli come due ruote diverse
        at = np.array(achs_times)
        t = at[:, 1]
        t[0] = 0  # correggere None
        # secondi del timestamp
        t_BBG = [str_to_datetime(r) for r in at[:, 2]]
        td = t_BBG[0]
        t_BBG = np.array([(ti - td).total_seconds() for ti in t_BBG])
        ##
        t_diff = t[1:] - t[:-1]
        if (np.sort(t) == t).all():
            if sum(t_diff == 0):
                error.append('axle_time_repetition_err')
            else:
                t_mask = t_diff > T_MIN_RAD
        else:
            error.append('axle_time_ascending_err')

        if len(error) > 0:
            t_diff = t_BBG[1:] - t_BBG[:-1]
            t_mask = t_diff > T_MIN_RAD

        t_mask = np.hstack([[True], t_mask])
    except:
        error=['CORRECT_DOPPELTE_ACHSE']
        t_mask=[True]*len(t)

    return error, np.vstack([t[t_mask], t_BBG[t_mask]])


def calc_bogie():
    pass
    return None


def calc_xl2_time_correction(axle_data, xl2_start_uncorrected):
    """
    Berechnet zeitkorrektur für xl2

    xl2_start_uncorrected  ist nur für achsdaten ohne syncronisierung nötig
    """
    axle_data_start_rec = str_to_datetime(axle_data['start_rec'])
    sync = axle_data.get("sync_time", None)
    if sync is not None:
        xl2_time_correction = str_to_datetime(sync['BBG']) - str_to_datetime(sync['xl2'])
    else:  # für alte achsdaten (!ungenau)
        xl2_time_correction = (axle_data_start_rec - xl2_start_uncorrected)

    return xl2_time_correction


def xl2_logs_to_df(xl2_log, xl2_time_correction):
    """
    korrigiert  zeiten und tut messdaten in dataframe format
    """
    xl2_log_df = pd.DataFrame.from_dict(data=xl2_log['Broadband LOG Results']["samples"], orient='index')
    xl2_log_df.columns = xl2_log['Broadband LOG Results']["samples_columns"]
    # sync
    xl2_log_df.index = xl2_log_df.index + xl2_time_correction
    return xl2_log_df



if __name__=="__main__":
    import logging
    import sys
    import pickle
    from pathlib import Path

    PATH = Path("/home/esr/Documents/lausanne_triage/")


    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    logger.addHandler(logging.StreamHandler(sys.stdout))
    path_log = PATH.joinpath("zuordnung_Messung_XL2.log" )
    logger.addHandler(logging.FileHandler(str(path_log)))



    logger.info("Path: {}.\n#####################".format(PATH))

    # Iterate Messanlage files
    Messungen = []
    bemerkungen = {}
    n_last = 0

    ##
    logger.info("\nLOAD MESSDATA.\n#####################")
    for d in PATH.joinpath('Messdata').iterdir():
        if d.match("*Messung_2018_0[4-6]*"):
            logger.info("Directory: {}.".format(d))
            b, m = load_achs_data_from_Measurement_dir(d, logger)
            bemerkungen[d.name] = b
            Messungen += m

    ###########################
    ############################
    logger.info("number of rec: {}.".format(len(Messungen) - n_last))
    n_last = len(Messungen)
    logger.info("Total number of measurments found: {}.".format(len(Messungen)))
    ##
    logger.info("\nBEMERKUNGEN SUMMARY.\n#####################")
    for k, b in bemerkungen.items():
        logger.info("{}: {}.".format(k, b))
    ##
    logger.info("\nLOAD XL2 RECS.\n#####################")
    rec_found = []
    for d in PATH.iterdir():
        if d.match("XL2_*"):
            rec_found += load_xl2logs_infos(d, logger)
    logger.info("Total number of records found: {}.".format(len(rec_found)))

    ##stats
    logger.info("\nASSIGN xl2 TO MESSUNGEN.\n#####################")
    assigned, not_assigned, not_correctly_assigned = 0, 0, 0
    AssignedMessungen = {}
    for m in Messungen:
        path = assign_xl2rec_to_measurement(**m, records=rec_found)
        n_paths = len(path)
        if n_paths == 0:
            not_assigned += 1
            logger.debug("Not assigned: {}, {}.".format(m['path'].parent.parent.name, m['path'].name))
        elif n_paths == 1:
            m['xl2_file_path'] = path[0]
            AssignedMessungen[str(m["path"].relative_to(PATH))]={ "xl2_file_path":str(m["xl2_file_path"].relative_to(PATH)),
                                                                  'timedelta':m['timedelta'] }
            assigned += 1
        elif n_paths > 1:
            m['xl2_file_path'] = path
            not_correctly_assigned += 1
    logger.info("Correctly assigned {},\nNot assigned {},\
                \nNot correctly PATH.joinpath(assigned {}.".format(assigned, not_assigned, not_correctly_assigned))
    ##pickle
    name = "zuordnung_Messung_XL2"
    logger.info("\nPICKLE assignement to {}.\n####################".format(name))
    with PATH.joinpath(name+".json").open("w+") as f:
        json.dump(AssignedMessungen, f, sort_keys=True, indent=4,default=str)
    with PATH.joinpath(name+".pkl").open("wb") as f:
        pickle.dump(AssignedMessungen, f)