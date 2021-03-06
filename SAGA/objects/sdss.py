import os
import time
import re
from astropy import units as u
from casjobs import CasJobs
from ..utils import gzip_compress, get_logger

__all__ = ['extract_sdss_specs', 'run_casjob', 'construct_query']


def extract_sdss_specs(sdss):
    """
    Extract all objects that have SDSS spectra in a cleaned SDSS catalog.abs

    Parameters
    ----------
    sdss : astropy.table.Table

    Returns
    -------
    sdss_specs : astropy.table.Table
    """
    raise NotImplementedError
    return sdss_specs


def run_casjob(query, db_table_name, output_path, compress=True, overwrite=False, verbose=True):
    """
    Run single casjob and download casjob output

    Parameters
    ----------
    query : str, output from construct_query
    output_path : str
    compress : bool, optional
    overwrite : bool, optional
    verbose : bool, optional

    Notes
    -----
    Follow these instructions to use `run_casjob`

    1. Install by Dan FM's casjobs (https://github.com/dfm/casjobs):
        pip install git+git://github.com/dfm/casjobs.git

    2. Get an account from  http://skyserver.sdss3.org/CasJobs/CreateAccount.aspx

    3. Edit your `.bashrc`:
        export CASJOBS_WSID='2090870927'   # get your WSID from site above
        export CASJOBS_PW='my password'
    """

    if not all(k in os.environ for k in ('CASJOBS_WSID', 'CASJOBS_PW')):
        raise ValueError('You are not setup to run casjobs')

    # USES POST
    cjob = CasJobs(base_url='http://skyserver.sdss.org/casjobs/services/jobs.asmx', request_type='POST', context='DR14')

    output_path_tmp = output_path + '.tmp' if compress else output_path

    log = get_logger('INFO' if verbose else 'WARNING')

    # IF FILE DOESN"T ALREADY EXIST, SUBMIT JOB TO CAS
    if overwrite or not os.path.isfile(output_path):
        job_id = cjob.submit(query)
        code = None
        log.info('casjob ({}) submitted'.format(db_table_name))
        while code != 5:
            time.sleep(10)
            code, status = cjob.status(job_id)
            log.info('waiting for casjob ({}), current status: {} - {}'.format(db_table_name, code, status))

       # DOWNLOAD FILE AND REMOVE FROM CASJOBS DATABASE
        log.info('casjob ({}) finished, downloading data...'.format(db_table_name))
        cjob.request_and_get_output(db_table_name, 'FITS', output_path_tmp)
        cjob.drop_table(db_table_name)

        if compress:
            log.info('compressing output file...')
            gzip_compress(output_path_tmp, output_path)


def construct_query(db_table_name, ra, dec, radius=1.0):
    """
    Generates the query to send to the SDSS to get the full SDSS catalog around
    a target.

    Parameters
    ----------
    db_table_name : string
    ra : `Quantity` or float
        The center/host RA (iconn degrees if float)
    dec : `Quantity` or float
        The center/host Dec (in degrees if float)
    radius : `Quantity` or float
        The radius to search out to (in degrees if float)

    Returns
    -------
    query : str
        The SQL query to send to the SDSS skyserver
    """

    query_template = """
    SELECT  p.objId  as OBJID,
    p.ra as RA, p.dec as DEC,
    p.type as PHOTPTYPE,  dbo.fPhotoTypeN(p.type) as PHOT_SG,

    p.flags as FLAGS, p.clean,
    flags & dbo.fPhotoFlags('SATURATED') as SATURATED,
    flags & dbo.fPhotoFlags('BAD_COUNTS_ERROR') as BAD_COUNTS_ERROR,
    flags & dbo.fPhotoFlags('BINNED1') as BINNED1,
    flags & dbo.fPhotoFlags('TOO_FEW_GOOD_DETECTIONS') as TOO_FEW_GOOD_DETECTIONS,

    p.modelMag_u as u, p.modelMag_g as g, p.modelMag_r as r,p.modelMag_i as i,p.modelMag_z as z,
    p.modelMagErr_u as u_err, p.modelMagErr_g as g_err,
    p.modelMagErr_r as r_err,p.modelMagErr_i as i_err,p.modelMagErr_z as z_err,

    p.MODELMAGERR_U,p.MODELMAGERR_G,p.MODELMAGERR_R,p.MODELMAGERR_I,p.MODELMAGERR_Z,

    p.EXTINCTION_U, p.EXTINCTION_G, p.EXTINCTION_R, p.EXTINCTION_I, p.EXTINCTION_Z,
    p.DERED_U,p.DERED_G,p.DERED_R,p.DERED_I,p.DERED_Z,

    p.PETRORAD_U,p.PETRORAD_G,p.PETRORAD_R,p.PETRORAD_I,p.PETRORAD_Z,
    p.PETRORADERR_U,p.PETRORADERR_G,p.PETRORADERR_R,p.PETRORADERR_I,p.PETRORADERR_Z,

    p.DEVRAD_U,p.DEVRADERR_U,p.DEVRAD_G,p.DEVRADERR_G,p.DEVRAD_R,p.DEVRADERR_R,
    p.DEVRAD_I,p.DEVRADERR_I,p.DEVRAD_Z,p.DEVRADERR_Z,
    p.DEVAB_U,p.DEVAB_G,p.DEVAB_R,p.DEVAB_I,p.DEVAB_Z,

    p.CMODELMAG_U, p.CMODELMAGERR_U, p.CMODELMAG_G,p.CMODELMAGERR_G,
    p.CMODELMAG_R, p.CMODELMAGERR_R, p.CMODELMAG_I,p.CMODELMAGERR_I,
    p.CMODELMAG_Z, p.CMODELMAGERR_Z,

    p.PSFMAG_U, p.PSFMAGERR_U, p.PSFMAG_G, p.PSFMAGERR_G,
    p.PSFMAG_R, p.PSFMAGERR_R, p.PSFMAG_I, p.PSFMAGERR_I,
    p.PSFMAG_Z, p.PSFMAGERR_Z,

    p.FIBERMAG_U, p.FIBERMAGERR_U, p.FIBERMAG_G, p.FIBERMAGERR_G,
    p.FIBERMAG_R, p.FIBERMAGERR_R, p.FIBERMAG_I, p.FIBERMAGERR_I,
    p.FIBERMAG_Z, p.FIBERMAGERR_Z,

    p.FRACDEV_U, p.FRACDEV_G, p.FRACDEV_R, p.FRACDEV_I, p.FRACDEV_Z,
    p.Q_U,p.U_U, p.Q_G,p.U_G, p.Q_R,p.U_R, p.Q_I,p.U_I, p.Q_Z,p.U_Z,

    p.EXPAB_U, p.EXPRAD_U, p.EXPPHI_U, p.EXPAB_G, p.EXPRAD_G, p.EXPPHI_G,
    p.EXPAB_R, p.EXPRAD_R, p.EXPPHI_R, p.EXPAB_I, p.EXPRAD_I, p.EXPPHI_I,
    p.EXPAB_Z, p.EXPRAD_Z, p.EXPPHI_Z,

    p.FIBER2MAG_R, p.FIBER2MAGERR_R,
    p.EXPMAG_R, p.EXPMAGERR_R,

    p.PETROR50_R, p.PETROR90_R, p.PETROMAG_R,
    p.expMag_r + 2.5*log10(2*PI()*p.expRad_r*p.expRad_r + 1e-20) as SB_EXP_R,
    p.petroMag_r + 2.5*log10(2*PI()*p.petroR50_r*p.petroR50_r) as SB_PETRO_R,

    ISNULL(w.j_m_2mass,9999) as J, ISNULL(w.j_msig_2mass,9999) as JERR,
    ISNULL(w.H_m_2mass,9999) as H, ISNULL(w.h_msig_2mass,9999) as HERR,
    ISNULL(w.k_m_2mass,9999) as K, ISNULL(w.k_msig_2mass,9999) as KERR,

    s.survey,
    ISNULL(s.z, -1) as SPEC_Z, ISNULL(s.zErr, -1) as SPEC_Z_ERR, ISNULL(s.zWarning, -1) as SPEC_Z_WARN,
    ISNULL(pz.z,-1) as PHOTOZ, ISNULL(pz.zerr,-1) as PHOTOZ_ERR

    FROM dbo.fGetNearbyObjEq({ra}, {dec}, {radarcmin}) n, PhotoPrimary p
    INTO mydb.{db_table_name}
    LEFT JOIN SpecObj s ON p.specObjID = s.specObjID
    LEFT JOIN PHOTOZ  pz ON p.ObjID = pz.ObjID
    LEFT join WISE_XMATCH as wx on p.objid = wx.sdss_objid
    LEFT join wise_ALLSKY as w on  wx.wise_cntr = w.cntr
    WHERE n.objID = p.objID
    """

    if isinstance(ra, u.Quantity):
        ra = ra.to(u.deg).value

    if isinstance(dec, u.Quantity):
        dec = dec.to(u.deg).value

    if isinstance(radius, u.Quantity):
        radarcmin = radius.to(u.arcmin).value
    else:
        radarcmin = (radius*u.deg).to(u.arcmin).value

    # ``**locals()`` means "use the local variable names to fill the template"
    q = query_template.format(**locals())
    q = re.sub(r'\s+', ' ', q).strip()
    return q
