import os
import sys
import logging
import gzip
import shutil
import requests
import numpy as np
from easyquery import Query
from astropy.coordinates import SkyCoord
from astropy import units as u


def get_logger(level='WARNING'):
    log = logging.getLogger()
    log.setLevel(level if isinstance(level, int) else getattr(logging, level))
    logFormatter = logging.Formatter('[%(levelname)-5.5s][%(asctime)s] %(message)s')
    consoleHandler = logging.StreamHandler(sys.stdout)
    consoleHandler.setFormatter(logFormatter)
    log.addHandler(consoleHandler)
    return log


def get_decals_viewer_image(ra, dec, pixscale=0.2, layer='sdssco', size=256, out=None):
    url = 'http://legacysurvey.org/viewer-dev/jpeg-cutout/?ra={ra}&dec={dec}&pixscale={pixscale}&layer={layer}&size={size}'.format(**locals())
    content = requests.get(url).content
    if out is not None:
        if not out.lower().endswith('.jpg'):
            out += '.jpg'
        with open(out, 'wb') as f:
            f.write(content)
    return content


def gzip_compress(path, out_path=None, delete_original=True):
    if out_path is None:
        out_path = path + '.gz'

    with open(path, 'rb') as f_in, gzip.open(out_path, 'wb') as f_out:
        shutil.copyfileobj(f_in, f_out)

    if delete_original:
        os.unlink(path)

    return out_path


def join_table_by_coordinates(table, table_to_join,
                              columns_to_join=None, columns_to_rename=None,
                              max_distance=1.0/3600.0, missing_value=np.nan,
                              table_ra_name='RA', table_dec_name='DEC',
                              table_to_join_ra_name='RA',
                              table_to_join_dec_name='DEC'):
    """
    join two table by matching the sky coordinates

    Examples
    --------
    wise_cols = ('W1_MAG', 'W1_MAG_ERR', 'W2_MAG', 'W2_MAG_ERR')
    cols_rename = {'W1_MAG':'W1', 'W1_MAG_ERR':'W1ERR', 'W2_MAG':'W2', 'W2_MAG_ERR':'W2ERR'}
    join_table_by_coordinates(base, wise, wise_cols, cols_rename)
    """

    t1 = table
    t2 = table_to_join

    sc = SkyCoord(table[table_ra_name], table[table_dec_name], unit='deg')
    sc_to_join = SkyCoord(table_to_join[table_to_join_ra_name],
                          table_to_join[table_to_join_dec_name], unit='deg')

    if not hasattr(max_distance, 'unit'):
        max_distance = max_distance*u.deg
    idx1, idx2, _ = sc_to_join.search_around_sky(sc, max_distance)

    n_matched = len(idx1)

    if n_matched:
        if columns_to_join is None:
            columns_to_join = t2.colnames

        if columns_to_rename is None:
            columns_to_rename = dict()

        if isinstance(missing_value, dict):
            missing_value_dict = missing_value
            missing_value = np.nan
        else:
            missing_value_dict = dict()

        for c2 in columns_to_join:
            c1 = columns_to_rename.get(c2, c2)
            if c1 not in t1:
                t1[c1] = missing_value_dict.get(c1, missing_value)
            t1[c1][idx1] = t2[c2][idx2]

    return n_matched


def fill_values_by_query(table, query, values_to_fill):
    """

    Examples
    --------
    fill_values_by_query(table, 'OBJID == 1237668367995568266',
                         {'SPEC_Z': 0.21068, 'TELNAME':'SDSS', 'MASKNAME':'SDSS'})
    """
    mask = Query(query).mask(table)
    n_matched = np.count_nonzero(mask)

    if n_matched:
        for c, v in values_to_fill.items():
            table[c][mask] = v

    return n_matched
