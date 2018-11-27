import json
from NTiXL2.ntixl2.xl2parser import parse_broadband_file
import datetime
from pyLRM.passby import sync_str_to_datetime,xl2_time_correction
from pathlib import Path
import argparse
import logging
import sys,os
from shutil import copyfile
import pandas as pd

logging.basicConfig( stream=sys.stdout,format='%(funcName)-15s: %(message)s',level=logging.INFO)
logger = logging.getLogger()


def delete_files(file_path_list):
    for f in file_path_list:
        logger.info("delete {}.".format(f.as_posix()))
        os.remove(f.as_posix())


def copy_files(file_path_list, path_destination):
    if path_destination.is_dir():
        for f in file_path_list:
            new= copyfile(f.as_posix(), path_destination.as_posix())
            logger.info("File {} copied at {}.".format(f.as_posix(),new))
    else:
        raise Exception('destination_path {} is not a directory'.format(path_destination.as_posix()))

def load_passby_info(path):
    p_info = {}
    with path.open('r+') as file:
        p = json.load(file)
        p_info['path'] = path
        try:
            p_info['xl2_time_correction'] = xl2_time_correction(p)

        except Exception as e:
            logger.exception("Passby {} generate exception {}".format(path, e), exc_info=e)
            logger.warning("Skip  {}.".format(path.name))
            return None
        else:
            p_info['start_rec'] = sync_str_to_datetime(p['start_rec'])
            p_info['stop_rec'] = sync_str_to_datetime(p['stop_rec'])
    return p_info


def load_passby_info_from_dir(dir_path, name_match ="*passby.json"):
    passby_list = []
    if "bemerkung.json" in [f.name for f in dir_path.iterdir()]:
        with dir_path.joinpath("bemerkung.json").open('r+') as file:
            bem_d = json.load(file)
            skip = bem_d.get('skip', [])
        logger.info("bemerkung.json file found")
        logger.info("{}\n--------------".format(json.dumps(bem_d, indent=2)))
    else:
        bem_d=None
        skip=[]
    ##load or skip passby
    if type(skip) == list:
        for fp in dir_path.iterdir():
            if (fp.name not in skip) and fp.match(name_match):
                p_info = load_passby_info(fp)
                if p_info is not None:
                    passby_list.append(p_info)
            #else:
            #    logger.warning("Skip  {}.".format(fp.name))
                    # return
        return bem_d, passby_list
    else:
        raise TypeError("skip has to be a list.")

def load_xl2logs_info(path):
    rec_info = {}
    log_measurement = parse_broadband_file(str(path))['Measurement']
    rec_info['stop_rec'] = log_measurement['End']
    rec_info['start_rec'] = log_measurement['Start']
    rec_info['path'] = path
    return  rec_info


def load_xl2logs_from_dir(dir_path):
    rec_list=[]
    for fp in dir_path.iterdir():
        if fp.match("*123_Log.txt"):
            rec_info =load_xl2logs_info(fp)
            rec_list.append(rec_info)
    return rec_list


##########################
##########################

def max_duration(rec_passby_list, max_duration):
    index=[]
    for i, info in enumerate(rec_passby_list):
        start_stop_dt = (info['stop_rec'] - info['start_rec'])
        dt = start_stop_dt.total_seconds()
        if dt > max_duration:
            logger.warning("Total seconds: {}  for passby {} at index {}.".format(dt,info['path'].name,i))
            index.append(i)
    return index

def test_XL2_duration(xl2_data_path,duration, delete=False):
    logger.info("Load xl2 logs from {}.".format(xl2_data_path))
    rec_list = load_xl2logs_from_dir(xl2_data_path)
    if len(rec_list) == 0:
        raise Exception("No records found in {}.".format(xl2_data_path))
    else:
        logger.info("Number of XL2 records found: {}.".format(len(rec_list)))
    outliers = max_duration(rec_list,duration)
    outliers= [rec_list[i]['path'] for i in outliers]
    logger.info("{} XL2 logs with duration > than {}.".format(len(outliers),duration))
    if delete:
        delete_files(outliers)

def test_passby_duration(passby_path, duration, delete=False):
    logger.info("Load passbys from {}.".format(passby_path))
    bem, passby_list = load_passby_info_from_dir(passby_path,  "*passby.json")
    if len(passby_list) == 0:
        raise Exception("No valid passby found in {}.".format(passby_path))
    else:
        logger.info("Number of passby found: {}.".format(len(passby_list)))
    outliers = max_duration(passby_list,duration)
    logger.info("{} passby with duration > than {}.".format(len(outliers),duration))
    outliers= [passby_list[i]['path'] for i in outliers]
    if delete:
        delete_files(outliers)

def test_passby_time_corrrection(passby_path, max_correction, delete=False):
    logger.info("Load passbys from {}.".format(passby_path))
    bem, passby_list = load_passby_info_from_dir(passby_path, logger, "*passby.json")
    if len(passby_list) == 0:
        raise Exception("No valid passby found in {}.".format(passby_path))
    else:
        logger.info("Number of passby found: {}.".format(len(passby_list)))
        out = []
        approx_time_correction = [p['xl2_time_correction'].total_seconds() for p in passby_list]
        print(pd.Series(approx_time_correction).describe())
        avg = pd.Series(approx_time_correction).mean()
        for tc, p in zip(approx_time_correction, passby_list):
            if abs(tc - avg) > max_correction:
                print("time correction: {},  passby {} ".format(tc, p['path']))
                out.append(p['path'])

        return passby_list[0]['xl2_time_correction'], out

    time_correction, outlier = approx_time_correction(passby_list_f, outlier_th=10)
##########################
##########################
#assign
def has_time_overlap(A_start, A_end, B_start, B_end):
    latest_start = max(A_start, B_start)
    earliest_end = min(A_end, B_end)
    return latest_start <= earliest_end

def assign_xl2rec_to_passby(start_rec, stop_rec, xl2_time_correction, xl2_records, **kwargs):
    assigned_xl2_rec=[]
    dt = datetime.timedelta(seconds=2)
    start_rec -= dt
    stop_rec -= dt
    for rec_info in xl2_records:
        xl2_start=rec_info['start_rec']+xl2_time_correction
        xl2_stop=rec_info['stop_rec']+xl2_time_correction
        if has_time_overlap(start_rec, stop_rec, xl2_start, xl2_stop):
            assigned_xl2_rec.append(rec_info)
    return assigned_xl2_rec

def update_passby_with_xl2_path(path, xl2_filename_root):
    with path.open('r+') as file:
        passby = json.load(file)
    passby["xl2_filename_root"] = xl2_filename_root
    with path.open('w+') as file:
        json.dump(passby,file,sort_keys=True, indent=2,default=str)

def create_passby_dir_and_move_xl2_files(passby,xl2_p):
    xl2_name_root= passby['']
    passby_path = passby['path'].parent
    dir_name = passby['path'].name.replace(".json","")
    xl2_paths = []

def assign(passby_path,xl2_data_path,logger):
    logger.info("Load passbys from {}.".format(passby_path))
    bem, passby_list = load_passby_info_from_dir(passby_path, logger, "*passby.json")
    if len(passby_list) == 0:
        raise Exception("No valid passby found in {}.".format(passby_path))
    else:
        logger.info("Number of passby found: {}.".format(len(passby_list)))
    ##
    logger.info("Load xl2 logs from {}.".format(xl2_data_path))
    rec_list = load_xl2logs_from_dir(xl2_data_path)
    if len(rec_list) == 0:
        raise Exception("No records found in {}.".format(xl2_data_path))
    else:
        logger.info("Number of XL2 records found: {}.".format(len(rec_list)))

    # assignement
    logger.info("Start assigning XL2rec to passby.")
    assigned_passby = {}
    assigned, not_assigned, not_correctly_assigned = 0, 0, 0
    for p in passby_list:
        assigned_recs = assign_xl2rec_to_passby(**p, xl2_records=rec_list)
        n_assignements = len(assigned_recs)
        if n_assignements == 0:
            not_assigned += 1
            logger.warning("Not assigned: {}, {}.".format(p['path'].parent.parent.name, p['path'].name))
        elif n_assignements == 1:
            xl2_filename_root = p["xl2_file_path"].name.replace("_123_Log.txt","")
            assigned_passby[p["path"].name] = {"xl2_filename_root": xl2_filename_root,
                                               "xl2_time_correction": p['xl2_time_correction']}
            update_passby_with_xl2_path(p["path"], xl2_filename_root)
            assigned += 1
        elif n_assignements > 1:
            not_correctly_assigned += 1

    logger.info("Correctly assigned {}".format(assigned))
    logger.warning("Not assigned {}".format(not_assigned))
    logger.warning("Not correctly assigned {}".format(not_correctly_assigned))
    return assigned_passby
######################
######################

def copy():
    pass


if __name__=="__main__":
    parser = argparse.ArgumentParser(prog='PROG', description ='Tool für Zuordnung zwischen XL2-Daten und Passby Daten.')
    subparsers = parser.add_subparsers(help='sub-command help')

    parser_XL2_duration = subparsers.add_parser('test_XL2_duration', help='')
    parser_XL2_duration.add_argument('xl2_data_path', type=lambda p: Path(p).absolute(), help='Pfad von XL2 Data.')
    parser_XL2_duration.add_argument('duration', type=int, help='Dauer in Sekunden.')
    parser_XL2_duration.add_argument('-delete', action='store_true', help='Lösche XL2 files länger als duration')
    parser_XL2_duration.set_defaults(func=test_XL2_duration)

    parser_passby_duration = subparsers.add_parser('test_passby_duration', help='')
    parser_passby_duration.add_argument('passby_path', type=lambda p: Path(p).absolute(), help='Pfad von passby Data.')
    parser_passby_duration.add_argument('duration', type=int, help='Dauer in Sekunden.')
    parser_passby_duration.add_argument('-delete', action='store_true', help='Lösche passby files länger als duration')
    parser_passby_duration.set_defaults(func=test_passby_duration)

    parser_passby_correction = subparsers.add_parser('test_passby_correction', help='')
    parser_passby_correction.add_argument('passby_path', type=lambda p: Path(p).absolute(), help='Pfad von passby Data.')
    parser_passby_correction.add_argument('max_correction', type=int, help='Correction in Sekunden.')
    parser_passby_correction.add_argument('-delete', action='store_true', help='Lösche passby files mit grösse correction')
    parser_passby_correction.set_defaults(func=test_passby_time_corrrection)

    parser_assign = subparsers.add_parser('assign', help='')
    parser_assign.add_argument('passby_path', type=lambda p: Path(p).absolute(), help='Pfad von passby Data.')
    parser_assign.add_argument('xl2_data_path', type=lambda p: Path(p).absolute(), help='Pfad von XL2 Data.')
    parser_assign.add_argument('-update_passby', action='store_true', help='')
    parser_assign.set_defaults(func=assign)

    parser_copy = subparsers.add_parser('copy', help='')
    parser_copy.add_argument('passby_path', type=lambda p: Path(p).absolute(), help='Pfad von passby Data.')
    parser_copy.add_argument('xl2_data_path', type=lambda p: Path(p).absolute(), help='Pfad von XL2 Data.')
    parser_copy.add_argument('-move', action='store_true', help='')
    parser_copy.set_defaults(func=copy)


    args = parser.parse_args()
    args_d= vars(args)
    func = args_d.pop('func')

    filename =Path(__file__).name.split(".py")[0]
    logger.info("Begin {}.py".format(filename))
    ##
    func(**vars(args))
    #finish
    logger.info("End {}".format(filename))