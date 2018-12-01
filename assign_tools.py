import json
from NTiXL2.ntixl2.xl2parser import parse_broadband_file
import datetime
from pyLRM.passby import sync_str_to_datetime,xl2_time_correction
from pathlib import Path
import argparse
import logging
import sys,os
import shutil
import pandas as pd
from bokeh.models import ColumnDataSource,Plot, LinearAxis, Grid, DatetimeTickFormatter,Range1d,LabelSet
from bokeh.plotting import figure, show, output_notebook
import bokeh

logging.basicConfig( stream=sys.stdout,format='%(funcName)-15s: %(message)s',level=logging.INFO)
logger = logging.getLogger()


def delete_files(file_path_list):
    for f in file_path_list:
        logger.info("delete {}.".format(f.as_posix()))
        os.remove(f.as_posix())

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
        xl2_filename = p.get("xl2_filename_root")
        if xl2_filename is not None:
            p_info['xl2_filename_root'] = xl2_filename
    return p_info


def load_passby_info_from_dir(passby_path, name_match ="*passby.json"):
    passby_list = []
    logger.info("Load passbys from {}.".format(passby_path))

    #if "bemerkung.json" in [f.name for f in passby_path.iterdir()]:
    #    with passby_path.joinpath("bemerkung.json").open('r+') as file:
    #        bem_d = json.load(file)
    #        skip = bem_d.get('skip', [])
    #    logger.info("bemerkung.json file found")
    #    logger.info("{}\n--------------".format(json.dumps(bem_d, indent=2)))
    #else:
    #    bem_d=None
    #    skip=[]

    for fp in passby_path.iterdir():
        if fp.match(name_match):
            p_info = load_passby_info(fp)
            if p_info is not None:
                passby_list.append(p_info)

    if len(passby_list) == 0:
        raise Exception("No valid passby found in {}.".format(passby_path))
    logger.info("Number of passby found: {}.".format(len(passby_list)))
    return passby_list


def load_xl2logs_info(path):
    rec_info = {}
    log_measurement = parse_broadband_file(str(path))['Measurement']
    rec_info['stop_rec'] = log_measurement['End']
    rec_info['start_rec'] = log_measurement['Start']
    rec_info['path'] = path
    rec_info['xl2_filename_root'] = path.name.replace("_123_Log.txt", "")
    return  rec_info


def load_xl2logs_from_dir(xl2_data_path):
    rec_list=[]
    logger.info("Load xl2 logs from {}.".format(xl2_data_path))
    for fp in xl2_data_path.iterdir():
        if fp.match("*123_Log.txt"):
            rec_info =load_xl2logs_info(fp)
            rec_list.append(rec_info)
    if len(rec_list) == 0:
        raise Exception("No records found in {}.".format(xl2_data_path))
    else:
        logger.info("Number of XL2 records found: {}.".format(len(rec_list)))
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
    rec_list = load_xl2logs_from_dir(xl2_data_path)
    outliers = max_duration(rec_list,duration)
    outliers= [rec_list[i]['path'] for i in outliers]
    logger.info("{} XL2 logs with duration > than {}.".format(len(outliers),duration))
    if delete:
        delete_files(outliers)

def test_passby_duration(passby_path, duration, delete=False):
    passby_list = load_passby_info_from_dir(passby_path,  "*passby.json")
    outliers = max_duration(passby_list,duration)
    logger.info("{} passby with duration > than {}.".format(len(outliers),duration))
    outliers= [passby_list[i]['path'] for i in outliers]
    if delete:
        delete_files(outliers)

def test_passby_time_corrrection(passby_path, max_correction, max_deviation, delete=False):
    passby_list = load_passby_info_from_dir(passby_path,  "*passby.json")
    time_correction = []
    remaining_pb =[]
    out = []
    logger.info("Start max correction test:")
    for p in passby_list:
        dt = p['xl2_time_correction'].total_seconds()
        if abs(dt)< max_correction:
            time_correction.append(dt)
            remaining_pb.append(p)
        else:
            out.append(p['path'])
            logger.warning("{} correction {} bigger than {}.".format(p['path'].as_posix(),dt,max_correction))

    df = pd.Series(time_correction)
    mean = df.mean()
    time_correction=[]
    logger.info("Start max deviation test:")
    for p in remaining_pb:
        err = p['xl2_time_correction'].total_seconds()-mean
        if abs(err)> max_deviation:
            out.append(p['path'])
            logger.warning("{} correction error {} bigger than {}.".format(p['path'].as_posix(),int(err),max_deviation))
        else:
            time_correction.append(p['xl2_time_correction'].total_seconds())
    df = pd.Series(time_correction)
    logger.info("Stats: \n{}".format(str(df.describe())))

    if delete:
        delete_files(out)
    return df.mean()

##########################
##########################
#assign
def has_time_overlap(A_start, A_end, B_start, B_end):
    latest_start = max(A_start, B_start)
    earliest_end = min(A_end, B_end)
    return latest_start <= earliest_end

def assign_xl2rec_to_passby(start_rec, stop_rec, xl2_time_correction, xl2_records, **kwargs):
    """ return index of xl2 records"""
    assigned_xl2_rec_index=[]
    dt = datetime.timedelta(seconds=2)
    start_rec -= dt
    stop_rec -= dt
    for i, rec_info in enumerate(xl2_records):
        xl2_start=rec_info['start_rec']+xl2_time_correction
        xl2_stop=rec_info['stop_rec']+xl2_time_correction
        if has_time_overlap(start_rec, stop_rec, xl2_start, xl2_stop):
            assigned_xl2_rec_index.append(i)
    return assigned_xl2_rec_index

def update_passby_with_xl2_path(path, xl2_filename_root):
    with path.open('r+') as file:
        passby = json.load(file)
    passby["xl2_filename_root"] = xl2_filename_root
    with path.open('w+') as file:
        json.dump(passby,file, sort_keys=True, indent=2, default=str)

def assign_func(passby_list,rec_list):
    assigned = []
    rec_list=rec_list.copy()
    remaining_passby=[]
    assigned_rec = []
    not_correctly_assigned = 0
    for p in passby_list:
        assigned_recs_index = assign_xl2rec_to_passby(**p, xl2_records=rec_list)
        n_assignements = len(assigned_recs_index)
        if n_assignements == 0:
            remaining_passby.append(p)
            logger.warning("Not assigned: {}, {}.".format(p['path'].parent.parent.name, p['path'].name))
        elif n_assignements == 1:
            rec = rec_list.pop(assigned_recs_index[0])
            assigned.append((p,rec))
            assigned_rec.append(rec)
        elif n_assignements > 1:
            not_correctly_assigned += 1

    logger.info("Correctly assigned {}".format(len(assigned)))
    logger.info("Used recs {}".format(len(assigned_rec)))
    logger.warning("Not assigned {}".format(len(remaining_passby)))
    logger.warning("Not correctly assigned {}".format(not_correctly_assigned))
    return assigned,remaining_passby, rec_list


def plot_zuordnung(assigned, remaining_passby, remaining_rec, labels=True, **kwargs):
    y_range = ["records", "passby"]  # ,"not assigned passby"]
    plt = figure(
        title="Zuordnung zwische passby und XL2 records.",
        y_range=y_range,
        x_axis_type="datetime",
        x_axis_label='XL2 uncorrected time',
        tools=['xwheel_zoom', 'xpan'], active_scroll='xwheel_zoom', active_drag='xpan',
        **kwargs)
    plt.xaxis.formatter = DatetimeTickFormatter(days=["%m/%d"], months=["%m/%d"], hours=["%m/%d %H:%M"],
                                                hourmin=["%m/%d %H:%M"], minutes=["%m/%d %H:%M"],
                                                seconds=["%m/%d %H:%M:%S"], minsec=["%m/%d %H:%M:%S"])
    # data
    f_pb = lambda pb: {'x0': pb['start_rec'] - pb['xl2_time_correction'],
                       'x1': pb['stop_rec'] - pb['xl2_time_correction'], 'y0': "passby", 'y1': "passby",
                       'name': pb['path'].name.replace('_passby.json', '')}
    f_rec = lambda r: {'x0': r['start_rec'], 'x1': r['stop_rec'], 'y0': "records", 'y1': "records",
                       'name': r['xl2_filename_root']}

    plt.segment(x0="x0", y0="y0", x1="x1", y1="y1", line_width=20, color="red",
                source=ColumnDataSource(pd.DataFrame([f_pb(pb) for pb in remaining_passby]))
                )
    plt.segment(x0="x0", y0="y0", x1="x1", y1="y1", line_width=20, color="blue",
                source=ColumnDataSource(pd.DataFrame([f_pb(pb) for pb, r in assigned]))
                )
    # passby
    plt.segment(x0="x0", y0="y0", x1="x1", y1="y1", line_width=20, color="red",
                source=ColumnDataSource(pd.DataFrame([f_rec(r) for r in remaining_rec]))
                )
    plt.segment(x0="x0", y0="y0", x1="x1", y1="y1", line_width=20, color="blue",
                source=ColumnDataSource(pd.DataFrame([f_rec(r) for pb, r in assigned]))
                )

    if labels:
        plt.add_layout(LabelSet(x='x0', y='y0', text='name', level='glyph', x_offset=5, y_offset=10,
                                source=ColumnDataSource(pd.DataFrame([f_pb(pb) for pb in remaining_passby]))
                                ))
        plt.add_layout(LabelSet(x='x0', y='y0', text='name', level='glyph', x_offset=5, y_offset=10,
                                source=ColumnDataSource(pd.DataFrame([f_rec(r) for r in remaining_rec]))
                                ))
    return plt


def assign(passby_path,xl2_data_path,update_passby=False,plot=True):
    passby_list = load_passby_info_from_dir(passby_path, "*passby.json")
    rec_list = load_xl2logs_from_dir(xl2_data_path)
    # assignement
    logger.info("Start assigning XL2rec to passby.")
    assigned, remaining_passby, remaining_rec= assign_func(passby_list,rec_list)

    if update_passby:
        logger.info("update passby with xl2_filename_root.")
        for p,r in assigned:
            update_passby_with_xl2_path(p['path'], r['xl2_filename_root'])
    if plot:
        logger.info("generate plot.")
        p = plot_zuordnung(assigned, remaining_passby, remaining_rec, width=1500, height=200)
        bokeh.plotting.output_file(filename=passby_path.absolute().joinpath('plot.html').as_posix(),
                                   title='zuordnung_plot',mode='cdn')
        bokeh.io.save(p)



######################
######################

def copy_files(file_path_list, path_destination):
    if path_destination.is_dir():
        for f in file_path_list:
            new = shutil.copy(f.as_posix(), path_destination.as_posix())
            logger.info("File {} copied at {}.".format(f.as_posix(),new))
    else:
        raise Exception('destination_path {} is not a directory'.format(path_destination.as_posix()))

def passby_dir_name_and_file_to_move(passby, remaining_xl2):
    xl2_name_root= passby['xl2_filename_root']
    files_to_copy = [passby['path'].absolute()]
    dir_name = passby['path'].name.replace(".json","")
    index=[]
    for i,p in enumerate(remaining_xl2.copy()):
        if p.match("*{}*".format(xl2_name_root)):
            files_to_copy.append(p)
            remaining_xl2.remove(p)
    return dir_name, files_to_copy

def copy(passby_path,xl2_data_path,new_path):
    passby_list = load_passby_info_from_dir(passby_path, "*passby.json")
    flt_pb=[]
    for p in passby_list:
        try:
            p['xl2_filename_root']
        except:
            logger.warning("{} not assigned".format(p['path']))
        else:
            flt_pb.append(p)

    new_path.mkdir(exist_ok=True)
    logger.info("{} passby dir to create at {}.".format(len(flt_pb),new_path.as_posix()))
    xl2_data_paths=[p for p in xl2_data_path.iterdir()]
    for p in flt_pb:
        dir_name,files = passby_dir_name_and_file_to_move(p,xl2_data_paths)
        d = new_path.joinpath(dir_name)
        logger.info("create dir {}.".format(str(d)))
        d.mkdir(exist_ok=True)
        copy_files(files,d)





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
    parser_passby_correction.add_argument('max_correction', type=int, help='betrag maximale akzeptierte correction in Sekunden.')
    parser_passby_correction.add_argument('max_deviation', type=int, help='betrag maximale akzeptierte Abweichung.')
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
    parser_copy.add_argument('new_path', type=lambda p: Path(p).absolute(), help='Pfad wo das neue filesystem herstellt wird.')
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