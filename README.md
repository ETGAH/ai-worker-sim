# FFW Robot Stack — ai-worker-sim

---

## Step 1 — Clone the Repository

```bash
git clone https://github.com/ETGAH/ai-worker-sim.git
cd ai-worker-sim
```

---

## Step 2 — Install Dependencies (Binary Only)

```bash
sudo apt update
sudo apt install ros-jazzy-gz-ros2-control
sudo apt install ros-jazzy-moveit
sudo apt install ros-jazzy-realsense2-description
sudo apt install ros-jazzy-dual-laser-merger
```

---

## Step 3 — Build the Workspace

```bash
source /opt/ros/jazzy/setup.bash
colcon build --allow-overriding ffw_description
source install/setup.bash
```

---

## Step 4 — Fix Mesh Files for GzWeb

> **Run this after every `colcon build`.**

**Why this is needed:**
GzWeb's websocket server reads mesh files directly from disk. When mesh files are symlinks (which colcon creates by default), GzWeb cannot read them and the robot body does not appear. This step copies the real files over the symlinks. RViz and Gazebo are not affected since they resolve `package://` URIs normally.

```bash
find /root/workspaces/etgah_ws/install/ffw_description/share/ffw_description/meshes \
  -type l | while read f; do
    REAL=$(readlink -f "$f")
    rm "$f"
    cp "$REAL" "$f"
done
```

Verify (should print 0):

```bash
find /root/workspaces/etgah_ws/install/ffw_description/share/ffw_description/meshes -type l | wc -l
```

---

## Step 5 — Launch the Simulation

For the sh5 robot:

```bash
ros2 launch ffw_bringup ffw_sh5_follower_ai_gazebo.launch.py
```

For the sg2 robot:

```bash
ros2 launch ffw_bringup ffw_sg2_follower_ai_gazebo.launch.py
```

For the bg2 robot:

```bash
ros2 launch ffw_bringup ffw_bg2_follower_ai_gazebo.launch.py
```

---

## Re-building After Changes

Run Steps 3 and 4 after every code change:

```bash
colcon build --allow-overriding ffw_description
source install/setup.bash

find /root/workspaces/etgah_ws/install/ffw_description/share/ffw_description/meshes \
  -type l | while read f; do
    REAL=$(readlink -f "$f")
    rm "$f"
    cp "$REAL" "$f"
done
```

---

## Known Issues

### Robot appears without body in GzWeb (only camera/lidar visible)

Step 4 was not run after the build. Re-run Step 4 after every `colcon build`.

### Web panel shows "No launch files found"

The platform web panel filters launch files by checking for a literal world filename. Each launch file already contains these comments at the bottom as a workaround:

```python
# world: default.sdf
# world: empty_world.sdf
```

Click **Refresh Launch Files** in the web panel after building if files still do not appear.

### GzWeb connection times out when cameras are active

Camera sensors at high resolution (1280x720 at 30fps) flood the Gazebo transport layer. Reduce camera update rates in the `.gazebo.xacro` file if this occurs.

### TF errors for movable joints in RViz

This means `joint_state_broadcaster` is not active. Kill stale processes and relaunch:

```bash
pkill -f "gz sim"; pkill -f "controller_manager"; sleep 3
ros2 launch ffw_bringup ffw_sh5_follower_ai_gazebo.launch.py
```
