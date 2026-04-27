#!/usr/bin/env python3
import os
from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, IncludeLaunchDescription
from launch.actions import RegisterEventHandler, SetEnvironmentVariable
from launch.event_handlers import OnProcessExit
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, FindExecutable, LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    declared_arguments = [
        DeclareLaunchArgument('model', default_value='ffw_sg2_rev1_follower',
                              description='Robot model name.'),
        DeclareLaunchArgument('world', default_value='default',
                              description='Gz sim World'),
    ]

    model = LaunchConfiguration('model')
    world = LaunchConfiguration('world')

    ffw_description_path = os.path.join(
        get_package_share_directory('ffw_description'))

    ffw_bringup_path = os.path.join(
        get_package_share_directory('ffw_bringup'))

    gazebo_resource_path = SetEnvironmentVariable(
    name='GZ_SIM_RESOURCE_PATH',
    value=[
        os.path.join(ffw_bringup_path, 'worlds'), ':' +
        str(Path(ffw_description_path).parent.resolve()), ':' +
        # Add realsense2_description path
        str(Path(get_package_share_directory('realsense2_description')).parent.resolve())
    ]
)
    kill_old_bridges = ExecuteProcess(
            cmd=['bash', '-c', 'pkill -f parameter_bridge || true; sleep 1'],
            output='screen'
        )

    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([os.path.join(
            get_package_share_directory('ros_gz_sim'), 'launch'), '/gz_sim.launch.py']),
        launch_arguments=[
            ('gz_args', [world, '.sdf', ' -v 1', ' -r', ' -s'])
        ]
    )

    robot_description_content = Command([
        PathJoinSubstitution([FindExecutable(name='xacro')]),
        ' ',
        PathJoinSubstitution([FindPackageShare('ffw_description'),
                              'urdf', model, 'ffw_sg2_follower.urdf.xacro']),
        ' ', 'model:=', model, ' ', 'use_sim:=true',
    ])

    robot_description = {'robot_description': robot_description_content}

    robot_state_pub_node = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        parameters=[robot_description, {'use_sim_time': True}],
        output='screen'
    )

    gz_spawn_entity = Node(
        package='ros_gz_sim',
        executable='create',
        output='screen',
        arguments=[
            '-topic', 'robot_description',
            '-x', '0.0', '-y', '0.0', '-z', '0.2',
            '-R', '0.0', '-P', '0.0', '-Y', '0.0',
            '-name', model,
            '-allow_renaming', 'true',
            '-use_sim', 'true',
        ],
    )

    # Step 1: joint_state_broadcaster
    joint_state_broadcaster_spawner = Node(
        package='controller_manager',
        executable='spawner',
        arguments=['joint_state_broadcaster'],
        output='screen'
    )

    # Step 2: arm/head/lift controllers
    arm_controller_spawner = Node(
        package='controller_manager',
        executable='spawner',
        arguments=[
            '--controller-ros-args',
            '-r /arm_l_controller/joint_trajectory:='
            '/leader/joint_trajectory_command_broadcaster_left/joint_trajectory',
            '--controller-ros-args',
            '-r /arm_r_controller/joint_trajectory:='
            '/leader/joint_trajectory_command_broadcaster_right/joint_trajectory',
            '--controller-ros-args',
            '-r /head_controller/joint_trajectory:='
            '/leader/joystick_controller_left/joint_trajectory',
            '--controller-ros-args',
            '-r /lift_controller/joint_trajectory:='
            '/leader/joystick_controller_right/joint_trajectory',
            'arm_l_controller',
            'arm_r_controller',
            'head_controller',
            'lift_controller',
        ],
        parameters=[robot_description],
        output='screen',
    )

    # Step 3: zero the steering joints
    steering_init_spawner = Node(
        package='controller_manager',
        executable='spawner',
        arguments=['swerve_steering_initial_position_controller'],
        output='screen'
    )

    # Step 4: load swerve INACTIVE (must happen after steering init exits
    #         so the steering joints are free to be claimed)
    swerve_load_inactive = Node(
        package='controller_manager',
        executable='spawner',
        arguments=[
            '--inactive',
            'swerve_drive_controller',
        ],
        parameters=[robot_description],
        output='screen'
    )

    # Step 5: atomically deactivate steering init, activate swerve
    switch_to_swerve = ExecuteProcess(
        cmd=[
            'ros2', 'control', 'switch_controllers',
            '--deactivate', 'swerve_steering_initial_position_controller',
            '--activate', 'swerve_drive_controller',
            '--strict',
        ],
        output='screen'
    )

    gz_bridge_params_path = os.path.join(
        ffw_bringup_path, 'config', 'common', 'gz_bridge.yaml'
    )

    bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        arguments=['--ros-args', '-p', f'config_file:={gz_bridge_params_path}'],
        parameters=[{'use_sim_time': True}],
        output='screen'
    )

    rviz_config_file = os.path.join(ffw_description_path, 'rviz', 'ffw_sg2.rviz')

    rviz = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        output='log',
        arguments=['-d', rviz_config_file],
        parameters=[{'use_sim_time': True}],
    )

    dual_laser_merger_node = Node(
        package='dual_laser_merger',
        executable='dual_laser_merger_node',
        output='screen',
        parameters=[{
            'laser_1_topic': '/scan_left',
            'laser_2_topic': '/scan_right',
            'merged_scan_topic': '/scan',
            'target_frame': 'base_link',
            'angle_min': -3.141592654,
            'angle_max': 3.141592654,
            'angle_increment': 0.006544985,
            'scan_time': 0.1,
            'range_min': 0.05,
            'range_max': 20.0,
            'use_inf': True,
            'tolerance': 0.05,
            'queue_size': 10,
            'enable_shadow_filter': True,
            'enable_average_filter': True,
        }, {
            'use_sim_time': True,
        }],
    )

    return LaunchDescription([
        *declared_arguments,

        # robot spawned -> joint_state_broadcaster
        RegisterEventHandler(
            event_handler=OnProcessExit(
                target_action=gz_spawn_entity,
                on_exit=[joint_state_broadcaster_spawner],
            )
        ),

        # joint_state_broadcaster done -> arms + steering init (parallel)
        RegisterEventHandler(
            event_handler=OnProcessExit(
                target_action=joint_state_broadcaster_spawner,
                on_exit=[arm_controller_spawner, steering_init_spawner],
            )
        ),

        # steering init done -> load swerve inactive
        # (steering joints now free since init controller holds them
        #  until we explicitly switch)
        RegisterEventHandler(
            event_handler=OnProcessExit(
                target_action=steering_init_spawner,
                on_exit=[swerve_load_inactive],
            )
        ),

        # swerve loaded inactive -> atomic switch
        RegisterEventHandler(
            event_handler=OnProcessExit(
                target_action=swerve_load_inactive,
                on_exit=[switch_to_swerve],
            )
        ),

        kill_old_bridges,
        bridge,
        gazebo_resource_path,
        gazebo,
        robot_state_pub_node,
        gz_spawn_entity,
        rviz,
        dual_laser_merger_node,
    ])

# world: default.sdf
# world: empty_world.sdf