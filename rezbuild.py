# -*- coding: utf-8 -*-
"""
openvdb rezbuild.py - rez variants 기반 빌드
REZ 환경변수로 하드코딩 제거
"""
import os
import sys
import shutil
import subprocess


def run_cmd(cmd, cwd=None):
    """명령 실행"""
    print(f"[RUN] {cmd}  (cwd={cwd})")
    subprocess.run(
        ["bash", "-lc", cmd],
        cwd=cwd,
        check=True,
    )


def clean_build_dir(path):
    """빌드 디렉토리 클린업 (*.rxt, variant.json 보존)"""
    if os.path.isdir(path):
        print(f"Cleaning build directory (preserving .rxt/.json): {path}")
        for item in os.listdir(path):
            if item.endswith(".rxt") or item == "variant.json":
                continue
            full = os.path.join(path, item)
            if os.path.isdir(full):
                shutil.rmtree(full)
            else:
                os.remove(full)


def clean_install_dir(path):
    """설치 디렉토리 제거"""
    if os.path.isdir(path):
        print(f"Removing install directory: {path}")
        shutil.rmtree(path)


def write_pkgconfig(install_root, version):
    """pkg-config 파일 생성"""
    pc_dir = os.path.join(install_root, "lib", "pkgconfig")
    os.makedirs(pc_dir, exist_ok=True)
    pc = f"""\
prefix={install_root}
exec_prefix=${{prefix}}
libdir=${{prefix}}/lib
includedir=${{prefix}}/include

Name: OpenVDB
Description: Sparse volume data storage and IO library
Version: {version}
Requires: Imath
Libs: -L${{libdir}} -lopenvdb
Cflags: -I${{includedir}}
"""
    pc_path = os.path.join(pc_dir, "openvdb.pc")
    with open(pc_path, "w") as f:
        f.write(pc)
    print(f"Generated pkg-config file: {pc_path}")


def build(source_path, build_path, install_path_env, targets):
    version = os.environ.get("REZ_BUILD_PROJECT_VERSION")
    if not version:
        sys.exit("REZ_BUILD_PROJECT_VERSION not set")

    # ── Python 버전 (rez variant가 제공) ──
    py_major = os.environ.get("REZ_PYTHON_MAJOR_VERSION", "3")
    py_minor = os.environ.get("REZ_PYTHON_MINOR_VERSION", "13")
    py_version = f"{py_major}.{py_minor}"
    print(f"Building OpenVDB for Python {py_version}")

    # ── Python executable (REZ_PYTHON_ROOT 활용) ──
    python_root = os.environ.get("REZ_PYTHON_ROOT", "")
    python_exe = os.path.join(python_root, "bin", "python3") if python_root else ""
    if not python_exe or not os.path.exists(python_exe):
        python_exe = shutil.which("python3") or sys.executable
        print(f"Warning: Rez Python not found, using: {python_exe}")
    else:
        print(f"Using Python: {python_exe}")

    # ── variant subpath ──
    variant_subpath = os.environ.get("REZ_BUILD_VARIANT_SUBPATH", "")

    # ── 소스 디렉토리 ──
    src_dir = os.path.join(source_path, f"source/openvdb-{version}")
    if not os.path.isdir(src_dir):
        raise FileNotFoundError(f"Source not found: {src_dir}")

    # ── 빌드/설치 디렉토리 준비 ──
    clean_build_dir(build_path)
    os.makedirs(build_path, exist_ok=True)

    install_root = install_path_env
    if "install" in targets:
        install_root = f"/core/Linux/APPZ/packages/openvdb/{version}/{variant_subpath}"
        clean_install_dir(install_root)
        os.makedirs(install_root, exist_ok=True)

    # ── 의존 패키지 CMAKE_PREFIX_PATH 구성 ──
    dep_env_vars = [
        "REZ_BOOST_ROOT",
        "REZ_TBB_ROOT",
        "REZ_ZLIB_ROOT",
        "REZ_OPENEXR_ROOT",
        "REZ_IMATH_ROOT",
        "REZ_BLOSC_ROOT",
        "REZ_NANOBIND_ROOT",
        "REZ_TSL_ROBIN_MAP_ROOT",
        "REZ_PYTHON_ROOT",
    ]
    prefix_paths = [os.environ.get(v, "") for v in dep_env_vars if os.environ.get(v)]
    cmake_prefix = ";".join(prefix_paths)

    # ── TBB 경로 (oneAPI 구조) ──
    tbb_root = os.environ.get("REZ_TBB_ROOT", "")
    tbb_dir = os.path.join(tbb_root, "lib", "cmake", "tbb") if tbb_root else ""

    # ── Python 라이브러리/헤더 경로 ──
    python_lib = ""
    for libname in (f"libpython{py_version}.so", f"libpython{py_version}m.so"):
        candidate = os.path.join(python_root, "lib", libname)
        if os.path.exists(candidate):
            python_lib = candidate
            break

    python_include = ""
    for incdir in (f"python{py_version}", f"python{py_version}m"):
        candidate = os.path.join(python_root, "include", incdir)
        if os.path.isdir(candidate):
            python_include = candidate
            break

    # ── tsl_robin_map include 경로 ──
    tsl_include = os.environ.get("REZ_TSL_ROBIN_MAP_ROOT", "")
    tsl_include_dir = os.path.join(tsl_include, "include") if tsl_include else ""

    # ── CXX_FLAGS 구성 ──
    cxx_flags_parts = ["-DTBB_SUPPRESS_DEPRECATED_MESSAGES=1"]
    if tbb_root:
        tbb_oneapi_include = os.path.join(tbb_root, "include", "oneapi")
        if os.path.isdir(tbb_oneapi_include):
            cxx_flags_parts.append(f"-I{tbb_oneapi_include}")
    if python_include:
        cxx_flags_parts.append(f"-I{python_include}")
    if tsl_include_dir and os.path.isdir(tsl_include_dir):
        cxx_flags_parts.append(f"-I{tsl_include_dir}")
    cxx_flags = " ".join(cxx_flags_parts)

    # ── CMake 구성 ──
    cmake_args = [
        f"cmake {src_dir}",
        f"-DCMAKE_INSTALL_PREFIX={install_root}",
        "-DCMAKE_BUILD_TYPE=Release",
        "-DOPENVDB_USE_BLOSC=ON",
        "-DOPENVDB_BUILD_BINARIES=ON",
        "-DOPENVDB_BUILD_UNITTESTS=OFF",
        "-DOPENVDB_BUILD_PYTHON_MODULE=ON",
        f"-DPython_EXECUTABLE={python_exe}",
        f'-DCMAKE_PREFIX_PATH="{cmake_prefix}"',
        f"-DCMAKE_CXX_FLAGS='{cxx_flags}'",
        "-G Ninja",
    ]
    if python_lib:
        cmake_args.append(f"-DPython_LIBRARY={python_lib}")
    if python_include:
        cmake_args.append(f"-DPython_INCLUDE_DIR={python_include}")
    if tbb_root:
        cmake_args.append(f"-DTBB_ROOT={tbb_root}")
    if tbb_dir and os.path.isdir(tbb_dir):
        cmake_args.append(f"-DTbb_DIR={tbb_dir}")

    # ── Configure → Build → Install ──
    run_cmd(" ".join(cmake_args), cwd=build_path)
    run_cmd("cmake --build . --parallel", cwd=build_path)

    if "install" in targets:
        run_cmd("cmake --install .", cwd=build_path)
        write_pkgconfig(install_root, version)

        # package.py 복사 (버전 루트에 1개)
        server_base = f"/core/Linux/APPZ/packages/openvdb/{version}"
        os.makedirs(server_base, exist_ok=True)
        dst_pkg = os.path.join(server_base, "package.py")
        print(f"Copying package.py -> {dst_pkg}")
        shutil.copy(os.path.join(source_path, "package.py"), dst_pkg)

        # 빌드 마커
        marker = os.path.join(build_path, "build.rxt")
        print(f"Touching build marker: {marker}")
        open(marker, "a").close()

    print(f"openvdb-{version} (Python {py_version}) build/install complete: {install_root}")


if __name__ == "__main__":
    build(
        source_path      = os.environ["REZ_BUILD_SOURCE_PATH"],
        build_path       = os.environ["REZ_BUILD_PATH"],
        install_path_env = os.environ["REZ_BUILD_INSTALL_PATH"],
        targets          = sys.argv[1:],
    )
