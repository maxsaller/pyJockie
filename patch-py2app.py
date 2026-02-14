"""Patch py2app zlib bug for uv-managed Python.

uv-managed Python statically links zlib, so zlib has no __file__.
py2app tries to copy zlib.__file__ and crashes with AttributeError.
This script patches the offending line to check hasattr first.
"""
import pathlib
import py2app.build_app

path = pathlib.Path(py2app.build_app.__file__)
source = path.read_text()

# Match the full unpatched block (import + blank line + copy) to avoid
# substring matches on already-patched files.
old = (
    "            import zlib\n"
    "\n"
    "            self.copy_file(zlib.__file__, os.path.dirname(arcdir))"
)
new = (
    "            import zlib\n"
    "\n"
    '            if hasattr(zlib, "__file__") and zlib.__file__:\n'
    "                self.copy_file(zlib.__file__, os.path.dirname(arcdir))"
)

if old in source:
    path.write_text(source.replace(old, new))
    print("  Patched py2app zlib bug")
else:
    print("  py2app zlib patch already applied")
