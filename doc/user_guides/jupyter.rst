Jupyter
=======

The IPS Framework supports automatically creating Jupyter-based workflows. You can automatically upload Jupyter Notebooks and associated data files to the IPS Portal, which will in turn upload these to the appropriate JupyterHub directory.

This guide covers two aspects of how to use Jupyter-based workflows:

1. What you will need to set up on the IPS Framework side. This mostly involves understanding the APIs the framework provides, and configuration you will need to include.
2. How the IPS Portal creates files on JupyterHub for you, and how you can utilize the IPS Analysis API in your Jupyter Notebook.

The IPS Analysis API is an _indexing_ tool for allowing runs to quickly find any child or ensemble runs associated with them, and to quickly find the locations of any data files included with a run. Loading the data from the file locations, and constructing visualizations from the data, is left up to the end user.

-------------
IPS Framework
-------------

**Environment Variables**

The following variables are additional variables which are mandatory for an IPS simulation wanting to utilize the Jupyter workflow. They are required and do not utilize any default values.

*PORTAL_URL* - This should be the hostname of the IPS web portal you are interacting with (do not include any subpath). The IPS Portal will associate your run with a specific ID, which is used on JupyterHub/JupyterLab .

*PORTAL_API_KEY* - To use the JupyterHub capabilities of the IPS Portal, an API key is required. This API key should not be committed directly to a public version control repository. It is recommended that you set this as an environment variable in the run.

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

For updating data files, we generally accommodate for two approaches: one where you want to multiple data files for each timestamp called, and one where you maintain multiple data files for a single timestamp but replace it per timestamp call. Both workflows utilize `self.services.add_analysis_data_files` .

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
            self.services.add_analysis_data_files(
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
            self.services.add_analysis_data_files(
                current_data_file_path=data_file,
                replace=True,
            )

"Replace" will allow you to completely overwrite an existing timestamp entry with new data. If you don't set the flag but try to overwrite a specific timestamp, a ValueError is raised.

Note that if you attempt to overwrite an existing data file without setting `replace=True`, the file will not be overwritten remotely. You can check your IPS log file for "Portal Error" statements.

**IPS Framework Jupyter API reference**

.. automethod:: ipsframework.services.ServicesProxy.initialize_jupyter_notebook
    :noindex:

.. automethod:: ipsframework.services.ServicesProxy.add_analysis_data_files
    :noindex:

----------
IPS Portal
----------

**IPS Notebook Analysis API Guide**

NOTE: while you can update the notebook on the Portal side, it's best to have the completed notebook ready on the Framework side.

The IPS Portal will generate a cell prior to your own notebook which initializes a variable called ``ips_analysis_api``, which contains a number of helper functions for finding specific data locations.

- ``ips_analysis_api.get_data()`` - this generates a generic IPS mapping - a mapping of floating-point timesteps to a list of data file paths (absolute). Note that your notebook will need to handle the actual loading of the data.
- ``ips_analysis_api.get_child_data()`` - this generates a mapping of child runids to the "generic IPS mapping" described above.
- ``ips_analysis_api.get_child_data_not_ensembles()`` - get the child runid mapping as described above, but only use child runids NOT associated with ensembles.
- ``ips_analysis_api.get_child_data_by_ensemble_names()`` - gets the child runid mapping as described above, but will only retrieve child runids associated with ensembles. You can further filter this by ensemble name by providing an optional list of component names and an optional list of ensemble names; for example, ``ips_analysis_api.get_child_data_by_ensemble_names(ensemble_names=['ensemble_name_1', 'ensemble_name_2'])`` will ONLY fetch the child runids associated with 'ensemble_name_1' and 'ensemble_name_2', but will search all components for this.

**IPS Notebook Analysis API Reference**

.. autoclass:: doc.reference.portal_jupyter_api.ips_analysis_api_v1.IPSAnalysisApi
    :members:
    :undoc-members:    
    :noindex:

**JupyterHub Filesystem Notes**

The IPS Portal will always be reading and writing files to a specific directory on a JupyterHub filesystem. From there, the filesystem organization will look somewhat like this:

.. code-block:: bash
    
    .
    ├── username1
    └── username2
        ├── 1   # this is the runid as tracked by the IPS Portal
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
        |   ├── ensembles
        │   │   ├── DriverComponent
        │   │   │   ├── my_first_ensemble.csv
        │   │   │   └── my_second_ensemble.csv
        │   ├── ips_analysis_api_child_runs.txt        
        │   └── ips_analysis_api_data_listing.json
        ├── 2
        │   ├── basic.ipynb
        |   ├── data
        │   │   └── 0.0_state.json
        |   ├── ensembles
        │   ├── ips_analysis_api_child_runs.txt        
        │   └── ips_analysis_api_data_listing.json
        ├── api_v1_notebook.ipynb
        └── api_v1.py

- From base directory, runs are organized into specific usernames.
- From the username directory, the directory tree will continue based on runids as managed by the IPS Portal. Note that files titled `api_v*.py` and `api_v*_notebook.ipynb` will be added to this directory as well. These files may potentially be overwritten by the framework, but should always be done so in a backwards compatible manner.
- From the runid directory, a few additional files will be added:
    - Notebooks generated from your input notebooks. You should not change a notebook's name, but may freely edit its content.
    - IPS analysis files used for the IPS Analysis API to help organize run information (`ips_analysis_api_child_runs.txt`, `ips_analysis_api_data_listing.json`). These files should not be modified.
    - A `data` directory which will contain all data files you added during the run. (Note that the data files are determined on the domain science side, and can be of any content-type, not just JSON.) You should not change the names of these files.
    - An `ensembles` directory which will contain the CSV files summarizing any ensembles this run initiated. Each CSV file is named after the name of the ensemble, and all CSV files are organized into additional directories named after the component which launched them. Do not modify any of these files.
