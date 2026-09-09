# Panda–Human Voxel Distance

ROS 2 workspace for PeopleSemSegNet-based human voxels, TF-transformed Panda
collision-mesh voxels, and filtered minimum-distance estimation in Isaac Sim.

## Environment

Validated on the following configuration. Other combinations may work but are
untested.

**Hardware**

- CPU: AMD Ryzen 9 5900X (12C/24T)
- GPU: NVIDIA GeForce RTX 3070 (8 GB VRAM)
- RAM: 32 GB

**Software**

- Ubuntu 22.04.5 LTS
- NVIDIA driver 560.35.05
- CUDA 12.6
- TensorRT 10.7.0.23
- VPI 3.2.4
- ROS 2 Humble
- Isaac Sim 4.2.0
- Isaac ROS (NITROS) — `release-3.0` apt channel
  - `isaac-ros-nitros` / `isaac-ros-nvblox` / `isaac-ros-common` 3.2.5
  - `isaac-ros-unet` / `isaac-ros-tensor-rt` / `isaac-ros-tensor-proc` / `isaac-ros-triton` / `isaac-ros-dnn-image-encoder` 3.2.10
  - `isaac-ros-visual-slam` 3.2.6

## Installation

### 1. Prerequisites

- Install ROS 2 Humble (desktop or base) following the
  [official ROS 2 installation guide](https://docs.ros.org/en/humble/Installation.html).
- Install the standard ROS 2 build tools: `python3-colcon-common-extensions`,
  `python3-rosdep`, `python3-vcstool` (and run `rosdep init` / `rosdep update`
  if this is a fresh ROS 2 install).
- Install [git-lfs](https://git-lfs.com/) and run `git lfs install` once per
  machine — this repo stores `my_world/Materials/carter_nvblox_ros.usd`
  (145 MB) via LFS, so without it the file is just a pointer stub after
  cloning. Run `git lfs pull` after cloning if the asset didn't come down
  automatically.

### 2. NVIDIA driver + CUDA 12.6

```bash
sudo apt install nvidia-driver-560

wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/cuda-keyring_1.1-1_all.deb
sudo dpkg -i cuda-keyring_1.1-1_all.deb
sudo apt update
sudo apt install cuda-toolkit-12-6
```

TensorRT (`libnvinfer*` 10.7.0.23) is pulled in transitively while installing
the Isaac ROS packages below, matched to CUDA 12.6.

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

Install the standalone package under `~/.local/share/ov/pkg/isaac_sim-4.2.0`
(via Omniverse Launcher, or by extracting the standalone
`isaac-sim-standalone@4.2.0` archive to that path).

### 6. `~/.bashrc` environment

```bash
# ============================================================
# CUDA 12.6
# ============================================================
export CUDA_HOME="/usr/local/cuda-12.6"
export PATH="$CUDA_HOME/bin:$PATH"
export LD_LIBRARY_PATH="$CUDA_HOME/targets/x86_64-linux/lib:/usr/local/lib"

# ============================================================
# Isaac Sim 4.2
# ============================================================
export ISAAC_SIM_PATH="$HOME/.local/share/ov/pkg/isaac_sim-4.2.0"
export OMNI_PY="$ISAAC_SIM_PATH/python.sh"

alias omni_python="$OMNI_PY"
alias isaacsim="$ISAAC_SIM_PATH/isaac-sim.sh"

# ============================================================
# Isaac ROS / nvblox workspace
# ============================================================
export ISAAC_ROS_WS="$HOME/panda_human_ws"

# ============================================================
# ROS 2 Humble underlay
# ============================================================
# Keep this single-machine Isaac Sim workspace isolated from ROS 2
# participants (and especially /clock publishers) on the local network.
unset ROS_DOMAIN_ID
export ROS_LOCALHOST_ONLY=1

# Discard inherited ROS overlays before loading the selected workspace.
unset AMENT_PREFIX_PATH CMAKE_PREFIX_PATH COLCON_PREFIX_PATH ROS_PACKAGE_PATH PYTHONPATH

if [ -f "/opt/ros/humble/setup.bash" ]; then
    source "/opt/ros/humble/setup.bash"
fi

# Primary ROS 2 workspace overlay: ~/panda_human_ws
if [ -f "$ISAAC_ROS_WS/install/setup.bash" ]; then
    source "$ISAAC_ROS_WS/install/setup.bash"
fi
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

The `.plan` files under `models/peoplesemsegnet/1/` are TensorRT engines,
which are tied to the exact GPU + TensorRT version they were built on, so
they are intentionally not tracked in git — only the source `.onnx` weights
(in `models/peoplesemsegnet/`) are. Build the engine(s) you need with
`trtexec` (installed as part of TensorRT, see step 2/4 above):

```bash
cd "$HOME/panda_human_ws/models/peoplesemsegnet"
mkdir -p 1

# Original engine, used in Terminal 3's "original" launch (output: argmax_1)
/usr/src/tensorrt/bin/trtexec \
  --onnx=model.onnx \
  --saveEngine=1/model.plan \
  --shapes=input_2:1x544x960x3 \
  --fp16

# 0.90-threshold lightweight variant (output: threshold_mask)
/usr/src/tensorrt/bin/trtexec \
  --onnx=model_threshold_090.onnx \
  --saveEngine=1/model_threshold_090.plan \
  --shapes=input_2:1x544x960x3 \
  --fp16
```

`--fp16` matches the precision this workspace was validated with; drop it to
build an FP32 engine instead. Repeat for any other `model_*.onnx` variant you
want to run, saving to the matching `1/model_*.plan` name.

* * *

## Run

Open `my_world/env_panda_human.usd` in Isaac Sim, then run the following in
five terminals.

#### Terminal 1 — Launch Isaac Sim

```bash
isaacsim
```

#### Terminal 2 — CameraInfo fix node

```bash
ros2 run my_peoplesemseg_bringup camera_info_fix
```

#### Terminal 3 — ShuffleSeg segmentation engine

- Original engine

```bash
MODEL_DIR="$HOME/panda_human_ws/models/peoplesemsegnet"

ros2 launch isaac_ros_unet \
  isaac_ros_unet_tensor_rt_isaac_sim.launch.py \
  engine_file_path:="$MODEL_DIR/1/model.plan" \
  input_binding_names:="[input_2]" \
  output_binding_names:="[argmax_1]" \
  use_planar_input:=False \
  network_output_type:=argmax
```

- 0.90-threshold lightweight variant

```bash
MODEL_DIR="$HOME/panda_human_ws/models/peoplesemsegnet"

ros2 launch my_peoplesemseg_bringup \
  my_unet_tensor_rt_isaac_sim.launch.py \
  engine_file_path:="$MODEL_DIR/1/model_threshold_090.plan" \
  input_binding_names:="[input_2]" \
  output_binding_names:="[threshold_mask]" \
  use_planar_input:=False \
  network_output_type:=argmax
```

#### Terminal 4 — Mask resize

```bash
ros2 run my_peoplesemseg_bringup mask_resize
```

#### Terminal 5 — nvblox people segmentation + sphere monitoring/debug rviz

```bash
ros2 launch my_people_nvblox_bringup \
  panda_human_segmentation.launch.py \
  mode:=people_segmentation \
  num_cameras:=1
```

### Distance graphs (optional)

Run alongside the five terminals above to plot the closest Panda–human
distance live.

#### Terminal 1 — `d_filtered` plot

```bash
source ~/my_ws/install/setup.bash
ros2 run my_people_nvblox_bringup plot_filtered_distance
```

#### Terminal 2 — `d_raw` vs. `d_filtered` comparison

```bash
source ~/my_ws/install/setup.bash
ros2 run my_people_nvblox_bringup plot_distances
```
