# Panda–Human Voxel Distance

ROS 2 workspace for PeopleSemSegNet-based human voxels, TF-transformed Panda
collision-mesh voxels, and filtered minimum-distance estimation in Isaac Sim.

## Workspace setup

```bash
cd "$HOME/panda_human_ws"
vcs import src < isaac_ros_nvblox.repos
git -C src/isaac_ros_nvblox submodule update --init --recursive
git -C src/isaac_ros_nvblox apply patches/nvblox_skip_empty_deletion.patch
colcon build --symlink-install --cmake-args -DBUILD_TESTING=OFF
source install/setup.bash
```

The local TensorRT engines are intentionally not tracked. Put them under
`isaac_ros_assets/models/` or regenerate them for the target GPU/TensorRT version.

## Run

Use the same five-terminal sequence as the validated original workspace, replacing
`$HOME/my_ws` with `$HOME/panda_human_ws` in the model path.
