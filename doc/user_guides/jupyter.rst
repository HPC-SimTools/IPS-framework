Jupyter
=======

The IPS Framework supports automatically creating Juypter-based workflows. If the IPS simulation is executed on a platform with JupyterHub installed, you can automatically add notebooks and data to your JupyterHub directory.

**Configuration File**

The following variables are additional variables which are mandatory for an IPS simulation wanting to utilize the Jupyter workflow. They are required and do not utilize any default values.

*PORTAL_URL* - This should be the hostname of the IPS web portal you are interacting with (do not include any subpath). The IPS Portal will associate your run with a specific ID, which is used on JupyterHub/JupyterLab .

*JUPYTERHUB_DIR* - This is the base directory for your JupyterHub or JupyterLab web server. This MUST be an absolute directory.

*JUPYTERHUB_URL* - This is the base URL for your JupyterHub web server, i.e. "https://yourdomain.com/lab/tree/var/www/jupyterlab"

It is recommended that you configure *INPUT_DIR* as well, and place any notebook templates as IPS input files.

**Configuration File - NERSC specific information**

The IPS Framework is agnostic as to *specific* JupyterHub implementations, but at time of writing we expect most users will be running simulations and viewing Jupyter Notebooks on NERSC. Below is some specific information about NERSC:

*JUPYTERHUB_DIR* - You can generally just set this to ${PSCRATCH}, which is an environment variable pre-set on NERSC systems.

*JUPYTERHUB_URL* - You can usually just set this to https://jupyter.nersc.gov/user/${USER}/perlmutter-login-node-base/lab/tree${PSCRATCH} . Some notes on this:

    - The "/user/${USER}" URL path authenticates through NERSC Shibboleth as ${USER} , so you will need to make sure that anyone who clicks on this URL can authenticate as the user or knows to replace the username with their own.
    - By default, the notebooks will be executed on the login nodes. If the notebooks should be executed on a different node, replace "perlmutter-login-node-base" with the appropriate node name.
    - The directory path after "/lab/tree" needs to have read and execute permissions for the NERSC Shibboleth user. For users to access the Jupyter Notebook through either JupyterHub OR directly on the server, you will have to manually `chmod 755` or `chmod 750` your $PSCRATCH/ipsframework/runs directory and set Unix group ownerships as necessary.

**Notebook Input File information**

You can load template notebooks in your input directory which can automatically generate analyses visible on a remote JupyterHub instance. The IPS Framework instance will copy your template notebook and add some initialization code in a new cell at the beginning.

In your template code, you can reference the variable `DATA_FILES` to load the current data mapping. This data mapping is a dictionary of timestamps (floating point) to filepaths of the data file.

**IPS Framework Usage**

To set up Jupyter integration, you will need to call "self.services.initialize_jupyter_notebook" inside of an IPS Component. These statements should only be executed once, for example in an "init" function. For example:

.. code-block:: python

    from ipsframework import Component

    SOURCE_NOTEBOOK_NAME='base_notebook.ipynb'

    class Driver(Component):
        def init(self, timestamp=0.0):
            # ...
            # assumes your notebooks are configured in the input directory
            # if you have an absolute path on the filesystem to your notebook, staging the input notebook is not required
            self.services.stage_input_files([SOURCE_NOTEBOOK_NAME])
            self.services.initialize_jupyter_notebook(
                dest_notebook_name='jupyterhub_visible_notebook.ipynb',
                source_notebook_path=SOURCE_NOTEBOOK_NAME,
            )
            # call self.services.initialize_jupyter_notebook for EACH notebook you want to initialize
            # ...

This code initializes JupyterHub to work with this run and contacts the web portal to associate a runid with this specific run.

---

For updating data files, we generally accomodate for two approaches: one where you want to multiple data files for each timestamp called, and one where you maintain multiple data files for a single timestamp but replace it per timestamp call.

For the approach where data files for multiple timestamps are maintained, the below code provides an example of loading it from a file which is regularly updated with the IPS state:

.. code-block:: python

    import os
    from ipsframework import Component

    class Monitor(Component):
        def step(self, timestamp=0.0):
            # assume that we have already written IPS state earlier into this file,
            # and that this file is updated per timestamp call
            # In this example, we just want to snapshot our IPS state and save it in our JupyterHub workflow
            data_file = f'{timestamp}_state.json' # get current data file
            self.services.add_analysis_data_file(
                current_data_file_path=data_file,
                timestamp=timestamp,
            )

If you do not set timestamp yourself, it will default to "0.0" .

Or, if you only want to maintain a single timestamp, set the "replace" flag to True:

.. code-block:: python

    import os
    from ipsframework import Component

    class Monitor(Component):
        def step(self, timestamp=0.0):
            # assume that we continually update our state
            data_file = 'state.json' # get current data file
            self.services.add_analysis_data_file(
                current_data_file_path=data_file,
                replace=True,
            )

"Replace" will allow you to completely overwrite an existing timestamp entry with new data. If you don't set the flag but try to overwrite a specific timestamp, a ValueError is raised.

Note that if you attempt to overwrite an existing data file without setting `replace=True`, a ValueError will be raised.

**JupyterHub Filesystem Notes**

Inside of ${JUPYTERHUB_DIR}/ipsframework/runs, a directory structure may look like this:

.. code-block:: bash
    
    .
    ├── https://example-portal-url.com
    └── https://lb.ipsportal.development.svc.spin.nersc.org/
        ├── 1
        │   ├── basic.ipynb
        │   ├── bokeh-plots.ipynb
        │   ├── data
        │   │   ├── 10.666666666666666_state.json
        │   │   ├── 1.0_state.json
        │   │   ├── 11.633333333333333_state.json
        │   │   ├── 12.6_state.json
        │   │   ├── 13.566666666666666_state.json
        │   │   ├── 14.533333333333333_state.json
        │   │   ├── 15.5_state.json
        │   │   ├── 16.46666666666667_state.json
        │   │   ├── 17.433333333333334_state.json
        │   │   ├── 18.4_state.json
        │   │   ├── 19.366666666666667_state.json
        │   │   ├── 1.9666666666666668_state.json
        │   │   ├── 20.333333333333332_state.json
        │   │   ├── 21.3_state.json
        │   │   ├── 22.266666666666666_state.json
        │   │   ├── 23.233333333333334_state.json
        │   │   ├── 24.2_state.json
        │   │   ├── 25.166666666666668_state.json
        │   │   ├── 26.133333333333333_state.json
        │   │   ├── 27.1_state.json
        │   │   ├── 28.066666666666666_state.json
        │   │   ├── 29.033333333333335_state.json
        │   │   ├── 2.9333333333333336_state.json
        │   │   ├── 30.0_state.json
        │   │   ├── 3.9_state.json
        │   │   ├── 4.866666666666667_state.json
        │   │   ├── 5.833333333333333_state.json
        │   │   ├── 6.8_state.json
        │   │   ├── 7.766666666666667_state.json
        │   │   ├── 8.733333333333334_state.json
        │   │   └── 9.7_state.json
        │   └── data_listing.py
        ├── 2
        │   ├── basic.ipynb
        |   ├── data
        │   │   └── 0.0_state.json
        │   └── data_listing.py
        ├── api_v1_notebook.ipynb
        └── api_v1.py

- The IPS Framework will only modify files inside of ${JUPYTERHUB_DIR}/ipsframework/runs/
- From this directory, runs are divided by specific web portal hostnames, as runids are determined by a web portal.
- From the ${JUPYTERHUB_DIR}/ipsframework/runs/${PORTAL_URL} directory, the directory tree will continue based on runids. Note that files titled `api_v*.py` and `api_v*_notebook.ipynb` will be added to this directory as well. These files may potentially be overwritten by the framework, but should always be done so in a backwards compatible manner.
- From the ${JUPYTERHUB_DIR}/ipsframework/runs/${PORTAL_URL}/${RUNID} directory, a few additional files will be added:
    - Notebooks generated from your input notebooks.
    - A `data_listing.py` Python module file which is imported from and which exports a dictionary containing a mapping of timestamps to data file names. Note that this file is likely to be modified during a run, do NOT change it yourself unless you're sure the run has been finalized.
    - A `data` directory which will contain all data files you added during the run. (Note that the data files are determined on the domain science side, and can be of any content-type, not just JSON.)

