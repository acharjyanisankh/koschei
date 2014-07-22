# Copyright (C) 2014  Red Hat, Inc.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#
# Author: Michael Simacek <msimacek@redhat.com>

from __future__ import print_function

import logging
import json

from datetime import datetime

from . import util
from .models import Build, Session, Package, DependencyChange

log = logging.getLogger('submitter')

def submit_builds(db_session, koji_session):
    scheduled_builds = db_session.query(Build).filter_by(state=Build.SCHEDULED)
    for build in scheduled_builds:
        package = build.package
        name = package.name
        build.state = Build.RUNNING
        build_opts = None
        if package.build_opts:
            build_opts = json.loads(package.build_opts)
        try:
            build.task_id = util.koji_scratch_build(koji_session, name, build_opts)
        except util.PackageBlocked:
            package.state = Package.RETIRED
            db_session.delete(build)
            db_session.commit()
            continue
        build.started = datetime.now()
        build.package.manual_priority = 0
        DependencyChange.build_submitted(db_session, build)
        db_session.commit()

def update_koji_state(db_session, build, state):
    if state in Build.KOJI_STATE_MAP:
        state = Build.KOJI_STATE_MAP[state]
        if state == Build.CANCELED:
            log.info('Deleting build {0} because it was canceled'\
                     .format(build))
            db_session.delete(build)
        else:
            log.info('Setting build {build} state to {state}'\
                      .format(build=build, state=Build.REV_STATE_MAP[state]))
            build.state = state
        db_session.commit()
        #TODO finish time

def main():
    import time
    db_session = Session()
    koji_session = util.create_koji_session()
    print("submitter started")
    while True:
        submit_builds(db_session, koji_session)
        db_session.expire_all()
        time.sleep(3)

if __name__ == '__main__':
    main()
