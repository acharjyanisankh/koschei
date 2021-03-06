# Copyright (C) 2017 Red Hat, Inc.
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
# Author: Mikolaj Izdebski <mizdebsk@redhat.com>

"""
Basic experimental REST API to get the list of packages with their current states.
"""

from flask import request, Response
from sqlalchemy.sql import literal_column, case

from koschei.frontend.base import db, app
from koschei.models import Package, Collection, Build


def sql_if(cond, then, else_=None):
    return case([(cond, then)], else_=else_)


@app.route('/api/v1/packages')
def list_packages():
    """
    Return a list of all packages as JSON. Uses Postgres to generate all the JSON in a
    single query.

    Optional query parameters:
    collection: filter by collection name (list, literal match)
    name: filter by package name (list, literal match)

    Response format:
    [
        {
            "name": "foo",
            "collection": "f29",
            "state": "unresolved",
            "last_complete_build": {
                "task_id": 123
            }
        },
        ...
    ]
    """
    query = (
        db.query(
            Package.name.label('name'),
            Collection.name.label('collection'),
            # pylint:disable=no-member
            Package.state_string.label('state'),
            sql_if(
                Build.id != None,
                db.query(Build.task_id.label('task_id'))
                .correlate(Build)
                .as_record()
            ).label('last_complete_build')
        )
        .join(Collection)
        .outerjoin(
            Build,
            (Package.last_complete_build_id == Build.id) & Build.last_complete
        )
        .order_by(Package.name)
    )
    if 'name' in request.args:
        query = query.filter(Package.name.in_(request.args.getlist('name')))
    if 'collection' in request.args:
        query = query.filter(Collection.name.in_(request.args.getlist('collection')))

    result = (
        db.query(literal_column(
            "coalesce(array_to_json(array_agg(row_to_json(pkg_query)))::text, '[]')"
        ).label('q'))
        .select_from(query.subquery('pkg_query'))
        .scalar()
    )

    return Response(result, mimetype='application/json')
