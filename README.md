SAGA
====

This package contains code to access, create and edit SAGA data catalogs.

See the [SAGA Survey website](http://sagasurvey.org/) for details about SAGA.

## Installation

    pip install git+git://github.com/sagasurvey/saga.git


## Example Usage

```python
import SAGA
from SAGA import ObjectCuts as C

saga_database = SAGA.Database('/path/to/SAGA/data/folder')
saga_hosts = SAGA.HostCatalog(saga_database)
saga_objects = SAGA.ObjectCatalog(saga_database)

# load host list (no flags)
hosts_no_flag = saga_hosts.load()

# load host list (no SDSS flags)
hosts_no_sdss_flags = saga_hosts.load('no_sdss_flags')

# load all specs with some basic cuts
specs = saga_objects.load(has_spec=True, cuts=C.basic_cut)

# load base catalogs for all paper1 hosts with the same basic cuts into a list:
base_paper1 = list(saga_objects.load(hosts='paper1', cuts=C.basic_cut, iter_hosts=True))

# count number of satellites
for base in base_paper1:
    print(base['HOST_NSAID'][0], '# of satellites', C.is_sat.count(base))

# load all base catalogs with the same basic cuts into a list
base_all = list(saga_objects.load(cuts=C.basic_cut, iter_hosts=True))
```
