# encoding: utf-8
"""
An object for managing IPython profile directories.

Authors:

* Brian Granger
* Fernando Perez
* Min RK

"""

#-----------------------------------------------------------------------------
#  Copyright (C) 2008-2011  The IPython Development Team
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
#-----------------------------------------------------------------------------

#-----------------------------------------------------------------------------
# Imports
#-----------------------------------------------------------------------------

import os
import shutil
import sys

from IPython.config.configurable import LoggingConfigurable
from IPython.config.loader import Config
from IPython.utils.path import get_ipython_package_dir, expand_path
from IPython.utils.traitlets import List, Unicode, Bool

#-----------------------------------------------------------------------------
# Classes and functions
#-----------------------------------------------------------------------------


#-----------------------------------------------------------------------------
# Module errors
#-----------------------------------------------------------------------------

class ProfileDirError(Exception):
    pass


#-----------------------------------------------------------------------------
# Class for managing profile directories
#-----------------------------------------------------------------------------

class ProfileDir(LoggingConfigurable):
    """An object to manage the profile directory and its resources.

    The profile directory is used by all IPython applications, to manage
    configuration, logging and security.

    This object knows how to find, create and manage these directories. This
    should be used by any code that wants to handle profiles.
    """

    security_dir_name = Unicode('security')
    log_dir_name = Unicode('log')
    startup_dir_name = Unicode('startup')
    pid_dir_name = Unicode('pid')
    security_dir = Unicode(u'')
    log_dir = Unicode(u'')
    startup_dir = Unicode(u'')
    pid_dir = Unicode(u'')

    location = Unicode(u'', config=True,
        help="""Set the profile location directly. This overrides the logic used by the
        `profile` option.""",
        )

    _location_isset = Bool(False) # flag for detecting multiply set location

    def _location_changed(self, name, old, new):
        if self._location_isset:
            raise RuntimeError("Cannot set profile location more than once.")
        self._location_isset = True
        if not os.path.isdir(new):
            os.makedirs(new)
        
        # ensure config files exist:
        self.security_dir = os.path.join(new, self.security_dir_name)
        self.log_dir = os.path.join(new, self.log_dir_name)
        self.startup_dir = os.path.join(new, self.startup_dir_name)
        self.pid_dir = os.path.join(new, self.pid_dir_name)
        self.check_dirs()

    def _log_dir_changed(self, name, old, new):
        self.check_log_dir()

    def check_log_dir(self):
        if not os.path.isdir(self.log_dir):
            os.mkdir(self.log_dir)

    def _startup_dir_changed(self, name, old, new):
        self.check_startup_dir()

    def check_startup_dir(self):
        if not os.path.isdir(self.startup_dir):
            os.mkdir(self.startup_dir)
        readme = os.path.join(self.startup_dir, 'README')
        src = os.path.join(get_ipython_package_dir(), u'config', u'profile', u'README_STARTUP')
        if not os.path.exists(readme):
            shutil.copy(src, readme)

    def _security_dir_changed(self, name, old, new):
        self.check_security_dir()

    def check_security_dir(self):
        if not os.path.isdir(self.security_dir):
            os.mkdir(self.security_dir, 0700)
        else:
            try:
                os.chmod(self.security_dir, 0700)
            except OSError:
                self.log.warn("Could not set security dir permissions to private.")

    def _pid_dir_changed(self, name, old, new):
        self.check_pid_dir()

    def check_pid_dir(self):
        if not os.path.isdir(self.pid_dir):
            os.mkdir(self.pid_dir, 0700)
        else:
            try:
                os.chmod(self.pid_dir, 0700)
            except OSError:
                self.log.warn("Could not set pid dir permissions to private.")

    def check_dirs(self):
        self.check_security_dir()
        self.check_log_dir()
        self.check_pid_dir()
        self.check_startup_dir()

    def copy_config_file(self, config_file, path=None, overwrite=False):
        """Copy a default config file into the active profile directory.

        Default configuration files are kept in :mod:`IPython.config.default`.
        This function moves these from that location to the working profile
        directory.
        """
        dst = os.path.join(self.location, config_file)
        if os.path.isfile(dst) and not overwrite:
            return False
        if path is None:
            path = os.path.join(get_ipython_package_dir(), u'config', u'profile', u'default')
        src = os.path.join(path, config_file)
        shutil.copy(src, dst)
        return True

    @classmethod
    def create_profile_dir(cls, profile_dir, config=None):
        """Create a new profile directory given a full path.

        Parameters
        ----------
        profile_dir : str
            The full path to the profile directory.  If it does exist, it will
            be used.  If not, it will be created.
        """
        return cls(location=profile_dir, config=config)

    @classmethod
    def create_profile_dir_by_name(cls, path, name=u'default', config=None):
        """Create a profile dir by profile name and path.

        Parameters
        ----------
        path : unicode
            The path (directory) to put the profile directory in.
        name : unicode
            The name of the profile.  The name of the profile directory will
            be "profile_<profile>".
        """
        if not os.path.isdir(path):
            raise ProfileDirError('Directory not found: %s' % path)
        profile_dir = os.path.join(path, u'profile_' + name)
        return cls(location=profile_dir, config=config)

    @classmethod
    def find_profile_dir_by_name(cls, ipython_dir, name=u'default', config=None):
        """Find an existing profile dir by profile name, return its ProfileDir.

        This searches through a sequence of paths for a profile dir.  If it
        is not found, a :class:`ProfileDirError` exception will be raised.

        The search path algorithm is:
        1. ``os.getcwdu()``
        2. ``ipython_dir``

        Parameters
        ----------
        ipython_dir : unicode or str
            The IPython directory to use.
        name : unicode or str
            The name of the profile.  The name of the profile directory
            will be "profile_<profile>".
        """
        dirname = u'profile_' + name
        paths = [os.getcwdu(), ipython_dir]
        for p in paths:
            profile_dir = os.path.join(p, dirname)
            if os.path.isdir(profile_dir):
                return cls(location=profile_dir, config=config)
        else:
            raise ProfileDirError('Profile directory not found in paths: %s' % dirname)

    @classmethod
    def find_profile_dir(cls, profile_dir, config=None):
        """Find/create a profile dir and return its ProfileDir.

        This will create the profile directory if it doesn't exist.

        Parameters
        ----------
        profile_dir : unicode or str
            The path of the profile directory.  This is expanded using
            :func:`IPython.utils.genutils.expand_path`.
        """
        profile_dir = expand_path(profile_dir)
        if not os.path.isdir(profile_dir):
            raise ProfileDirError('Profile directory not found: %s' % profile_dir)
        return cls(location=profile_dir, config=config)


