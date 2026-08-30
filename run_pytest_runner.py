import sys
import os
import inspect

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

import tests.test_writing as tw
import tests.test_reading as tr
from _pytest.monkeypatch import MonkeyPatch

def run_all_tests():
    test_functions = []
    
    for mod_name, mod in [("tests/test_writing.py", tw), ("tests/test_reading.py", tr)]:
        for attr_name in sorted(dir(mod)):
            if attr_name.startswith("test_") and callable(getattr(mod, attr_name)):
                test_functions.append((f"{mod_name}::{attr_name}", getattr(mod, attr_name)))

    print("================================= Test Results =================================")
    print()
    
    passed_count = 0
    failed_count = 0
    total = len(test_functions)

    for idx, (full_name, func) in enumerate(test_functions, 1):
        pct = int((idx / total) * 100)
        try:
            sig = inspect.signature(func)
            if "monkeypatch" in sig.parameters:
                mp = MonkeyPatch()
                try:
                    func(monkeypatch=mp)
                finally:
                    mp.undo()
            else:
                func()
            print(f"{full_name:<65} PASSED [{pct:>3}%]")
            passed_count += 1
        except Exception as err:
            print(f"{full_name:<65} FAILED [{pct:>3}%]")
            print(f"  Error: {err}")
            failed_count += 1

    print()
    print(f"========================== {passed_count} passed, {failed_count} failed ==========================")
    return failed_count

if __name__ == "__main__":
    sys.exit(run_all_tests())
