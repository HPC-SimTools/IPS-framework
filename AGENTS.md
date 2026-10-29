* add type hints to function definitions wherever possible, 
  if you get a circular import error then just make note of it
* always run the Ruff formatter
* make sure that existing Ruff lints as defined by the `pyproject.toml` 
  specification pass, and try to enforce additional Ruff rules through 
  `pyproject.toml` when possible. 
  * We humans can manually add the rules we don't like to the extend-ignore 
    list.
* When adding a new function or class, add a docstring to the function 
  or class definition. 
  * The docstring should describe what the function or class does, its 
    parameters, and its return value. 
  * If the function or class is complex, consider adding examples of
    how to use it.  
    * If it makes sense, use doctest-style examples in the docstring, so that 
      they can be run as tests.
  * Please use RestructuredText (reST) format for docstrings, 
    as it is widely used in the Python community and is compatible with many 
    documentation tools, such as Sphinx.
    * Be sure to document all function arguments via `:param:` directives, 
      including their types and any relevant details about their usage.
    * Be sure to document all return values via `:return:` or `:returns:` 
      directives.
  * If the function is a coroutine, include a description of the 
    coroutine's behavior and any relevant details about its execution. 
  * If the function is a generator, include a description of the generator's 
    behavior and any relevant details about its execution. 
  * If the function is a property, include a description of the property's 
    behavior and any relevant details about its execution. 
  * If the function is a static method, include a description of the static 
    method's behavior and any relevant details.