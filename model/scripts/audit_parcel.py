"""Audit the latest evaluated geometry export against the maintained design intent."""

import json

from project_paths import load_engine_modules

paths, persistence, requirements, design_package = load_engine_modules(
    "paths", "persistence", "requirements", "design_package"
)


def main():
    report = requirements.check_actual_geometry(
        design_package.load_design(paths.DESIGN),
        requirements.load_requirements(paths.REQUIREMENTS),
        paths.BRIEF,
        persistence.read_json(paths.ACTUAL_GEOMETRY),
    )
    persistence.atomic_write_json(paths.PARCEL_AUDIT, report)
    print(json.dumps({"summary": report["summary"]}))
    failures = [check for check in report["checks"] if check["status"] == "fail"]
    for check in failures:
        print(json.dumps(check))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
