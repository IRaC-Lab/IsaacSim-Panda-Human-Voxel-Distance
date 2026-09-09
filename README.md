# Panda–Human Voxel Distance

ROS 2 workspace for PeopleSemSegNet-based human voxels, TF-transformed Panda
collision-mesh voxels, and filtered minimum-distance estimation in Isaac Sim.

## Workspace setup

```bash
cd "$HOME/panda_human_ws"
vcs import src < isaac_ros_nvblox.repos
git -C src/isaac_ros_nvblox submodule update --init --recursive
git -C src/isaac_ros_nvblox apply patches/nvblox_skip_empty_deletion.patch
colcon build --symlink-install \
  --packages-up-to my_people_nvblox_bringup my_peoplesemseg_bringup \
  --cmake-args -DBUILD_TESTING=OFF
source install/setup.bash
```

The local TensorRT engines are intentionally not tracked. Put them under
`models/peoplesemsegnet/1/` or regenerate them for the target GPU/TensorRT version.

## Run

Open `my_world/env_panda_human.usd` in Isaac Sim. Use the same five-terminal
sequence as the validated original workspace, with:

```bash
MODEL_DIR="$HOME/panda_human_ws/models/peoplesemsegnet"
```

Launch the nvblox pipeline with:

```bash
ros2 launch my_people_nvblox_bringup \
  panda_human_segmentation.launch.py \
  mode:=people_segmentation \
  num_cameras:=1
```
