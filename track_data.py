class TrackPoint:
    def __init__(self, x, y, z, station_name=None, switch_name=None, track_name=None):
        self.x = x
        self.y = y
        self.z = z
        self.station_name = station_name
        self.switch_name = switch_name
        self.track_name = track_name


class CurveSegment:
    def __init__(self, p1, p2, p3, station_name=None, switch_name=None):
        self.p1 = p1
        self.p2 = p2
        self.p3 = p3
        self.station_name = station_name
        self.switch_name = switch_name

    def get_points(self):
        return [self.p1, self.p2, self.p3]

    def update_station_switch(self):
        pts = self.get_points()
        stations = {p.station_name for p in pts if p.station_name}
        switches = {p.switch_name for p in pts if p.switch_name}
        if len(stations) == 1:
            self.station_name = stations.pop()
        else:
            self.station_name = None
        if len(switches) == 1:
            self.switch_name = switches.pop()
        else:
            self.switch_name = None

    def remove_point(self, p):
        pts = self.get_points()
        if p not in pts:
            return [self]
        idx = pts.index(p)
        # Jednoduchá logika mazání bodu, viz předchozí příklady
        if idx == 1:
            p1 = pts[0]
            p3 = pts[2]
            m = TrackPoint((p1.x+p3.x)/2, (p1.y+p3.y)/2, (p1.z+p3.z)/2, station_name=self.station_name, switch_name=self.switch_name)
            seg = CurveSegment(p1, m, p3, station_name=self.station_name, switch_name=self.switch_name)
            return [seg]
        else:
            p1, p2, p3 = pts
            if idx == 0:
                seg = CurveSegment(p2, TrackPoint((p2.x+p3.x)/2,(p2.y+p3.y)/2,(p2.z+p3.z)/2, station_name=self.station_name, switch_name=self.switch_name), p3,
                                   station_name=self.station_name, switch_name=self.switch_name)
                return [seg]
            elif idx == 2:
                seg = CurveSegment(p1, TrackPoint((p1.x+p2.x)/2,(p1.y+p2.y)/2,(p1.z+p2.z)/2, station_name=self.station_name, switch_name=self.switch_name), p2,
                                   station_name=self.station_name, switch_name=self.switch_name)
                return [seg]
