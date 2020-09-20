#!/usr/bin/env python3

import tempfile
import contextlib
import os
import subprocess
import logging
import argparse
import shutil


def log(level, msg):
    logging.getLogger("llvm-from-source").log(level, msg)


def which(program):
    return os.getenv(program.upper() + "_EXECUTABLE", program)


@contextlib.contextmanager
def cd(newdir):
    prevdir = os.getcwd()
    try:
        yield os.chdir(os.path.expanduser(newdir))
    finally:
        os.chdir(prevdir)


def download_llvm():
    subprocess.run(("git", "clone", "--depth", "1",
                    "https://github.com/llvm/llvm-project.git")).check_returncode()
    return os.path.join(os.getcwd(), "llvm-project")


def build_llvm(source_dir, generator=None, build_dir=None, install_prefix=None):
    @contextlib.contextmanager
    def build_directory():
        tmp_dir = None
        try:
            if not build_dir:
                tmp_dir = tempfile.TemporaryDirectory()
                yield tmp_dir.name
            else:
                yield os.path.expanduser(build_dir)
        finally:
            if tmp_dir:
                shutil.rmtree(tmp_dir.name)

    with build_directory() as build_dir, cd(build_dir):
        cmake_executable = which("cmake")
        cmake_cmd_line = [cmake_executable, "-DCMAKE_BUILD_TYPE=Release", "-DLLVM_TARGETS_TO_BUILD=X86",
                          "-DLLVM_ENABLE_PROJECTS='clang,libcxx,libcxxabi,libunwind,lldb,compiler-rt,lld,polly'"]
        if generator:
            cmake_cmd_line += ["-G", generator]

        if install_prefix:
            cmake_cmd_line.append(f"-DCMAKE_INSTALL_PREFIX={install_prefix}")

        cmake_cmd_line.append(os.path.join(source_dir, "llvm"))

        log(logging.INFO, " ".join(cmake_cmd_line))
        cmake = subprocess.run(cmake_cmd_line)
        if cmake.returncode != 0:
            log(logging.ERROR, cmake.stderr)
            cmake.check_returncode()

        build_cmd_line = (cmake_executable, "--build", ".")
        log(logging.INFO, " ".join(build_cmd_line))
        build = subprocess.run(build_cmd_line)
        if build.returncode != 0:
            log(logging.ERROR, build.stderr)
            build.check_returncode()

        install = subprocess.run(
            (cmake_executable, "--build", ".", "--target", "install"))
        if install.returncode != 0:
            log(logging.ERROR, install.stderr)
            install.check_returncode()


def create_arg_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", dest="sources",
                        help="path to source if it's already available in system")
    parser.add_argument("--generator", dest="generator",
                        help="CMake generator to use")
    parser.add_argument("--build-dir", dest="build_dir",
                        help="directory to keep build files")
    parser.add_argument("--prefix", dest="prefix", help="install prefix")
    return parser


if __name__ == "__main__":
    args = create_arg_parser().parse_args()
    with tempfile.TemporaryDirectory() as wd, cd(wd):
        log(logging.INFO, f"Use {wd} as temporary directory")
        build_llvm(
            os.path.expanduser(args.sources) if args.sources else download_llvm(), args.generator, args.build_dir)
