# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import os
import subprocess


def which(program, search_path=None):
    def is_exe(fpath):
        return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

    fpath, fname = os.path.split(program)
    if fpath:
        if is_exe(program):
            return program
    else:
        if not search_path:
            search_path = os.environ["PATH"].split(os.pathsep)
        for path in search_path:
            exe_file = os.path.join(path, program)
            if is_exe(exe_file):
                return exe_file

    return None


def popen_checkcall(args, data_in=None):
    """
    Adapted from Py3 subprocess.checkcall().
    subprocess.run() where are thou? :( Py >=3.5 only)
    """
    try:
        if data_in is None:
            proc = subprocess.Popen(args)
        else:
            proc = subprocess.Popen(args, stdin=subprocess.PIPE)
            proc.communicate(input=data_in)
        returncode = proc.wait()
    except Exception as exc:
        proc.kill()
        proc.wait()
        raise

    if returncode:
        raise CalledProcessError(returncode, args)

    return 0


class CalledProcessError(Exception):

    def __init__(self, returncode, args):
        self.returncode = returncode
        self.cmd = args
        super(CalledProcessError, self).__init__()
