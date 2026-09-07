"""Check USD dependency closure without starting Isaac or writing the stage."""

from pathlib import Path


# This is an Isaac-supplied shader library, not a robot mesh/texture download.
# The current asset renders with PreviewSurface but retains the imported MDL
# definitions in its base layer. Never exempt arbitrary unresolved assets.
ISAAC_SHADER_LIBRARIES = {"OmniPBR.mdl"}
ISAAC_SHADER_PATHS = {Path("/isaac-sim/kit/mdl/core/Base/OmniPBR.mdl")}


def validate_bundle_dependencies(usd_path):
    from pxr import UsdUtils

    usd_path = Path(usd_path).resolve(strict=True)
    bundle_root = usd_path.parent.parent
    layers, assets, unresolved = UsdUtils.ComputeAllDependencies(str(usd_path))
    missing = set(unresolved) - ISAAC_SHADER_LIBRARIES
    if missing:
        raise AssertionError(f"Missing USD dependencies: {sorted(missing)}")
    for path in [layer.realPath for layer in layers]:
        resolved = Path(path).resolve(strict=True)
        if not resolved.is_relative_to(bundle_root):
            raise AssertionError(f"USD dependency escapes robot bundle: {path}")
    for path in assets:
        resolved = Path(path).resolve(strict=True)
        if not resolved.is_relative_to(bundle_root) and resolved not in ISAAC_SHADER_PATHS:
            raise AssertionError(f"USD dependency escapes robot bundle: {path}")
    # Relative dependencies are required even if an absolute reference happens
    # to exist on this developer's machine.
    for layer in layers:
        for reference in layer.GetCompositionAssetDependencies():
            if Path(reference).is_absolute() or ":" in reference:
                raise AssertionError(f"Nonportable USD layer reference: {reference}")
    print(
        f"LEKIWI_BUNDLE dependencies=PASS layers={len(layers)} "
        f"external_assets={len(assets)} "
        f"isaac_shader_libraries={','.join(sorted(set(unresolved) & ISAAC_SHADER_LIBRARIES)) or 'resolved'}"
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("usd", nargs="?", default=str(
        Path(__file__).resolve().parent / "assets/lekiwi_soarm/usd/lekiwi_soarm.usd"
    ))
    validate_bundle_dependencies(parser.parse_args().usd)
