import geojson
import numpy as np
import pony.orm as pny
from flask import Flask
from flask.ext.cache import Cache
from flask_restful import Resource, Api

from public_transport_analyser.database.database import Origin, init
from public_transport_analyser.visualiser.utils import get_voronoi_map

pta = Flask(__name__)
cache = Cache(pta, config={'CACHE_TYPE': 'simple'})
api = Api(pta)


@pta.route("/")
def index():
    return pta.send_static_file("origins.html")


class FetchAllOrigins(Resource):
    @cache.cached(timeout=5)
    def get(self):
        lonlats = []

        with pny.db_session:
            origins = pny.select(o for o in Origin)[:]

            for o in origins:
                lat, lon = map(float, o.location.split(","))
                lonlats.append((lon, lat, len(o.destinations)))

        features = []
        for lon, lat, num_dest in lonlats:
            properties = {"num_dest": num_dest,
                          "isOrigin": True,
                          "location": ",".join(map(str, (lat,lon)))}  # ""{}".format(origin),}
            features.append(geojson.Feature(geometry=geojson.Point((lon, lat)), properties=properties))

        fc = geojson.FeatureCollection(features)
        return fc


class FetchOrigin(Resource):
    def get(self, origin):
        destinations = []
        time = 6

        with pny.db_session:
            if Origin.exists(location=origin):
                o = Origin.get(location=origin)
            else:
                raise ValueError("No such origin.")

            num_dest = len(o.destinations)
            for d in o.destinations:
                dlat, dlon = map(float, d.location.split(","))

                driving = -1
                transit = -1
                for t in d.trips:
                    if t.mode == "driving":
                        driving = t.duration
                    elif t.time == time:
                        transit = t.duration

                ratio = 1.0
                if driving > 0 and transit > 0:
                    ratio = float(driving) / float(transit)

                destinations.append((dlon, dlat, len(d.trips), ratio))

        # Build GeoJSON features
        # Plot the origin point
        features = []
        opoint = tuple(reversed(list(map(float, origin.split(",")))))  # TODO fix this
        properties = {"isOrigin": True,
                      "num_dest": num_dest,
                      "location": opoint,
                      }
        features.append(geojson.Feature(geometry=geojson.Point(opoint), properties=properties))

        # Plot the destination points
        for details in destinations:
            dlon, dlat, num_trips, _ = details
            properties = {"trips": num_trips,
                          "isDestination": True,
                          "location": (dlon, dlat)}
            features.append(geojson.Feature(geometry=geojson.Point((dlon, dlat)), properties=properties))

        # Plot the destination map
        regions, vertices = get_voronoi_map(destinations)

        for i, region in enumerate(regions):
            properties = {"color": "blue",
                          "strokeWeight": "1",
                          "isOrigin": False,
                          "isPolygon": True,
                          "ratio": destinations[i][3]}
            points = [(lon, lat) for lon, lat in vertices[region]]
            points.append(points[0])  # close off the polygon

            features.append(geojson.Feature(geometry=geojson.Polygon([points]),
                                            properties=properties, ))

        fc = geojson.FeatureCollection(features)

        return fc


class FetchTrips(Resource):
    def get(self, origin, destination):

        jsonorigin = list(map(float, origin.split(",")))
        jsondest = list(map(float, destination.split(",")))
        print(jsonorigin, jsondest)
        with pny.db_session:
            if Origin.exists(location=origin):
                o = Origin.get(location=origin)
            else:
                raise ValueError("No such origin.")

            dest = None
            for d in o.destinations:
                if d.location == destination:
                    dest = d
                    break
            else:
                raise ValueError("No such destination.")

            trips = dest.trips

            features = []
            for t in trips:
                properties = {"mode": t.mode}  # ""{}".format(origin),}
                features.append(geojson.Feature(geometry=geojson.LineString([jsonorigin, jsondest]), properties=properties))

        fc = geojson.FeatureCollection(features)

        return fc


api.add_resource(FetchAllOrigins, '/api/origins')
api.add_resource(FetchOrigin, '/api/origin/<string:origin>')
api.add_resource(FetchTrips, '/api/trip/<string:origin>/<string:destination>')


if __name__ == "__main__":
    init()
    pta.debug = True
    pta.run()
