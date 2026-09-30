# Panda–Human Voxel Distance

ROS 2 workspace for PeopleSemSegNet-based human voxels, TF-transformed Panda
collision-mesh voxels, and filtered minimum-distance estimation in Isaac Sim.

## Environment

**Hardware**: AMD Ryzen 9 5900X, NVIDIA RTX 3070 (8 GB VRAM), 32 GB RAM.

**Software**: Ubuntu 22.04.5, NVIDIA driver 560.35.05, CUDA 12.6, TensorRT
10.7.0.23, VPI 3.2.4, ROS 2 Humble, Isaac Sim 4.2.0, Isaac ROS (NITROS)
`release-3.0`:
`isaac-ros-nitros`/`isaac-ros-nvblox`/`isaac-ros-common` 3.2.5,
`isaac-ros-unet`/`isaac-ros-tensor-rt`/`isaac-ros-tensor-proc`/`isaac-ros-triton`/`isaac-ros-dnn-image-encoder`
3.2.10, `isaac-ros-visual-slam` 3.2.6. Other combinations untested.

## Installation

### 1. Prerequisites

- ROS 2 Humble ([install guide](https://docs.ros.org/en/humble/Installation.html))
  + `python3-colcon-common-extensions` `python3-rosdep` `python3-vcstool`
  (`rosdep init && rosdep update` on a fresh install).
- [git-lfs](https://git-lfs.com/): `git lfs install` once per machine, then
  `git lfs pull` after cloning (`my_world/Materials/carter_nvblox_ros.usd` is
  LFS-tracked).

### 2. NVIDIA driver + CUDA 12.6

```bash
sudo apt install nvidia-driver-560

wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/cuda-keyring_1.1-1_all.deb
sudo dpkg -i cuda-keyring_1.1-1_all.deb
sudo apt update
sudo apt install cuda-toolkit-12-6
```

### 3. VPI 3.2.4

```bash
curl -fsSL https://repo.download.nvidia.com/jetson/jetson-ota-public.asc \
  | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-jetson-ota-public.gpg

echo "deb [arch=amd64 signed-by=/usr/share/keyrings/nvidia-jetson-ota-public.gpg] https://repo.download.nvidia.com/jetson/x86_64/jammy r36.4 main" \
  | sudo tee /etc/apt/sources.list.d/nvidia-vpi.list
sudo apt update
sudo apt install libnvvpi3 vpi3-dev
```

### 4. Isaac ROS apt packages (NITROS)

```bash
curl -fsSL https://isaac.download.nvidia.com/isaac-ros/repos.key \
  | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-isaac-ros.gpg

echo "deb [arch=amd64 signed-by=/usr/share/keyrings/nvidia-isaac-ros.gpg] https://isaac.download.nvidia.com/isaac-ros/release-3 jammy release-3.0" \
  | sudo tee /etc/apt/sources.list.d/nvidia-isaac-ros.list
sudo apt update
sudo apt install \
  ros-humble-isaac-ros-nvblox \
  ros-humble-isaac-ros-unet \
  ros-humble-isaac-ros-tensor-rt \
  ros-humble-isaac-ros-triton \
  ros-humble-isaac-ros-visual-slam
```

### 5. Isaac Sim 4.2.0

Install to `~/.local/share/ov/pkg/isaac_sim-4.2.0` (Omniverse Launcher, or
extract the standalone `isaac-sim-standalone@4.2.0` archive there).

### 6. `~/.bashrc` environment

```bash
# CUDA 12.6
export CUDA_HOME="/usr/local/cuda-12.6"
export PATH="$CUDA_HOME/bin:$PATH"
export LD_LIBRARY_PATH="$CUDA_HOME/targets/x86_64-linux/lib:/usr/local/lib"

# Isaac Sim 4.2
export ISAAC_SIM_PATH="$HOME/.local/share/ov/pkg/isaac_sim-4.2.0"
export OMNI_PY="$ISAAC_SIM_PATH/python.sh"
alias omni_python="$OMNI_PY"
alias isaacsim="$ISAAC_SIM_PATH/isaac-sim.sh"

# Isaac ROS / nvblox workspace
export ISAAC_ROS_WS="$HOME/panda_human_ws"

# Keep this workspace isolated from other ROS 2 participants on the network.
unset ROS_DOMAIN_ID
export ROS_LOCALHOST_ONLY=1

unset AMENT_PREFIX_PATH CMAKE_PREFIX_PATH COLCON_PREFIX_PATH ROS_PACKAGE_PATH PYTHONPATH
[ -f "/opt/ros/humble/setup.bash" ] && source "/opt/ros/humble/setup.bash"
[ -f "$ISAAC_ROS_WS/install/setup.bash" ] && source "$ISAAC_ROS_WS/install/setup.bash"
```

### 7. Workspace setup

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

### 8. Regenerate TensorRT engines

`models/peoplesemsegnet/shuffleseg/` and `.../vanilla/` hold the source
`.onnx` weights; the `.plan` engines under each `1/` are GPU/TensorRT-version
specific and not tracked in git. Build with `trtexec`:

```bash
cd "$HOME/panda_human_ws/models/peoplesemsegnet/shuffleseg"
mkdir -p 1

# Original (output: argmax_1)
/usr/src/tensorrt/bin/trtexec \
  --onnx=model.onnx --saveEngine=1/model.plan \
  --shapes=input_2:1x544x960x3 --fp16

# 0.90-threshold lightweight variant (output: threshold_mask)
/usr/src/tensorrt/bin/trtexec \
  --onnx=model_threshold_090.onnx --saveEngine=1/model_threshold_090.plan \
  --shapes=input_2:1x544x960x3 --fp16
```

Drop `--fp16` for an FP32 engine.

* * *

## Run

Open `my_world/env_panda_human.usd` in Isaac Sim, then run five terminals.

#### Terminal 1 — Isaac Sim

```bash
isaacsim
```

#### Terminal 2 — CameraInfo fix node

```bash
ros2 run my_peoplesemseg_bringup camera_info_fix
```

#### Terminal 3 — ShuffleSeg segmentation engine

Original engine:

```bash
MODEL_DIR="$HOME/panda_human_ws/models/peoplesemsegnet/shuffleseg"

ros2 launch isaac_ros_unet \
  isaac_ros_unet_tensor_rt_isaac_sim.launch.py \
  engine_file_path:="$MODEL_DIR/1/model.plan" \
  input_binding_names:="[input_2]" \
  output_binding_names:="[argmax_1]" \
  use_planar_input:=False \
  network_output_type:=argmax
```

0.90-threshold lightweight variant:

```bash
MODEL_DIR="$HOME/panda_human_ws/models/peoplesemsegnet/shuffleseg"

ros2 launch my_peoplesemseg_bringup \
  my_unet_tensor_rt_isaac_sim.launch.py \
  engine_file_path:="$MODEL_DIR/1/model_threshold_090.plan" \
  input_binding_names:="[input_2]" \
  output_binding_names:="[threshold_mask]" \
  use_planar_input:=False \
  network_output_type:=argmax
```

Pick one, not both — running both at once can exhaust an 8 GB GPU.

#### Terminal 4 — Mask resize

```bash
ros2 run my_peoplesemseg_bringup mask_resize
```

#### Terminal 5 — nvblox people segmentation + sphere debug rviz

```bash
ros2 launch my_people_nvblox_bringup \
  panda_human_segmentation.launch.py \
  mode:=people_segmentation \
  num_cameras:=1
```

Opens two RViz windows: the main monitoring view (people highlighted in the
camera overlay, Panda/human voxel distance) and a lighter Panda-only debug
view (`panda_sphere_debug.rviz`, `run_panda_debug_rviz:=false` to disable).

### Distance graphs (optional)

```bash
source ~/panda_human_ws/install/setup.bash
ros2 run my_people_nvblox_bringup plot_filtered_distance   # d_filtered
ros2 run my_people_nvblox_bringup plot_distances            # d_raw vs d_filtered
```
