import importlib
from pathlib import Path
import pkgutil
import unittest


def load_tests(
    loader: unittest.TestLoader,
    discovered_tests: unittest.TestSuite,
    pattern: str | None,
) -> unittest.TestSuite:
    suite = unittest.TestSuite()

    for module_info in pkgutil.iter_modules([str(Path(__file__).parent)]):
        if not module_info.name.endswith("_test"):
            continue

        module = importlib.import_module(f"{__name__}.{module_info.name}")
        suite.addTests(loader.loadTestsFromModule(module))

    return suite
