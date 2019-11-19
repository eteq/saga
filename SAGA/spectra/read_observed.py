import logging
import os

import astropy.constants
import numpy as np
from astropy.coordinates import EarthLocation, SkyCoord
from astropy.io import fits
from astropy.io.ascii.cparser import CParserError  # pylint: disable=E0611
from astropy.table import Table, vstack
from astropy.time import Time
from easyquery import Query

from ..database import CsvTable, FitsTable
from .common import SPEED_OF_LIGHT, ensure_specs_dtype

__all__ = [
    "read_mmt",
    "read_aat",
    "read_aat_mz",
    "read_imacs",
    "read_wiyn",
    "read_deimos",
    "read_palomar",
]

# pylint: disable=logging-format-interpolation


def heliocentric_correction(
    fits_filepath,
    site_name,
    ra_name="RA",
    dec_name="DEC",
    time_name="MJD",
    ra_unit="hourangle",
    dec_unit="deg",
    time_format="mjd",
):
    hdr = fits.getheader(fits_filepath)
    sc = SkyCoord(hdr[ra_name], hdr[dec_name], unit=(ra_unit, dec_unit))
    obstime = Time(hdr[time_name], format=time_format)
    helio_corr = sc.radial_velocity_correction(
        "heliocentric", obstime=obstime, location=EarthLocation.of_site(site_name)
    )
    return helio_corr.to_value(astropy.constants.c), obstime  # pylint: disable=E1101


def read_generic_spectra(
    dir_path,
    extension,
    telname,
    usecols,
    n_cols_total,
    cuts=None,
    postprocess=None,
    midprocess=None,
    **kwargs
):

    names = [usecols.get(i + 1, "_{}".format(i)) for i in range(n_cols_total)]
    exclude_names = [n for n in names if n.startswith("_")]

    output = []

    for f in os.listdir(dir_path):
        if not f.endswith(extension):
            continue
        if "conflicted copy" in f:
            logging.warning(
                "SKIPPING spectra file {}/{} - it's a conflicted copy; check if something went wrong!".format(
                    dir_path, f
                )
            )
            continue
        try:
            this = Table.read(
                os.path.join(dir_path, f),
                format="ascii.fast_no_header",
                guess=False,
                names=names,
                exclude_names=exclude_names,
                **kwargs,
            )
        except (IOError, CParserError) as e:
            logging.warning(
                "SKIPPING spectra file {}/{} - could not read or parse\n{}".format(
                    dir_path, f, e
                )
            )
            continue
        this = ensure_specs_dtype(this, skip_missing_cols=True)
        this = Query(cuts).filter(this)
        if not len(this):
            continue
        if "MASKNAME" not in this.colnames:
            this["MASKNAME"] = f
        if midprocess:
            this = midprocess(this)
        output.append(this)

    output = vstack(output, "exact")
    output["TELNAME"] = telname
    if postprocess:
        output = postprocess(output)

    return ensure_specs_dtype(output)


def read_mmt(dir_path, before_time=None):

    usecols = {
        2: "RA",
        3: "DEC",
        4: "mag",
        5: "SPEC_Z",
        6: "SPEC_Z_ERR",
        7: "ZQUALITY",
        8: "SPECOBJID",
    }
    cuts = Query("mag != 0", "ZQUALITY >= 0", (lambda x: x != "0", "SPECOBJID"))

    def midprocess(t):
        fits_filepath = os.path.join(
            dir_path, t["MASKNAME"][0].replace(".zlog", ".fits.gz")
        )
        try:
            corr, obstime = heliocentric_correction(
                fits_filepath, "mmt", "RA", "DEC", "MJD"
            )
        except IOError:
            t["HELIO_CORR"] = False
        else:
            if before_time is not None and obstime > before_time:
                return
            t["SPEC_Z"] += corr
            t["HELIO_CORR"] = True
        return t

    def postprocess(t):
        del t["mag"]
        t["RA"] *= 15.0
        return t

    return read_generic_spectra(
        dir_path, ".zlog", "MMT", usecols, 11, cuts, postprocess, midprocess
    )


def read_aat(dir_path, before_time=None):

    usecols = {2: "RA", 3: "DEC", 5: "SPEC_Z", 7: "ZQUALITY", 8: "SPECOBJID"}
    cuts = Query("ZQUALITY >= 0", (lambda x: x != "0", "SPECOBJID"))

    def midprocess(t):
        fits_filepath = os.path.join(
            dir_path, t["MASKNAME"][0].replace(".zlog", ".fits.gz")
        )
        try:
            corr, obstime = heliocentric_correction(
                fits_filepath, "sso", "MEANRA", "MEANDEC", "UTMJD"
            )
        except IOError:
            t["HELIO_CORR"] = False
        else:
            if before_time is not None and obstime > before_time:
                return
            t["SPEC_Z"] += corr
            t["HELIO_CORR"] = True
        return t

    def postprocess(t):
        t["SPEC_Z_ERR"] = 10 / SPEED_OF_LIGHT
        return t

    return read_generic_spectra(
        dir_path, ".zlog", "AAT", usecols, 11, cuts, postprocess, midprocess
    )


def read_aat_mz(dir_path, before_time=None):

    usecols = {3: "RA", 4: "DEC", 13: "SPEC_Z", 14: "ZQUALITY", 1: "SPECOBJID"}
    cuts = Query("ZQUALITY >= 0")

    def midprocess(t):
        fits_filepath = os.path.join(
            dir_path, t["MASKNAME"][0].replace(".mz", ".fits.gz")
        )
        try:
            corr, obstime = heliocentric_correction(
                fits_filepath, "sso", "MEANRA", "MEANDEC", "UTMJD"
            )
        except IOError:
            t["HELIO_CORR"] = False
        else:
            if before_time is not None and obstime > before_time:
                return
            t["SPEC_Z"] += corr
            t["HELIO_CORR"] = True
        return t

    def postprocess(t):
        t["RA"] *= 180.0 / np.pi
        t["DEC"] *= 180.0 / np.pi
        t["SPEC_Z_ERR"] = 10 / SPEED_OF_LIGHT
        return t

    return read_generic_spectra(
        dir_path,
        ".mz",
        "AAT",
        usecols,
        15,
        cuts,
        postprocess,
        midprocess,
        delimiter=",",
    )


def read_imacs(dir_path):

    usecols = {
        2: "RA",
        3: "DEC",
        5: "SPEC_Z",
        6: "SPEC_Z_ERR",
        7: "ZQUALITY",
        8: "SPECOBJID",
        11: "MASKNAME",
    }
    cuts = Query("ZQUALITY >= 1", (lambda x: x != "0", "SPECOBJID"))
    return read_generic_spectra(dir_path, ".zlog", "IMACS", usecols, 12, cuts)


def read_wiyn(dir_path):

    output = []

    for f in os.listdir(dir_path):
        if not f.endswith(".fits.gz"):
            continue
        this = FitsTable(os.path.join(dir_path, f)).read()[
            ["RA", "DEC", "ZQUALITY", "FID", "Z", "Z_ERR"]
        ]
        this = Query("ZQUALITY >= 1").filter(this)
        this["MASKNAME"] = f
        output.append(this)

    output = vstack(output, "exact")

    output.rename_column("FID", "SPECOBJID")
    output.rename_column("Z", "SPEC_Z")
    output.rename_column("Z_ERR", "SPEC_Z_ERR")
    output["TELNAME"] = "WIYN"

    sc = SkyCoord(output["RA"], output["DEC"], unit=("hourangle", "deg"))
    output["RA"] = sc.ra.deg
    output["DEC"] = sc.dec.deg
    del sc

    return ensure_specs_dtype(output)


def read_deimos():
    data = {
        "RA": [247.825839103498, 221.86742, 150.12470],
        "DEC": [20.210825313885, -0.28144459, 32.561687],
        "MASKNAME": ["deimos2014", "deimos2016-DN1", "deimos2016-MD1"],
        "SPECOBJID": [1, 1, 1],
        "SPEC_Z": [2375 / SPEED_OF_LIGHT, 0.056, 1.08],
        "SPEC_Z_ERR": [0.001, 0.001, 0.001],
        "ZQUALITY": [4, 4, 4],
        "TELNAME": ["DEIMOS", "DEIMOS", "DEIMOS"],
    }
    return ensure_specs_dtype(Table(data))


def read_palomar(file_path):
    if not hasattr(file_path, "read"):
        file_path = CsvTable(file_path)

    cols = [
        "SPECOBJID",
        "RA",
        "DEC",
        "SPEC_Z",
        "SPEC_Z_ERR",
        "ZQUALITY",
        "MASKNAME",
        "TELNAME",
        "HELIO_CORR",
    ]
    specs = file_path.read()[cols]

    return ensure_specs_dtype(specs)
