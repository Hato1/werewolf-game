"""Geometry helpers for polygon-based room objects."""

Point = tuple[float, float]
Polygon = tuple[Point, ...]


def point_in_polygon(point: Point, polygon: Polygon) -> bool:
    """Return whether ``point`` lies inside ``polygon`` using an even-odd ray cast.

    Points on the polygon boundary are not guaranteed to be included; room
    polygons are authored with enough margin that this is not significant.
    """
    x, y = point
    inside = False
    vertex_count = len(polygon)
    for index in range(vertex_count):
        x1, y1 = polygon[index]
        x2, y2 = polygon[(index + 1) % vertex_count]
        if (y1 > y) != (y2 > y):
            crossing_x = x1 + (y - y1) * (x2 - x1) / (y2 - y1)
            if x < crossing_x:
                inside = not inside
    return inside
