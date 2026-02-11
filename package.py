# -*- coding: utf-8 -*-
name = "openvdb"
version = "13.0.0"
authors = ["DreamWorks Animation"]
description = "OpenVDB: Sparse volume data structure and tools."

variants = [
    ["python-3.11", "imath-3.1.9"],
    ["python-3.11", "imath-3.2.0"],
    ["python-3.12", "imath-3.1.9"],
    ["python-3.12", "imath-3.2.0"],
    ["python-3.13", "imath-3.2.0"],
]

requires = [
    "boost-1.85.0",
    "tbb-2022.2.0",
    "zlib-1.2.13",
    "openexr-3.3.3",
    "blosc-1.21.5",
]

build_requires = [
    "cmake-3.26.5",
    "gcc-11.5.0",
    "nanobind-2.5.0",
    "tsl_robin_map-1.3.0",
]

build_command = "python {root}/rezbuild.py {install}"

def commands():
    env.OPENVDB_ROOT = "{root}"
    env.OpenVDB_ROOT = "{root}"
    env.CMAKE_PREFIX_PATH.append("{root}")
    env.PATH.append("{root}/bin")
    env.LD_LIBRARY_PATH.prepend("{root}/lib64")
    env.LIBRARY_PATH.prepend("{root}/lib64")
    env.PKG_CONFIG_PATH.prepend("{root}/lib/pkgconfig")
    env.CPATH.prepend("{root}/include")
    py_pkg = resolve["python"]
    py_ver = f"{py_pkg.version.major}.{py_pkg.version.minor}"
    env.PYTHONPATH.prepend(f"{{root}}/lib64/python{py_ver}/site-packages")
