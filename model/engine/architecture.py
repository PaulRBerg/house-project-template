"""Host-side architectural compiler. Shapely never runs inside Blender."""

from __future__ import annotations

import math
from collections import Counter
from itertools import pairwise

from shapely.ops import unary_union

from .compiler import compile_design, frame_member_measures, frame_members, frame_totals
from .double_height import cut_voids
from .geometry import (
    as_polygon,
    extrude_polygon,
    furnishing_footprint,
    oriented_box,
    rectangle_mesh,
    roof_covering_z,
    wall_box,
    wall_footprint,
)
from .mesh_descriptors import ROOF_CAP_SOLAR, level_collection, mesh_descriptor

GENERATOR_VERSION = "architecture-1.0.0"
# Frame meshes sit this far inside their nominal faces so they never z-fight with
# coplanar wall, slab or ceiling faces; properties and quantities stay nominal.
FRAME_FACE_INSET_M = 0.002
# Furnished cutaways hide wall bands above this height unless a wall sets its own.
CUTAWAY_HEIGHT_M = 1.05


def polygon_json(polygon):
    return {
        "outer": [list(p) for p in list(polygon.exterior.coords)[:-1]],
        "holes": [[list(p) for p in list(ring.coords)[:-1]] for ring in polygon.interiors],
    }


def polygon_parts(geometry):
    if geometry.is_empty:
        return []
    if geometry.geom_type == "Polygon":
        return [geometry]
    return sorted(
        (part for part in geometry.geoms if part.geom_type == "Polygon" and part.area > 1e-10),
        key=lambda part: (part.bounds, part.area),
    )


def wall_cells(wall, openings, height):
    length = math.dist(wall["start"], wall["end"])
    cuts = sorted(
        {
            0.0,
            length,
            *[float(v) for op in openings for v in (op["offset"], op["offset"] + op["width"])],
        }
    )
    for index, (lo, hi) in enumerate(pairwise(cuts)):
        middle = (lo + hi) / 2
        opening = next(
            (op for op in openings if op["offset"] < middle < op["offset"] + op["width"]),
            None,
        )
        bands = (
            [(0, height)] if opening is None else [(0, opening["sill"]), (opening["head"], height)]
        )
        for band, (bottom, top) in enumerate(bands):
            if top - bottom > 1e-9:
                yield index, band, lo, hi, bottom, top


class Builder:
    def __init__(self, design, compiled):
        self.design = design
        self.components = {c["id"]: c for c in compiled["components"]}
        self.levels = {level["id"]: level for level in design["levels"]}
        # Brief records the design's semantic_refs cite for each entity, shown on its meshes.
        self.brief_records = {
            reference["entity_id"]: ", ".join(reference["requirements"])
            for reference in design.get("semantic_refs", [])
        }
        self.openings_by_wall = {}
        for opening in design["openings"]:
            self.openings_by_wall.setdefault(opening["wall_id"], []).append(opening)
        self.meshes = []
        self.quantities = {
            "rooms": {},
            "walls": {},
            "roofs": {},
            "stairs": {},
            "structure": {},
            "totals": {},
        }

    def add(
        self,
        entity,
        child,
        mesh,
        collection,
        *,
        slot="body",
        material=None,
        kind=None,
        properties=None,
        name=None,
    ):
        component = self.components[entity["id"]]
        level = entity.get("level_id", entity.get("from_level_id"))
        props = {
            "Status": "Concept geometry",
            **({"Floor level": level} if level else {}),
            **(
                {"Brief records": self.brief_records[entity["id"]]}
                if entity["id"] in self.brief_records
                else {}
            ),
            **(properties or {}),
        }
        if component["kind"] == "wall":
            props["Wall role"] = entity["role"]
            if entity["role"] == "exterior" and (kind or component["kind"]) in (
                "wall",
                "facade",
            ):
                props["Gross area role"] = "finished-exterior-boundary"
                props["Gross boundary source"] = entity["id"]
                props["Setback subject"] = True
        if component["kind"] == "roof" or (
            component["kind"] == "slab" and entity.get("role", "slab") != "ceiling"
        ):
            props["Setback subject"] = True
        descriptor = mesh_descriptor(
            component=component,
            child_id=child,
            mesh=mesh,
            collection=collection,
            transform=self.design["transform"],
            material_id=material or entity.get("material_id"),
            slot=slot,
            kind=kind,
            properties=props,
            name=name,
            generator_version=GENERATOR_VERSION,
        )
        self.meshes.append(descriptor)
        return descriptor


def _floors(builder):
    design = builder.design
    wall_unions = {
        level_id: unary_union(
            [
                as_polygon(wall_footprint(w["start"], w["end"], w["thickness"]))
                for w in sorted(design["walls"], key=lambda item: item["id"])
                if w["level_id"] == level_id
            ]
        )
        for level_id in builder.levels
    }
    for room in sorted(design["rooms"], key=lambda item: item["id"]):
        floor = (
            as_polygon(room["zone"])
            .buffer(-room["floor_inset_m"], join_style="mitre")
            .difference(wall_unions[room["level_id"]])
        )
        floor = cut_voids(design, floor, level_id=room["level_id"])
        parts = polygon_parts(floor)
        if not parts:
            raise ValueError(f"{room['id']}: walls/inset consume the entire room zone")
        level, area = builder.levels[room["level_id"]], sum(p.area for p in parts)
        top_offset = level["floor_top_offset_m"]
        finished_top = level["elevation_m"] + top_offset
        records = [polygon_json(p) for p in parts]
        builder.quantities["rooms"][room["id"]] = {
            "area_m2": area,
            "level_id": level["id"],
            "polygons": records,
            "finished_top_m": finished_top,
        }
        for i, part in enumerate(parts):
            builder.add(
                room,
                f"floor-{i:02d}",
                extrude_polygon(part, level["elevation_m"] + (top_offset - 0.002), finished_top),
                level_collection(level["id"], "Floors"),
                kind="room_floor",
                properties={
                    "Room ID": room["id"],
                    "Room name": room["name"],
                    "Room label": room.get("short_name", room["name"]),
                    "Net concept area m²": part.area,
                    "Room total area m²": area,
                    "Floor generation": "inset_zone_minus_wall_footprints",
                    "Floor top offset m": top_offset,
                },
                name=f"{room['id']} · {room['name']} | floor {i + 1}",
            )


def _walls(builder):
    for wall in sorted(builder.design["walls"], key=lambda item: item["id"]):
        level = builder.levels[wall["level_id"]]
        z = level["elevation_m"]
        height = wall.get("height_m", level["clear_height_m"])
        openings = builder.openings_by_wall.get(wall["id"], [])
        volume = 0
        cutaway = wall.get("cutaway_height_m", CUTAWAY_HEIGHT_M)
        for index, band, lo, hi, bottom, top in wall_cells(wall, openings, height):
            volume += (hi - lo) * (top - bottom) * wall["thickness"]
            for label, a, b in [
                ("low", bottom, min(top, cutaway)),
                ("high", max(bottom, cutaway), top),
            ]:
                if b - a > 1e-9:
                    builder.add(
                        wall,
                        f"span-{index:03d}-{band}-{label}",
                        wall_box(wall, lo, hi, 0, wall["thickness"], z + a, z + b),
                        level_collection(level["id"], f"Walls {label}"),
                    )
        builder.quantities["walls"][wall["id"]] = {
            "length_m": math.dist(wall["start"], wall["end"]),
            "height_m": height,
            "volume_m3": volume,
        }


def _curtain_pockets(design):
    """Plan footprints of recessed curtain pockets per level; each cuts that level's ceiling."""
    rooms = {room["id"]: room for room in design["rooms"]}
    pockets = {}
    for item in design.get("furnishings", []):
        generated = item.get("generated") or {}
        if generated.get("kind") == "curtain" and generated.get("params", {}).get("pocket"):
            room = rooms[item["room_id"]]
            pockets.setdefault(room["level_id"], []).append(furnishing_footprint(room, item))
    return pockets


def _slabs(builder):
    pockets = _curtain_pockets(builder.design)
    for slab in sorted(builder.design["slabs"], key=lambda item: item["id"]):
        role = slab.get("role", "slab")
        # Roof slabs join the roof bodies so cutaways and plans that hide the roof also hide them.
        collection = {
            "ceiling": level_collection(slab["level_id"], "Ceiling"),
            "roof": ROOF_CAP_SOLAR,
        }.get(role, level_collection(slab["level_id"], "Structure"))
        polygon = cut_voids(builder.design, as_polygon(slab["polygon"]), slab_id=slab["id"])
        if role == "ceiling" and slab["level_id"] in pockets:
            polygon = polygon.difference(unary_union(pockets[slab["level_id"]]))
            if polygon.geom_type != "Polygon":
                raise ValueError(f"{slab['id']}: curtain pockets split the ceiling")
        builder.add(
            slab,
            "body",
            extrude_polygon(
                polygon,
                slab["base_z_m"],
                slab["base_z_m"] + slab["thickness_m"],
            ),
            collection,
            kind="ceiling" if role == "ceiling" else "slab",
            name=slab["name"],
        )


def _centimetres(value):
    return f"{round(value * 100):d}"


def frame_member_mesh(member):
    """Nominal column or beam box with every face inset by ``FRAME_FACE_INSET_M``."""
    inset = FRAME_FACE_INSET_M
    bottom, top = member["bottom_z_m"] + inset, member["top_z_m"] - inset
    if member["kind"] == "column":
        (x, y), (sx, sy) = member["center"], member["section_m"]
        half_x, half_y = sx / 2 - inset, sy / 2 - inset
        return rectangle_mesh(x - half_x, y - half_y, x + half_x, y + half_y, bottom, top)
    (x0, y0), (x1, y1) = member["start"], member["end"]
    length = math.dist(member["start"], member["end"])
    dx, dy = (x1 - x0) / length, (y1 - y0) / length
    start = (x0 + dx * inset, y0 + dy * inset)
    end = (x1 - dx * inset, y1 - dy * inset)
    footprint = wall_footprint(start, end, member["width_m"] - 2 * inset)
    return oriented_box(footprint["outer"], bottom, top)


def _structure(builder):
    members = frame_members(builder.design)
    for member in members:
        if member["kind"] == "column":
            section_m, placement = member["section_m"], {}
        else:
            section_m = (member["width_m"], member["top_z_m"] - member["bottom_z_m"])
            placement = {"Structure placement": member["placement"]}
        builder.add(
            member,
            "body",
            frame_member_mesh(member),
            level_collection(member["level_id"], "Frame"),
            kind=member["kind"],
            properties={
                "Structure mark": member["mark"],
                "Structure section": "×".join(_centimetres(value) for value in section_m),
                **placement,
            },
            name=f"{member['id']} · {member['mark']}",
        )
        builder.quantities["structure"][member["id"]] = {
            "kind": member["kind"],
            "level_id": member["level_id"],
            "mark": member["mark"],
            **frame_member_measures(member),
        }
    builder.quantities["totals"].update(frame_totals(members))


def roof_mesh(roof):
    """Solid build-up from the flat structural deck up to the pitched covering surface."""
    mesh = extrude_polygon(roof["polygon"], roof["deck_z_m"], roof["deck_z_m"] + 1)
    for vertex in mesh["vertices"][len(mesh["vertices"]) // 2 :]:
        vertex[2] = roof_covering_z(roof, vertex)
    return mesh


def compile_architecture(design, compiled=None):
    """Compile current inputs; immutable baseline polygons are comparison evidence only."""
    from .architectural_details import compile_details

    compiled = compile_design(design) if compiled is None else compiled
    builder = Builder(design, compiled)
    _floors(builder)
    _walls(builder)
    _slabs(builder)
    _structure(builder)
    for void in design.get("voids", []):
        z = builder.levels[void["level_id"]]["elevation_m"]
        builder.add(
            void,
            "excluded-floor",
            extrude_polygon(as_polygon(void["polygon"]), z, z + 0.001),
            "Site | Audit footprints",
            kind="void",
            properties={"Gross area role": "excluded-void", "Room below ID": void["room_below_id"]},
        )
    for roof in sorted(design["roofs"], key=lambda item: item["id"]):
        builder.add(roof, "body", roof_mesh(roof), ROOF_CAP_SOLAR, name=roof["name"])
        builder.quantities["roofs"][roof["id"]] = {"area_m2": as_polygon(roof["polygon"]).area}
    compile_details(builder)
    totals = builder.quantities["totals"]
    totals.update(
        heated_floor_face_m2=sum(r["area_m2"] for r in builder.quantities["rooms"].values()),
        wall_volume_m3=sum(w["volume_m3"] for w in builder.quantities["walls"].values()),
    )
    comparison = {}
    for evidence in design.get("baseline_evidence", {}).get("room_finished_floors", []):
        actual = builder.quantities["rooms"].get(evidence["room_id"])
        if actual:
            comparison[evidence["room_id"]] = {
                "baseline_m2": evidence["area_m2"],
                "generated_m2": actual["area_m2"],
                "delta_m2": actual["area_m2"] - evidence["area_m2"],
            }
    builder.meshes.sort(key=lambda mesh: mesh["id"])
    return {
        "generator": {"id": "engine.architecture", "version": GENERATOR_VERSION},
        "meshes": builder.meshes,
        "quantities": builder.quantities,
        "coverage": {
            "component_ids": sorted({mesh["component_id"] for mesh in builder.meshes}),
            "generated_count": len(builder.meshes),
            "categories": dict(Counter(m["kind"] for m in builder.meshes)),
            "baseline_comparison": comparison,
        },
    }
