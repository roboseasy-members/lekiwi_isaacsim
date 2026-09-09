"""SO101 손가락의 오목한 안쪽 면을 보존하는 충돌 형상 설정."""

FINGER_COLLIDERS = (
    "gripper_link/collisions/wrist_roll_follower_so101_v1/node_STL_BINARY_",
    "moving_jaw_so101_v1_link/collisions/moving_jaw_so101_v1/node_STL_BINARY_",
)


def configure_gripper_collisions(stage, base_path="/LeKiwi/base_link"):
    from pxr import UsdPhysics

    paths = [base_path + "/" + suffix for suffix in FINGER_COLLIDERS]
    # 누락된 자산에는 일부 설정만 적용하지 않는다.
    for path in paths:
        prim = stage.GetPrimAtPath(path)
        if not prim or not prim.HasAPI(UsdPhysics.MeshCollisionAPI):
            raise ValueError(f"SO101 finger collider is missing: {path}")
    for path in paths:
        # 참조 원본과 시각 메시를 보존하고 현재 장면의 충돌 분기만 편집한다.
        branch = stage.GetPrimAtPath(path.split("/collisions/")[0] + "/collisions")
        branch.SetInstanceable(False)
        collider = stage.GetPrimAtPath(path)
        UsdPhysics.MeshCollisionAPI(collider).CreateApproximationAttr(
            "convexDecomposition"
        )
    return paths
