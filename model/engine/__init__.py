"""Procedural house model engine.

The package initializer deliberately imports no host-only dependencies. Blender
adapters can therefore import native submodules such as ``engine.assets`` without
loading Shapely. Host callers import ``engine.design_package`` and ``engine.compiler``
explicitly.
"""
