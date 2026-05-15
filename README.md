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

## Step 3 - Build the Workspace

```bash
source /opt/ros/jazzy/setup.bash
colcon build --allow-overriding ffw_description
source install/setup.bash
```

---

## Step 4 - Fix Mesh Files for GzWeb

> **Run this after every `colcon build`.**

**Why this is needed:**

1. **Symlinks:** GzWeb's websocket server reads mesh files directly from disk. When mesh files are symlinks (which colcon creates by default), GzWeb cannot read them. This step copies the real files over the symlinks.

2. **package:// URIs:** GzWeb cannot resolve `package://ffw_description/...` URIs. The URDF files in the install folder must be patched to use absolute `file://` paths.

RViz and native Gazebo are not affected since they resolve `package://` URIs normally.

```bash
# Run from workspace root
cd /root/workspaces/turtlebot3_ws

# 1. Break mesh symlinks (copy real files over symlinks)
find /root/workspaces/turtlebot3_ws/install/ffw_description/share/ffw_description/meshes \
  -type l | while read f; do
    REAL=$(readlink -f "$f")
    rm "$f"
    cp "$REAL" "$f"
done

# 2. Convert package:// to file:// in install URDF files (GzWeb fix)
INSTALL_MESH_DIR="/root/workspaces/turtlebot3_ws/install/ffw_description/share/ffw_description/meshes"
find /root/workspaces/turtlebot3_ws/install/ffw_description \
    \( -name "*.xacro" -o -name "*.urdf" \) | \
    xargs sed -i "s|package://ffw_description/meshes|file://${INSTALL_MESH_DIR}|g"
```

### Verify Step 4 Worked

```bash
# Should print 0 (no symlinks remaining)
find /root/workspaces/turtlebot3_ws/install/ffw_description/share/ffw_description/meshes -type l | wc -l

# Should print file:// paths (not package://)
xacro /root/workspaces/turtlebot3_ws/install/ffw_description/share/ffw_description/urdf/ffw_sh5_rev1_follower/ffw_sh5_follower.urdf.xacro \
  model:=ffw_sh5_rev1_follower use_sim:=true 2>&1 | grep "mesh filename" | head -3
```

Expected output for the second command:

```
<mesh filename="file:///root/workspaces/turtlebot3_ws/install/ffw_description/share/ffw_description/meshes/common/follower/swerve/base_mobile_assy.stl" ... />
```

---

## Step 5 - Launch the Simulation

For the sh5 robot:

```bash
ros2 launch ffw_bringup ffw_sh5_follower_ai_gazebo.launch.py
```

---

## Re-building After Changes

Run Steps 3 and 4 after every code change:

```bash
cd /root/workspaces/turtlebot3_ws
colcon build --allow-overriding ffw_description
source install/setup.bash

# Step 4: symlinks + package:// patch (run as a single block)
find /root/workspaces/turtlebot3_ws/install/ffw_description/share/ffw_description/meshes \
  -type l | while read f; do
    REAL=$(readlink -f "$f")
    rm "$f"
    cp "$REAL" "$f"
done

INSTALL_MESH_DIR="/root/workspaces/turtlebot3_ws/install/ffw_description/share/ffw_description/meshes"
find /root/workspaces/turtlebot3_ws/install/ffw_description \
    \( -name "*.xacro" -o -name "*.urdf" \) | \
    xargs sed -i "s|package://ffw_description/meshes|file://${INSTALL_MESH_DIR}|g"
```

---

## Known Issues

### Robot appears without body in GzWeb (only camera/lidar visible)

Step 4 was not run after the build, OR the `package://` to `file://` patch was missed. Re-run Step 4 in full after every `colcon build`.



Click **Refresh Launch Files** in the web panel after building if files still do not appear.

### GzWeb connection times out when cameras are active

Camera sensors at high resolution (1280x720 at 30fps) flood the Gazebo transport layer. Reduce camera update rates in the `.gazebo.xacro` file if this occurs.

### TF errors for movable joints in RViz

This means `joint_state_broadcaster` is not active. Kill stale processes and relaunch:

```bash
pkill -f "gz sim"; pkill -f "controller_manager"; sleep 3
ros2 launch ffw_bringup ffw_sh5_follower_ai_gazebo.launch.py
```
