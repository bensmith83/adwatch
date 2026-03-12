"""Plugin modules for adwatch — auto-discovered from this directory."""

import importlib
import pkgutil

# Import every submodule so @register_parser decorators fire automatically.
for _info in pkgutil.iter_modules(__path__):
    importlib.import_module(f"{__name__}.{_info.name}")
