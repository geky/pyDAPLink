"""
 mbed CMSIS-DAP debugger
 Copyright (c) 2006-2013 ARM Limited

 Licensed under the Apache License, Version 2.0 (the "License");
 you may not use this file except in compliance with the License.
 You may obtain a copy of the License at

     http://www.apache.org/licenses/LICENSE-2.0

 Unless required by applicable law or agreed to in writing, software
 distributed under the License is distributed on an "AS IS" BASIS,
 WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 See the License for the specific language governing permissions and
 limitations under the License.
"""

import subprocess
from subprocess import Popen
import os


# Creating and disowning processes
def popen_and_detach(args):
    os_flags = {}

    # Disowning processes in linux/mac
    if hasattr(os, 'setsid'):
        os_flags['preexec_fn'] = os.setsid

    # Disowning processes in windows
    if hasattr(subprocess, 'STARTUPINFO'):
        # Detach the process
        os_flags['creationflags'] = subprocess.CREATE_NEW_CONSOLE

        # Hide the process console
        startupinfo = subprocess.STARTUPINFO()
	startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        os_flags['startupinfo'] = startupinfo

    # Redirect child's io
    with open(os.devnull, 'w+') as null:
        return Popen(args, stdin=null, stdout=null, stderr=null, **os_flags)
