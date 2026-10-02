"""Create non-destructive turf layers over the existing net arena USDs."""
from pathlib import Path
from pxr import Usd, UsdPhysics
from turf_floor import apply_turf

root = Path(__file__).resolve().parent
for layout in 'ABCD':
    for suffix in ('', '_4robots'):
        source = root / f'lekiwi_arena_3p0x2p0_net_{layout}{suffix}.usd'
        output = source.with_name(source.stem + '_turf.usd')
        stage = Usd.Stage.CreateNew(str(output))
        stage.GetRootLayer().subLayerPaths = ['./' + source.name]
        size = stage.GetPrimAtPath('/World/Arena').GetAttribute('arena:interiorSizeMeters').Get()
        apply_turf(stage, *size)
        stage.GetRootLayer().Save()
        check = Usd.Stage.Open(str(output))
        assert not check.GetPrimAtPath('/World/Arena/Markings/CenterLine').IsActive()
        assert check.GetPrimAtPath('/World/Arena/Floor/Field').HasAPI(UsdPhysics.CollisionAPI)
        assert not check.GetPrimAtPath('/World/Arena/Floor/TurfBlades').HasAPI(UsdPhysics.CollisionAPI)
        original = Usd.Stage.Open(str(source))
        for prim in original.Traverse():
            if any(str(prim.GetPath()).startswith('/World/Arena/' + p) for p in ('Floor', 'Materials', 'Markings')):
                continue
            updated = check.GetPrimAtPath(prim.GetPath())
            assert updated and updated.GetTypeName() == prim.GetTypeName()
            for attr in prim.GetAttributes():
                assert updated.GetAttribute(attr.GetName()).Get() == attr.Get(), (prim.GetPath(), attr.GetName())
        print('PASS', output.name, flush=True)
