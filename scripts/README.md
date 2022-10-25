# BinaryRTS Scripts

This collection of scripts is meant to facilitate setting up BinaryRTS for a new project. Currently, the following
scripts are included:

- `patch_msvc_props.py`: Utility to patch MSVC project properties files for including the BinaryRTS test listener static
  library (see [`BinaryRTS listener`](../binaryrts/listener))
- `patch_google_test.py`: Utility to patch GoogleTest C++ projects by globbing all `main.cxx` files.
- `collect_image_files.py`: Utility to recursively collect all image files (e.g., `.dll`, `.exe`) from a directory;
  useful if instrumenting only certain modules.
- `collect_functions_from_binaries.py`: Utility to collect functions from Microsoft binaries (EXE, DLL) for experimental Frida agent
