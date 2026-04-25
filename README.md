# FFW Robot Stack - ai-worker-sim

---

## Step 1 - Clone the Repository

```bash
git clone https://github.com/ETGAH/ai-worker-sim.git
cd ai-worker-sim
```

---

## Step 2 - Install Dependencies (Binary Only)

```bash
sudo apt update
sudo apt install ros-jazzy-gz-ros2-control
sudo apt install ros-jazzy-moveit
sudo apt install ros-jazzy-realsense2-description
sudo apt install ros-jazzy-dual-laser-merger
```

---

## Step 3 - Fix Realsense System Files (Once Only)

The realsense description installed by apt also uses `package://` URIs. Fix it once:

```bash
find /opt/ros/jazzy/share/realsense2_description -name "*.xacro" -o -name "*.urdf" | \
  xargs grep -l "package://realsense2_description/meshes" 2>/dev/null | while read f; do
    cp --remove-destination "$f" "$f.bak"
    mv "$f.bak" "$f"
    sed -i "s|package://realsense2_description/meshes|file:///opt/ros/jazzy/share/realsense2_description/meshes|g" "$f"
done
```

---

## Step 4 - Build the Workspace

```bash
source /opt/ros/jazzy/setup.bash
colcon build --allow-overriding ffw_description
source install/setup.bash
```

---

## Step 5 - Fix Mesh URIs for GzWeb

> **Run this after every `colcon build`.**

**Why this is needed:**

- RViz requires `package://` URIs in source files to resolve meshes via the ROS package system
- GzWeb runs in the browser and cannot resolve `package://` URIs, it needs `file://` absolute paths
- This step converts URIs only in `install/` so GzWeb works, while `src/` keeps `package://` so RViz works

```bash
# Step 5a — Make sure src has package:// (restore if needed)
MESH_BASE="file:///root/workspaces/etgah_ws/install/ffw_description/share/ffw_description/meshes"

find /root/workspaces/etgah_ws/src/ai-worker-sim/ffw_description/urdf -type f | \
  xargs sed -i "s|${MESH_BASE}|package://ffw_description/meshes|g" 2>/dev/null || true

find /root/workspaces/etgah_ws/src/ai-worker-sim/ffw_description/urdf -type f | \
  xargs sed -i "s|file:///opt/ros/jazzy/share/realsense2_description/meshes|package://realsense2_description/meshes|g" 2>/dev/null || true

# Step 5b — Rebuild so install gets fresh files from src
colcon build --allow-overriding ffw_description
source install/setup.bash

# Step 5c — Convert package:// to file:// in install only
MESH_BASE="file:///root/workspaces/etgah_ws/install/ffw_description/share/ffw_description/meshes"

find /root/workspaces/etgah_ws/install/ffw_description/share/ffw_description/urdf -type f | \
  xargs sed -i "s|package://ffw_description/meshes|${MESH_BASE}|g"

find /root/workspaces/etgah_ws/install/ffw_description/share/ffw_description/urdf -type f | \
  xargs sed -i "s|package://realsense2_description/meshes|file:///opt/ros/jazzy/share/realsense2_description/meshes|g"
```

Verify fix worked (should print 0):

```bash
xacro install/ffw_description/share/ffw_description/urdf/ffw_sg2_rev1_follower/ffw_sg2_follower.urdf.xacro \
  model:=ffw_sg2_rev1_follower use_sim:=true | grep "filename" | grep "package://" | wc -l
```

---

## Step 6 - Launch the Simulation

For the sg2 robot:

```bash
ros2 launch ffw_bringup ffw_sg2_follower_ai_gazebo.launch.py
```

---

## Re-building After Changes

Repeat Steps 5 and 6 after every code change:

```bash
# Restore src to package://
MESH_BASE="file:///root/workspaces/etgah_ws/install/ffw_description/share/ffw_description/meshes"
find /root/workspaces/etgah_ws/src/ai-worker-sim/ffw_description/urdf -type f | \
  xargs sed -i "s|${MESH_BASE}|package://ffw_description/meshes|g" 2>/dev/null || true
find /root/workspaces/etgah_ws/src/ai-worker-sim/ffw_description/urdf -type f | \
  xargs sed -i "s|file:///opt/ros/jazzy/share/realsense2_description/meshes|package://realsense2_description/meshes|g" 2>/dev/null || true

# Rebuild
colcon build --allow-overriding ffw_description
source install/setup.bash

# Fix install for GzWeb
MESH_BASE="file:///root/workspaces/etgah_ws/install/ffw_description/share/ffw_description/meshes"
find /root/workspaces/etgah_ws/install/ffw_description/share/ffw_description/urdf -type f | \
  xargs sed -i "s|package://ffw_description/meshes|${MESH_BASE}|g"
find /root/workspaces/etgah_ws/install/ffw_description/share/ffw_description/urdf -type f | \
  xargs sed -i "s|package://realsense2_description/meshes|file:///opt/ros/jazzy/share/realsense2_description/meshes|g"
```

---

## Known Issues

### Robot appears without body in GzWeb (only camera/lidar visible)

Step 5 was not run after the build. Re-run Step 5 after every `colcon build`.
