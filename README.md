# Panda–Human Voxel Distance

ROS 2 workspace for PeopleSemSegNet-based human voxels, TF-transformed Panda
collision-mesh voxels, and filtered minimum-distance estimation. Runs either
against Isaac Sim (see below) or a real Panda + RealSense rig — see
[Real robot](#real-robot-jetson-agx-orin) — sharing the same perception and
distance-estimation packages (`my_people_nvblox_bringup`,
`my_peoplesemseg_bringup`, `panda_camera_alignment`).

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
source ~/panda_human_ws/install/setup.bash
ros2 run my_people_nvblox_bringup plot_filtered_distance
```

#### Terminal 2 — `d_raw` vs. `d_filtered` comparison

```bash
source ~/panda_human_ws/install/setup.bash
ros2 run my_people_nvblox_bringup plot_distances
```

* * *

## Real robot (Jetson AGX Orin)

Same perception/distance stack as above, but against a physical Panda +
RealSense rig instead of Isaac Sim. Adds two packages: `panda_pick_place`
(joint-space left/right pick-and-place) and `panda_real_bringup` (bringup
launch tying the camera, alignment, perception, and Panda TF together).

### Hardware

- Panda arm, System 4.2.2, with a Franka Hand gripper
- Intel RealSense (tested: D435-class), fixed or on an ArUco-tracked mount
- Jetson AGX Orin — match JetPack/L4T and the Isaac ROS release actually
  installed to your board; the versions pinned under **Environment** above
  are for the Isaac Sim desktop, not this path

### Why not the official `franka_ros2` driver

Panda (System 4.x) needs **libfranka 0.9.x**. The official
[franka_ros2](https://github.com/frankaemika/franka_ros2) driver targets FR3
and newer libfranka, and doesn't support Panda on ROS 2. This setup uses the
community fork [LCAS/franka_arm_ros2](https://github.com/LCAS/franka_arm_ros2),
which is tested against Panda + libfranka 0.9.2 + Humble + ros2_control.

### Installation

#### 1. libfranka 0.9.2

Built standalone (not a colcon package), pinned to the exact release Panda's
FCI expects:

```bash
sudo apt remove ros-humble-libfranka   # if present: wrong version for Panda
sudo apt install ros-humble-ros2-controllers ros-humble-joint-trajectory-controller

git clone --recursive https://github.com/frankarobotics/libfranka.git ~/libfranka
cd ~/libfranka
git checkout 0.9.2
git submodule update --init --recursive
mkdir build && cd build
cmake -DCMAKE_BUILD_TYPE=Release ..
cmake --build . -j"$(nproc)"
```

#### 2. `franka_arm_ros2` (LCAS fork)

Imported like `isaac_ros_nvblox` above — pinned via `.repos`, not vendored:

```bash
cd "$HOME/panda_human_ws"
vcs import src < franka_arm_ros2.repos
colcon build --symlink-install \
  --packages-select franka_description franka_msgs franka_semantic_components \
    franka_hardware franka_gripper franka_control2 franka_example_controllers \
  --cmake-args -DFranka_DIR="$HOME/libfranka/build" -DBUILD_TESTING=OFF
```

#### 3. `~/.bashrc` additions

```bash
export LD_LIBRARY_PATH="$HOME/libfranka/build:${LD_LIBRARY_PATH:-}"
```

(The rest of the environment — `ISAAC_ROS_WS`, ROS 2 underlay, etc. — is the
same as step 6 in the main Installation section above.)

#### 4. Build the real-robot packages

```bash
cd "$HOME/panda_human_ws"
colcon build --symlink-install \
  --packages-up-to panda_pick_place panda_real_bringup \
  --cmake-args -DFranka_DIR="$HOME/libfranka/build" -DBUILD_TESTING=OFF
source install/setup.bash
```

### Run

Five terminals. On the Desk web UI, activate FCI before Terminal 1.

#### Terminal 1 — Panda driver + TF + pick-and-place controller

```bash
ros2 launch panda_pick_place panda_control.launch.py robot_ip:=172.16.0.2
```

#### Terminal 2 — RealSense

```bash
ros2 launch nvblox_examples_bringup realsense.launch.py \
  run_standalone:=True \
  color_profile:=1280x720x15 \
  depth_profile:=848x480x15
```

#### Terminal 3 — ArUco camera alignment

Use `mode:=dynamic` while the camera mount isn't fixed yet; switch to
`mode:=static` (with `num_samples:=15`) once it's permanently mounted.

```bash
ros2 launch panda_camera_alignment aruco_align.launch.py \
  mode:=dynamic \
  camera_mount_frame:=camera0_link
```

#### Terminal 4 — People segmentation + nvblox + Panda/human distance

```bash
MODEL_DIR="$HOME/panda_human_ws/models/peoplesemsegnet"

ros2 launch panda_real_bringup panda_realsense_people.launch.py \
  run_realsense:=False \
  run_alignment:=False \
  run_rviz:=False \
  people_segmentation:=peoplesemsegnet_vanilla \
  vanilla_engine_file_path:="$MODEL_DIR/1/model_vanilla_v2_0_2.plan" \
  segmentation_output_binding_names:='["argmax_1"]'
```

#### Terminal 5 — RViz

Full monitoring view:

```bash
rviz2 -d ~/panda_human_ws/src/panda_real_bringup/config/panda_realsense_people.rviz
```

Or, for a lighter arm-only debug view (Panda RobotModel + collision spheres,
no camera/segmentation required — just Terminal 1 and Terminal 4's TF-driven
nodes):

```bash
rviz2 -d ~/panda_human_ws/src/my_people_nvblox_bringup/config/visualization/panda_sphere_debug.rviz
```

#### Terminal 6 (optional) — Pick-and-place motion

Left/right joint-space pick-and-place, repeating until Ctrl+C (which returns
the arm to its home pose before stopping; a second Ctrl+C halts in place
instead). See `panda_pick_place/config/pick_place.yaml` to adjust waypoints,
speed, and gripper force before running on real hardware.

```bash
ros2 run panda_pick_place pick_place_node --ros-args \
  --params-file ~/panda_human_ws/src/panda_pick_place/config/pick_place.yaml
```

### Known gaps

- The Panda/human minimum distance (`/closest_panda_human/distance`) is
  computed but not yet wired into `pick_place_node` — no automatic slowdown
  or stop when a person gets close. Planned next step.
- `panda_realsense_people.launch.py`'s `people_segmentation` /
  `shuffleseg_engine_file_path` handling only forwards the ShuffleSeg engine
  path to `segmentation.launch.py`; a `vanilla_engine_file_path` CLI override
  is accepted but not forwarded, so switching to the vanilla model currently
  relies on `segmentation.launch.py`'s own default for that engine path.
