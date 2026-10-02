"""Deterministic visual turf; the existing flat floor retains all physics."""
import math
import random
from pxr import Gf, Sdf, UsdGeom, UsdShade


def apply_turf(stage, width=3.0, height=2.0):
    root = '/World/Arena'
    mat = UsdShade.Material.Define(stage, root + '/Materials/Turf')
    shader = UsdShade.Shader.Define(stage, str(mat.GetPath()) + '/Shader')
    shader.CreateIdAttr('UsdPreviewSurface')
    shader.CreateInput('diffuseColor', Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(.04, .20, .05))
    shader.CreateInput('roughness', Sdf.ValueTypeNames.Float).Set(.95)
    mat.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(), 'surface')
    UsdShade.MaterialBindingAPI.Apply(stage.GetPrimAtPath(root + '/Floor/Field')).Bind(mat)
    line = stage.GetPrimAtPath(root + '/Markings/CenterLine')
    if line:
        line.SetActive(False)

    # One mesh with varied blades, no per-blade prims or collision shapes. Each
    # blade is a thin card: two base points spaced across a random lean angle
    # (its width) and a tip leaning further along that same angle (its height),
    # so the blade reads as a short leaning card instead of a twisted sliver.
    #
    # A blade card standing this close to vertical has a true cross-product face
    # normal that points mostly sideways, not up, so under the arena's ambient
    # dome light most blades rendered near-black at a low viewing angle (seen when
    # this draft was first rendered and inspected). Real short-pile turf reads as
    # evenly green because of inter-fibre bounce light that a flat, untextured
    # triangle can't reproduce, so the face normal is authored explicitly, biased
    # toward +Z with only a small lean-direction component for grain variation,
    # instead of using the true geometric normal.
    rng = random.Random(20260910)
    points, colors, normals = [], [], []
    palette = [(.09, .32, .085), (.13, .38, .10), (.17, .42, .12), (.06, .26, .07)]
    count = int(width * height * 18000)
    for _ in range(count):
        x = rng.uniform(-width / 2 + .006, width / 2 - .006)
        y = rng.uniform(-height / 2 + .006, height / 2 - .006)
        a = rng.uniform(0, math.tau)
        perp = (-math.sin(a), math.cos(a))
        lean = (math.cos(a), math.sin(a))
        half_w = rng.uniform(.0009, .0016)
        lean_amt = rng.uniform(.0015, .0030)
        z = rng.uniform(.0035, .007)
        points.extend([
            (x - half_w * perp[0], y - half_w * perp[1], .0002),
            (x + half_w * perp[0], y + half_w * perp[1], .0002),
            (x + lean_amt * lean[0], y + lean_amt * lean[1], z),
        ])
        colors.append(palette[rng.randrange(len(palette))])
        nx, ny, nz = lean[0] * .22, lean[1] * .22, 1.0
        n_len = math.sqrt(nx * nx + ny * ny + nz * nz)
        normals.append((nx / n_len, ny / n_len, nz / n_len))
    mesh = UsdGeom.Mesh.Define(stage, root + '/Floor/TurfBlades')
    mesh.CreatePointsAttr(points)
    mesh.CreateFaceVertexCountsAttr([3] * count)
    mesh.CreateFaceVertexIndicesAttr(list(range(count * 3)))
    mesh.CreateSubdivisionSchemeAttr('none')
    mesh.CreateDoubleSidedAttr(True)
    mesh.CreateDisplayColorPrimvar(UsdGeom.Tokens.uniform).Set(colors)
    mesh.CreateNormalsAttr(normals)
    mesh.SetNormalsInterpolation(UsdGeom.Tokens.uniform)
    mesh.CreateExtentAttr([(-width/2, -height/2, 0), (width/2, height/2, .007)])
    blade_mat = UsdShade.Material.Define(stage, root + '/Materials/TurfBlades')
    reader = UsdShade.Shader.Define(stage, str(blade_mat.GetPath()) + '/Color')
    reader.CreateIdAttr('UsdPrimvarReader_float3')
    reader.CreateInput('varname', Sdf.ValueTypeNames.Token).Set('displayColor')
    reader.CreateOutput('result', Sdf.ValueTypeNames.Float3)
    surface = UsdShade.Shader.Define(stage, str(blade_mat.GetPath()) + '/Shader')
    surface.CreateIdAttr('UsdPreviewSurface')
    surface.CreateInput('diffuseColor', Sdf.ValueTypeNames.Color3f).ConnectToSource(reader.ConnectableAPI(), 'result')
    surface.CreateInput('roughness', Sdf.ValueTypeNames.Float).Set(.98)
    blade_mat.CreateSurfaceOutput().ConnectToSource(surface.ConnectableAPI(), 'surface')
    UsdShade.MaterialBindingAPI.Apply(mesh.GetPrim()).Bind(blade_mat)
    mesh.GetPrim().CreateAttribute('arena:visualOnly', Sdf.ValueTypeNames.Bool).Set(True)
