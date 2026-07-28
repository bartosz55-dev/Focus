import unittest
import sys
import os
import platform
import subprocess
from pathlib import Path

class TestBackendSeparationAndCleanImports(unittest.TestCase):
    """
    TDD Test Suite for verifying clean architectural separation between
    backend engine, Qt GUI, and legacy Tkinter GUI.
    Ensures zero Tkinter/CustomTkinter imports in Qt processes to prevent Cocoa crashes on macOS.
    """

    def test_backend_module_has_no_tkinter_imports(self):
        """Verify that importing scenepack_generator_backend does not load tkinter or customtkinter into sys.modules."""
        cmd = [
            sys.executable, "-c",
            "import scenepack_generator_backend, sys; "
            "assert 'tkinter' not in sys.modules, 'tkinter was accidentally imported!'; "
            "assert 'customtkinter' not in sys.modules, 'customtkinter was accidentally imported!'"
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"Backend import check failed: {res.stderr or res.stdout}")

    def test_qt_workers_have_no_tkinter_imports(self):
        """Verify that importing scenepack_generator_workers_qt does not load tkinter or customtkinter."""
        cmd = [
            sys.executable, "-c",
            "import scenepack_generator_workers_qt, sys; "
            "assert 'tkinter' not in sys.modules, 'tkinter loaded by workers!'; "
            "assert 'customtkinter' not in sys.modules, 'customtkinter loaded by workers!'"
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"Workers import check failed: {res.stderr or res.stdout}")

    def test_qt_gui_has_no_tkinter_imports(self):
        """Verify that importing scenepack_generator_gui_qt does not load tkinter or customtkinter."""
        cmd = [
            sys.executable, "-c",
            "import scenepack_generator_gui_qt, sys; "
            "assert 'tkinter' not in sys.modules, 'tkinter loaded by Qt GUI!'; "
            "assert 'customtkinter' not in sys.modules, 'customtkinter loaded by Qt GUI!'"
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"Qt GUI import check failed: {res.stderr or res.stdout}")

    def test_app_version_is_incremented(self):
        """Verify APP_VERSION in backend is incremented to v1.0.8."""
        import scenepack_generator_backend as backend
        self.assertEqual(backend.APP_VERSION, "v1.0.8")

    def test_platform_manager_flags(self):
        """Verify PlatformManager isolates Windows creationflags from macOS/POSIX."""
        import scenepack_generator_backend as backend
        pm = backend.PlatformManager
        flags = pm.get_creation_flags()
        if platform.system() == "Windows":
            expected = getattr(subprocess, "CREATE_NO_WINDOW", 0)
            self.assertEqual(flags, expected)
            self.assertEqual(pm.get_exe_suffix(), ".exe")
            self.assertTrue(pm.is_windows())
            self.assertFalse(pm.is_macos())
        elif platform.system() == "Darwin":
            self.assertEqual(flags, 0)
            self.assertEqual(pm.get_exe_suffix(), "")
            self.assertFalse(pm.is_windows())
            self.assertTrue(pm.is_macos())
        else:
            self.assertEqual(flags, 0)
            self.assertEqual(pm.get_exe_suffix(), "")

    def test_reexport_in_legacy_modules(self):
        """Verify legacy modules re-export from backend seamlessly."""
        import scenepack_generator as cli_mod
        import scenepack_generator_gui as tk_mod
        import scenepack_generator_backend as backend
        
        self.assertIs(cli_mod.ScenePackGenerator, backend.ScenePackGenerator)
        self.assertIs(tk_mod.ScenePackGenerator, backend.ScenePackGenerator)
        self.assertIs(tk_mod.TRANSLATIONS, backend.TRANSLATIONS)
        self.assertIs(tk_mod.get_translation, backend.get_translation)

if __name__ == "__main__":
    unittest.main()
