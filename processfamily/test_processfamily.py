__author__ = 'matth'

import unittest
import sys
from processfamily.test import ParentProcess, Config
import os
import subprocess
import requests
import time
import socket
import logging
import glob
from processfamily.processes import process_exists, kill_process
from processfamily import _traceback_str

class TestStartStop(unittest.TestCase):
    def test_start_stop_one(self):
        family = ParentProcess.ProcessFamilyForTests(number_of_child_processes=1)
        family.start()
        family.stop()

    def test_start_stop_three(self):
        family = ParentProcess.ProcessFamilyForTests(number_of_child_processes=3)
        family.start()
        family.stop()

class _BaseProcessFamilyFunkyWebServerTestSuite(unittest.TestCase):

    def setUp(self):
        self.check_server_ports_unbound()

        self.pid_dir = os.path.join(os.path.dirname(__file__), 'test', 'pid')
        if not os.path.exists(self.pid_dir):
            os.makedirs(self.pid_dir)
        for pid_file in self.get_pid_files():
            with open(pid_file, "r") as f:
                pid = f.read().strip()
            if pid and process_exists(int(pid)):
                logging.warning(
                    "Process with pid %s is stilling running. This could be a problem " + \
                    "(but it might be a new process with a recycled pid so I'm not killing it)." % pid )
            os.remove(pid_file)

        self.start_parent_process()

    def tearDown(self):
        self.wait_for_parent_to_stop(5)

        #Now check that no processes are left over:
        processes_left_running = []
        for pid_file in self.get_pid_files():
            with open(pid_file, "r") as f:
                pid = f.read().strip()
            if pid and process_exists(int(pid)):
                processes_left_running.append(int(pid))
            os.remove(pid_file)
        for pid in processes_left_running:
            try:
                kill_process(pid)
            except Exception as e:
                logging.warning("Error killing process with pid %d: %s", pid, _traceback_str())

        self.assertFalse(processes_left_running, msg="There should be no PIDs left running but there are: %s" % (', '.join([str(p) for p in processes_left_running])))

        self.check_server_ports_unbound()

    def get_pid_files(self):
        return glob.glob(os.path.join(self.pid_dir, "*.pid"))

    def test_start_stop1(self):
        time.sleep(5)
        self.send_parent_http_command("stop")

    def test_start_stop2(self):
        time.sleep(5)
        self.send_parent_http_command("stop")

    def check_server_ports_unbound(self):
        for pnumber in range(4):
            port = Config.get_starting_port_nr() + pnumber
            #I just try and bind to the server port and see if I have a problem:
            logging.info("Checking for ability to bind to port %d", port)
            serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                if not sys.platform.startswith('win'):
                    #On linux I need this setting cos we are starting and stopping things
                    #so frequently that they are still in a STOP_WAIT state when I get here
                    serversocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                serversocket.bind(("", port))
            finally:
                serversocket.close()

    def get_path_to_ParentProcessPy(self):
        return os.path.join(os.path.dirname(__file__), 'test', 'ParentProcess.py')

    def send_parent_http_command(self, command):
        return self.send_http_command(Config.get_starting_port_nr(), command)

    def send_http_command(self, port, command):
        r = requests.get('http://localhost:%d/%s' % (port, command))
        return r.json


class NormalSubprocessServiceTests(_BaseProcessFamilyFunkyWebServerTestSuite):

    def start_parent_process(self):
        self.parent_process = subprocess.Popen(
            [sys.executable, self.get_path_to_ParentProcessPy()],
            close_fds=True)

    def wait_for_parent_to_stop(self, timeout):
        start_time = time.time()
        while time.time()-start_time < timeout:
            if self.parent_process.poll() is None:
                time.sleep(0.3)



#Remove the base class from the module dict so it isn't smelled out:
del(_BaseProcessFamilyFunkyWebServerTestSuite)