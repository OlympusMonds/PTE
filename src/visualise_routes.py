"""
Mostly for debugging for now, this script uses matplotlib to plot origins,
destinations, and their links. Eventually it will plot the ratio of driving
vs. transit for various times. It is also a prototype for the website that
will no double come later.
"""

import sys
import pony.orm as pny
from database import Origin, Destination
from database import init

import matplotlib.pyplot as plt
import matplotlib.colors as colors
import matplotlib.cm as cmx


def vis():
    jet = cm = plt.get_cmap('jet')
    cNorm  = colors.Normalize(vmin=0, vmax=1)
    scalarMap = cmx.ScalarMappable(norm=cNorm, cmap=jet)

    with pny.db_session:
        origins = pny.select(o for o in Origin)[:]

        for o in origins:
            lat, lon = o.location.split(",")
            plt.scatter(lon, lat, c="black", s=100)

            for d in o.destinations:
                dlat, dlon = d.location.split(",")


                count = 0
                driving_dur = 0
                transit_dur = 0
                for t in d.trips:
                    if t.mode == "driving":
                        driving_dur = t.duration
                    else:
                        transit_dur += t.duration
                        count += 1

                transit_dur /= count

                print driving_dur, transit_dur, driving_dur/transit_dur
                colorVal = scalarMap.to_rgba(1 - (driving_dur/transit_dur))

                plt.scatter(dlon, dlat, edgecolors="none", s=200, c=colorVal)

            plt.show()


if __name__ == "__main__":
    init()
    sys.exit(vis())