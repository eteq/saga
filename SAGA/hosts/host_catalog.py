"""
SAGA.host.host_catalog

This file defines the HostCatalog class
"""

class HostCatalog(object):
    """
    This class provides a high-level interface to access host catalogs
    (also known as "host list" and "master list", while the latter is not supported yet)

    Parameters
    ----------
    database : SAGA.Database object

    Returns
    -------
    host_catalog : SAGA.HostCatalog object

    Examples
    --------
    >>> import SAGA
    >>> saga_database = SAGA.Database('/path/to/SAGA/Dropbox')
    >>> saga_hosts = SAGA.HostCatalog(saga_database)
    >>> hosts_no_flag = saga_hosts.load('no_flags')
    >>> hosts_no_sdss_flag = saga_hosts.load('no_sdss_flags')

    Here hosts_no_flag and hosts_no_sdss_flag are astropy tables.

    >>> saga_hosts.resolve_id('AnaK')
    [61945]

    >>> saga_hosts.id_to_name(61945)
    'AnaK'
    """
    _paper1_complete_hosts = (166313, 147100, 165536, 61945, 132339, 149781, 33446, 150887)
    _paper1_incomplete_hosts = (161174, 85746, 145729, 140594, 126115, 13927, 137625, 129237)

    def __init__(self, database):
        self._database = database
        self._all_host_ids = self.load()['NSAID'].tolist()

        t = self._database['hosts_named'].read()
        self._host_name_to_id = dict(zip((n.lower() for n in t['SAGA']), t['NSA']))
        self._host_id_to_name = dict(zip(t['NSA'], t['SAGA']))


    def resolve_id(self, hosts):
        """
        Get a list of host IDs from SAGA names or some short-hand names (e.g. 'paper1')

        Currently supports SAGA names and "all", "paper1", paper1_complete",
        and "paper1_incomplete"

        Parameters
        ----------
        hosts : int, str, list
            host names/IDs or a list of host names/IDs

        Returns
        -------
        host_ids : list
            a list of host IDs. The returned value is always a list

        Examples
        --------
        >>> saga_hosts.resolve_id('paper1_complete')
        [166313, 147100, 165536, 61945, 132339, 149781, 33446, 150887]

        >>> saga_hosts.resolve_id('AnaK')
        [61945]

        """
        try:
            hosts = int(hosts)
        except(TypeError, ValueError):
            pass
        else:
            return [hosts]

        try:
            hosts = hosts.lower()
        except AttributeError:
            pass
        else:
            if hosts == 'all':
                return self._all_host_ids
            elif hosts == 'paper1_complete':
                return list(self._paper1_complete_hosts)
            elif hosts == 'paper1_incomplete':
                return list(self._paper1_incomplete_hosts)
            elif hosts == 'paper1':
                return list(self._paper1_complete_hosts + self._paper1_incomplete_hosts)
            elif hosts.lower() in self._host_name_to_id:
                return [self._host_name_to_id[hosts.lower()]]
            else:
                raise ValueError('cannot resolve {}'.format(hosts))

        out = []
        for host in hosts:
            out.extend(self.resolve_id(host))
        return out


    def id_to_name(self, host_id):
        """
        Get SAGA host name from a NSA ID.
        Note that we are moving away from NSA ID. Use caution with this function!

        Parameters
        ----------
        host_id : int

        Returns
        -------
        host_saga_name : str
        """
        return self._host_id_to_name.get(host_id)


    def load(self, host_type='no_flags', reload=False):
        """
        load a host catalog

        Parameters
        ----------
        host_type : str, optional
            Currently it can be "no_flags" or "no_sdss_flags"

        reload : bool, optional
            If set to True, do not use tha cached table. Default is False.

        Returns
        -------
        hosts : astropy.table.Table

        Examples
        --------
        >>> hosts_no_flag = saga_hosts.load('no_flags')
        >>> hosts_no_sdss_flag = saga_hosts.load('no_sdss_flags')
        """
        return self._database['hosts_{}'.format(host_type)].read(reload=reload)
