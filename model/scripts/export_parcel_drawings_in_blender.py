"""Export nominal model sections from a clean saved parcel for PNG drafting."""

import math

import bpy
from mathutils import Matrix, Vector
from project_paths import BLEND, DESIGN, DRAWING_GEOMETRY, load_engine_modules

mesh_descriptors, persistence, render_inventory, transforms = load_engine_modules(
    "mesh_descriptors", "persistence", "render_inventory", "transforms"
)


def xy(point):
    """Undo the parcel placement so both floors share house-local drawing axes."""
    local = world_to_local @ point
    return [local.x, local.y]


def section(obj, height):
    # Base meshes preserve nominal wall sizes; decorative bevels are not drafting edges.
    vertices = [obj.matrix_world @ v.co for v in obj.data.vertices]
    points = []
    for edge in obj.data.edges:
        a, b = [vertices[i] for i in edge.vertices]
        if (a.z < height < b.z) or (b.z < height < a.z):
            points.append(xy(a.lerp(b, (height - a.z) / (b.z - a.z))))
    return points


def footprint(obj):
    return [xy(obj.matrix_world @ v.co) for v in obj.data.vertices]


def add_room_part(rooms, room_id, polygons):
    room = rooms.setdefault(room_id, {"id": room_id, "polygons": [], "area_m2": 0.0})
    room["polygons"].extend(polygons)
    room["area_m2"] += sum(
        abs(
            sum(
                point[0] * following[1] - following[0] * point[1]
                for point, following in zip(ring, ring[1:] + ring[:1], strict=True)
            )
        )
        / 2
        for ring in polygons
    )


def finalize_rooms(rooms, expected_ids, level):
    """Return the measured rooms in the design's order; every expected room must be present."""
    actual_ids, expected = set(rooms), set(expected_ids)
    assert actual_ids == expected, (
        f"{level} drawing rooms mismatch: "
        f"missing={sorted(expected - actual_ids)}, "
        f"unexpected={sorted(actual_ids - expected)}"
    )
    return [rooms[room_id] for room_id in expected_ids]


def north_local(design):
    """House-local unit vector of grid north, or None when the parcel records no bearing.

    ``grid_north_deg`` turns world +Y clockwise toward +X; the design transform's rotation
    maps that world direction into the house-local drawing axes.
    """
    angle = design["parcel"].get("grid_north_deg")
    if angle is None:
        return None
    world = (math.sin(math.radians(angle)), math.cos(math.radians(angle)), 0.0)
    local = world_to_local.to_3x3() @ Vector(world)
    length = math.hypot(local.x, local.y)
    return [local.x / length, local.y / length]


bpy.context.view_layer.update()
style = persistence.read_json(DESIGN / "style.json")
scene = bpy.data.scenes[render_inventory.default_view(style)["scene"]]
design = persistence.read_json(DESIGN / "house.json")
world_to_local = Matrix(design["transform"]).inverted()
result = {
    "exported_at": persistence.utc_now(),
    "blend": str(BLEND),
    # The runner's preflight hashed the clean saved blend this export reads.
    "blend_sha256": globals()["BLENDER_TASK_CONTEXT"]["blend_sha256"],
    "exporter_sha256": persistence.sha256_file(__file__),
    "section_height_m": 1.60,
    "basis": "World-transformed base meshes; nominal wall sections without decorative bevels. Door arcs use modeled hinges and leaf angles. Explicit sliding openings export their active panel and travel direction; other glazing access mechanisms are not inferred. Frame columns share the section cut; each level's beams export their plan footprint.",
    "floors": {},
}
result["project_name"] = design["name"]
result["north_local"] = north_local(design)
openings = {item["id"]: item for item in design["openings"]}
walls = {item["id"]: item for item in design["walls"]}
rooms_by_id = {room["id"]: room for room in design["rooms"]}
# Both drawings show each staircase, dashed above the cut on the level it rises from.
stair_levels = {
    mesh_descriptors.level_collection(stair["from_level_id"], "Stair"): stair["from_level_id"]
    for stair in design["stairs"]
}
axes = [
    {key: item[key] for key in ("id", "label", "direction", "position")}
    for item in design.get("structure", [])
    if item["kind"] == "axis"
]
for storey in design["levels"]:
    level, elevation = storey["id"], storey["elevation_m"]
    expected_room_ids = [room["id"] for room in design["rooms"] if room["level_id"] == level]
    room_parts = {}
    cut = elevation + result["section_height_m"]
    data = {
        "elevation_m": elevation,
        "walls": [],
        "glazing": [],
        "frames": [],
        "doors": [],
        "sliding_doors": [],
        "stairs": [],
        "rooms": [],
        "openings": [],
        "columns": [],
        "beams": [],
        "axes": axes,
        "voids": [v for v in design.get("voids", []) if v["level_id"] == level],
        # The travel arrow reads up from a level a stair rises from, down elsewhere.
        "stair_up": level in stair_levels.values(),
    }
    # Joinery marks and schedules use the maintained opening records placed on their walls.
    for opening in design["openings"]:
        wall = walls[opening["wall_id"]]
        if wall["level_id"] != level or opening["kind"] == "open":
            continue
        span = [
            transforms.wall_point(wall, opening["offset"]),
            transforms.wall_point(wall, opening["offset"] + opening["width"]),
        ]
        data["openings"].append(
            {
                "id": opening["id"],
                "kind": opening["kind"],
                "width_m": opening["width"],
                "height_m": round(opening["head"] - opening["sill"], 3),
                "sill_m": opening["sill"],
                "operation": opening.get("operation"),
                "door_style": opening.get("door_style"),
                "panels": opening.get("panel_count"),
                "blind": bool(opening.get("blind")),
                "exterior": wall["role"] == "exterior",
                "wall_thickness_m": wall["thickness"],
                "span": span,
            }
        )
    for obj in scene.objects:
        if obj.type != "MESH":
            continue
        collections = {c.name for c in obj.users_collection}
        if collections & {level + " | Walls low", level + " | Walls high"}:
            points = section(obj, cut)
            if points:
                wall = walls[obj["Component ID"]]
                data["walls"].append(
                    {
                        "name": obj.name,
                        "points": points,
                        "role": wall["role"],
                        "thickness_m": wall["thickness"],
                    }
                )
        # Frame columns are cut like walls; beams of the slab above the level draw in projection.
        if level + " | Frame" in collections:
            member = {
                "id": obj["Component ID"],
                "mark": obj["Structure mark"],
                "level": obj["Floor level"],
                "section": obj["Structure section"],
            }
            if obj["Component kind"] == "column":
                points = section(obj, cut)
                if points:
                    data["columns"].append({**member, "points": points})
            elif obj["Component kind"] == "beam":
                data["beams"].append(
                    {**member, "placement": obj["Structure placement"], "points": footprint(obj)}
                )
        child = str(obj.get("Procedural child ID", "")).rsplit("/", 1)[-1]
        if level + " | Openings" in collections:
            points = section(obj, cut)
            if child.startswith("pane") and points:
                pane = {"name": obj.name, "points": points}
                if obj.get("Opening operation") == "sliding":
                    pane.update(
                        {
                            "opening_id": obj["Opening ID"],
                            "operation": "sliding",
                            "panel_index": obj["Sliding panel index"],
                            "leaf_role": obj["Sliding leaf role"],
                            "slide_direction": obj["Slide direction"],
                        }
                    )
                    if obj["Sliding leaf role"] == "active":
                        opening = openings[obj["Opening ID"]]
                        wall = walls[opening["wall_id"]]
                        _, unit, _ = transforms.wall_frame(wall)
                        span_start = transforms.wall_point(wall, opening["offset"])
                        span_end = transforms.wall_point(wall, opening["offset"] + opening["width"])
                        sense = -1 if opening["slide_direction"] == "toward-start" else 1
                        data["sliding_doors"].append(
                            {
                                "id": opening["id"],
                                "active_panel": obj["Sliding panel index"],
                                "slide_direction": opening["slide_direction"],
                                "opening_span": [span_start, span_end],
                                "travel_vector": [sense * value for value in unit],
                                "active_leaf_points": points,
                            }
                        )
                data["glazing"].append(pane)
            elif child.startswith(("jamb-", "mullion-")) and points:
                data["frames"].append({"name": obj.name, "points": points})
            elif child == "door-leaf" and points and obj.get("Door operation") == "sliding-pocket":
                opening = openings[obj["Opening ID"]]
                wall = walls[opening["wall_id"]]
                _, unit, _ = transforms.wall_frame(wall)
                sense = -1 if opening["slide_direction"] == "toward-start" else 1
                data["sliding_doors"].append(
                    {
                        "id": opening["id"],
                        "slide_direction": opening["slide_direction"],
                        "opening_span": [
                            transforms.wall_point(wall, opening["offset"]),
                            transforms.wall_point(wall, opening["offset"] + opening["width"]),
                        ],
                        "travel_vector": [sense * value for value in unit],
                        "active_leaf_points": points,
                    }
                )
            elif child == "door-leaf" and points:
                wall = walls[openings[obj["Opening ID"]]["wall_id"]]
                closed = math.atan2(
                    wall["end"][1] - wall["start"][1], wall["end"][0] - wall["start"][0]
                )
                swing = math.radians(obj["Swing degrees"])
                # An end hinge closes back along the wall and mirrors the swing sign.
                if obj.get("Door hinge") == "end":
                    closed, swing = closed + math.pi, -swing
                angle = closed + swing
                direction = (math.cos(angle), math.sin(angle))
                projected = [(sum(p[i] * direction[i] for i in (0, 1)), p) for p in points]
                lo, hi = min(v for v, _ in projected), max(v for v, _ in projected)
                ends = []
                for value in (lo, hi):
                    side = [p for v, p in projected if abs(v - value) < 1e-5]
                    ends.append([sum(p[i] for p in side) / len(side) for i in (0, 1)])
                data["doors"].append(
                    {
                        "name": obj.name,
                        "opening_id": obj["Opening ID"],
                        "points": points,
                        "hinge": ends[0],
                        "end": ends[1],
                        "closed_angle": closed,
                    }
                )
        if obj.get("Floor level") == level and obj.get("Room ID"):
            polygons = [
                [xy(obj.matrix_world @ obj.data.vertices[index].co) for index in face.vertices]
                for face in obj.data.polygons
                if face.normal.z > 0.5
            ]
            add_room_part(room_parts, obj["Room ID"], polygons)
        stair_level = next(
            (stair_levels[name] for name in collections if name in stair_levels), None
        )
        if stair_level and (
            child.startswith(("flight-1-riser-", "flight-2-riser-")) or child == "landing"
        ):
            top = max((obj.matrix_world @ v.co).z for v in obj.data.vertices)
            data["stairs"].append(
                {
                    "name": obj.name,
                    "part": child,
                    "points": footprint(obj),
                    "overhead": level == stair_level and top > cut,
                }
            )
    data["rooms"] = finalize_rooms(room_parts, expected_room_ids, level)
    for room in data["rooms"]:
        source = rooms_by_id[room["id"]]
        room["label"] = source.get("short_name", source["name"])
        room["anchor"] = source["anchor"]
    assert data["walls"] and data["glazing"] and data["doors"]
    result["floors"][level] = data
persistence.atomic_write_json(DRAWING_GEOMETRY, result)
print("DRAWING GEOMETRY EXPORTED", str(DRAWING_GEOMETRY))
