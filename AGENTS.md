# AGENTS.md

## High Level Overview

The IPS framework is a framework where users create components (as defined in the simulation config file) which are intended to execute in parallel. Users are generally expected to execute `ips.py` directly, and place all domain-specific logic within components.

## Specific Rules

* add type hints to function definitions wherever possible,
  if you get a circular import error then just make note of it
* always run the Ruff formatter
* make sure that existing Ruff lints as defined by the `pyproject.toml`
  specification pass, and try to enforce additional Ruff rules through
  `pyproject.toml` when possible.
  * We humans can manually add the rules we don't like to the extend-ignore
    list. Do NOT ignore a rule on your own, explicitly ask the human if you REALLY think the rule should be ignored.
* When adding a new module, if nothing in the module is intended to be imported directly by framework users, place the module somewhere under the `ipsframework/_internal` directory. These are considered private modules.
  * Note that several modules SHOULD be added to this `_internal` private module directory, but currently aren't. As a general rule, anything not in `component.py`, `services.py`, or not explicitly marked in `__init__.py` should probably be considered private.
  * If a module has ANYTHING re-exported in the root `__init__.py`, it should not be in a private module.
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
  * If the function or class is only used inside the private module it's defined in, prefix it with one underscore.
  * If the function or class is only used inside a given public module and is not intended to be used by application developers, prefix it with one underscore.
* If adding a new variable inside a class, and the variable should not be used outside of the class itself, prefix the variable with one underscore.
