"""Explicit habitable double-height exclusions, distinct from circulation stairs."""

from shapely.ops import unary_union

from .geometry import as_polygon, map_plan


def cut_voids(design, polygon, *, level_id=None, slab_id=None):
    cuts = [
        as_polygon(void["polygon"])
        for void in design.get("voids", [])
        if void["level_id"] == level_id or slab_id in void["cut_slab_ids"]
    ]
    return polygon.difference(unary_union(cuts)) if cuts else polygon


def validate_voids(design):
    levels = {level["id"]: level for level in design["levels"]}
    rooms = {room["id"]: room for room in design["rooms"]}
    slabs = {slab["id"]: slab for slab in design["slabs"]}
    for void in design.get("voids", []):
        if void["level_id"] not in levels or void["room_below_id"] not in rooms:
            raise ValueError(f"{void['id']}: unknown level or room below")
        room = rooms[void["room_below_id"]]
        polygon = as_polygon(void["polygon"])
        if levels[room["level_id"]]["elevation_m"] >= levels[void["level_id"]]["elevation_m"]:
            raise ValueError(f"{void['id']}: room must be below the excluded floor")
        if not as_polygon(room["zone"]).covers(polygon):
            raise ValueError(f"{void['id']}: void must remain over its declared room")
        for slab_id in void["cut_slab_ids"]:
            if slab_id not in slabs or not as_polygon(slabs[slab_id]["polygon"]).covers(polygon):
                raise ValueError(f"{void['id']}: cut must be contained in {slab_id}")


def measured_voids(design, objects, footprint):
    """Require independently exported absence of floor/slab, then measure clear volume.

    A semantic exclusion mesh alone never proves a double-height void. Inspect the
    evaluated occupied floor band and the declared slabs/ceiling as well. Boundary
    walls and edge beams may project into the nominated concept outline.
    """
    result = {}
    for void in design.get("voids", []):
        markers = [o for o in objects if o["component_id"] == void["id"]]
        if not markers:
            raise ValueError(f"{void['id']}: missing evaluated exclusion mesh")
        region = unary_union([footprint(o) for o in markers])
        expected = map_plan(void["polygon"], design["transform"])
        if region.symmetric_difference(expected).area > 1e-4:
            raise ValueError(f"{void['id']}: evaluated exclusion differs from the authored void")
        if any(
            o.get("kind") != "void"
            or o.get("properties", {}).get("Floor level") != void["level_id"]
            or o.get("properties", {}).get("Gross area role") != "excluded-void"
            for o in markers
        ):
            raise ValueError(f"{void['id']}: evaluated exclusion has invalid semantics")
        blockers = [
            o
            for o in objects
            if o["component_id"] in void["cut_slab_ids"]
            or (
                o.get("kind") == "room_floor"
                and o.get("properties", {}).get("Floor level") == void["level_id"]
            )
        ]
        obstructed = sum(region.intersection(footprint(o)).area for o in blockers)
        if obstructed > 1e-4:
            raise ValueError(f"{void['id']}: evaluated slab/floor still covers {obstructed:.3f} m²")
        lower = [
            max(v[2] for v in o["vertices_world"])
            for o in objects
            if o.get("kind") == "room_floor"
            and o.get("properties", {}).get("Room ID") == void["room_below_id"]
        ]
        upper = [
            min(v[2] for v in o["vertices_world"])
            for o in objects
            if o.get("kind") == "ceiling"
            and o.get("properties", {}).get("Floor level") == void["level_id"]
            and region.intersection(footprint(o)).area > region.area * 0.9
        ]
        if not lower or not upper:
            raise ValueError(f"{void['id']}: missing measured floor or high ceiling")
        result[void["id"]] = {
            "excluded_floor_m2": round(region.area, 6),
            "finished_clear_height_m": round(min(upper) - max(lower), 6),
            "blocked_slab_floor_m2": round(obstructed, 6),
        }
    return result
