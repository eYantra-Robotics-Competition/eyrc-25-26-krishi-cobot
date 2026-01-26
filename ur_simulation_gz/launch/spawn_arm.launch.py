#!/usr/bin/env python3

"""
UR5 launch file for eyantra warehouse world with sequential loading
"""

import os
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    IncludeLaunchDescription,
    SetEnvironmentVariable,
    AppendEnvironmentVariable,
    TimerAction,
)
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import (
    Command,
    FindExecutable,
    LaunchConfiguration,
    PathJoinSubstitution,
)
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
from ament_index_python.packages import get_package_share_directory


def generate_launch_description():
    # Arguments
    declared_arguments = []
    declared_arguments.append(
        DeclareLaunchArgument(
            "ur_type",
            default_value="ur5",
            description="Type of UR robot",
        )
    )

    # Get configurations
    ur_type = LaunchConfiguration("ur_type")

    # Package paths
    ur_description_package = FindPackageShare("ur_description")
    ur_simulation_gz_package = FindPackageShare("ur_simulation_gz")

    # Robot description with UR5 prefix
    robot_description_content = Command([
        PathJoinSubstitution([FindExecutable(name="xacro")]),
        " ",
        PathJoinSubstitution([ur_description_package, "urdf", "ur.urdf.xacro"]),
        " ",
        "name:=ur5",
        " ",
        "ur_type:=", ur_type,
        " ",
        # "prefix:=ur5_",  # Add prefix for TF frames
        " ",
        "sim_ignition:=true",
        " ",
        "use_fake_hardware:=true",
        " ",
        "fake_sensor_commands:=false",
        " ",
        "initial_positions_file:=", PathJoinSubstitution([ur_description_package, "config", "initial_positions.yaml"]),
        " ",
        "simulation_controllers:=", PathJoinSubstitution([ur_simulation_gz_package, "config", "ur_controllers.yaml"]),
    ])

    robot_description = {"robot_description": robot_description_content}

    # Step 2: Robot state publisher with ur5 namespace (3s - wait for world to load)
    robot_state_publisher_node = TimerAction(
        period=3.0,
        actions=[
            Node(
                package="robot_state_publisher",
                executable="robot_state_publisher",
                name="robot_state_publisher",
                # namespace="ur5",  # Add namespace
                output="both",
                parameters=[
                    robot_description,
                    {
                        "use_sim_time": True,
                        # "frame_prefix": "ur5_"  # Add frame prefix
                    }
                ],
            )
        ]
    )

    # Step 3: Bridge for essential topics (4s - after robot state publisher)
    bridge = TimerAction(
        period=5.0,
        actions=[
            Node(
                package="ros_gz_bridge",
                executable="parameter_bridge",
                name="ur5_gz_bridge",
                # namespace="ur5",  # Add namespace for bridge
                arguments=[
                    # "/clock@rosgraph_msgs/msg/Clock[ignition.msgs.Clock",
                    "/camera/image@sensor_msgs/msg/Image@ignition.msgs.Image",
                    "/camera/depth_image@sensor_msgs/msg/Image@ignition.msgs.Image",
                    "/camera/camera_info@sensor_msgs/msg/CameraInfo@ignition.msgs.CameraInfo",
                    "/camera/points@sensor_msgs/msg/PointCloud2@ignition.msgs.PointCloudPacked",
                    "/force_torque@geometry_msgs/msg/WrenchStamped@ignition.msgs.Wrench",
                ],
                remappings=[
                    ("/camera/image", "/camera/image_raw"),
                    ("/camera/depth_image", "/camera/depth/image_raw"),
                    ("/camera/camera_info", "/camera/camera_info"),
                    ("/camera/points", "/camera/depth/points"),
                    ("/force_torque", "/force_torque_sensor/wrench"),
                ],
                output="screen",
                parameters=[{"use_sim_time": True}],
            )
        ]
    )

    # Step 4: Spawn robot (5s - after bridge is ready)
    spawn_robot_delayed = TimerAction(
        period=6.0,
        actions=[
            Node(
                package="ros_gz_sim",
                executable="create",
                name="spawn_ur5",
                output="screen",
                arguments=[
                    "-name", "ur5",
                    "-topic", "robot_description",  # Use namespaced topic
                    "-x", "1.18",
                    "-y", "-1.96",
                    "-z", "0.59",
                    "-R", "0.0",
                    "-P", "0.0",
                    "-Y", "3.14",
                ],
                parameters=[{"use_sim_time": True}],
            )
        ]
    )

    # Step 5: Load joint state broadcaster with namespace (8s)
    joint_state_broadcaster_spawner = TimerAction(
        period=8.0,
        actions=[
            Node(
                package="controller_manager",
                executable="spawner",
                arguments=[
                    "joint_state_broadcaster", 
                    "--controller-manager", "/controller_manager"  # Namespaced controller manager
                ],
                parameters=[{"use_sim_time": True}],
                output="screen",
            )
        ]
    )

    # Step 6: Load forward velocity controller with namespace (10s)
    forward_velocity_controller_spawner = TimerAction(
        period=12.0,
        actions=[
            Node(
                package="controller_manager",
                executable="spawner",
                arguments=[
                    "forward_velocity_controller", 
                    "--controller-manager", "/controller_manager"  # Namespaced controller manager
                ],
                parameters=[{"use_sim_time": True}],
                output="screen",
            )
        ]
    )

    # Step 7: Camera info relay with namespace (11s)
    camera_info_relay = TimerAction(
        period=15.0,
        actions=[
            Node(
                package='topic_tools',
                executable='relay',
                name='camera_info_relay',
                # namespace='ur5',
                arguments=['/camera/camera_info', '/camera/depth/camera_info'],
                output='screen',
                parameters=[{"use_sim_time": True}],
            )
        ]
    )

    # Step 8: Cartesian servo node with namespace (12s)
    twist_servo_node = TimerAction(
        period=17.0,
        actions=[
            Node(
                package='ur_simulation_gz',
                executable='twist_servo_cal.py',
                name='cartesian_servo_node',
                # namespace='ur5',
                output='screen',
                parameters=[{"use_sim_time": True}],
            )
        ]
    )
    random_fruits_spawner = TimerAction(
        period=20.0,
        actions=[
            Node(
                package="ur_description",
                executable="random_fruits_spawner.py",
                name="random_fruits_spawner",
                output="screen",
                parameters=[{"use_sim_time": True}],
            )
        ]
    )

    return LaunchDescription(
        declared_arguments + [
            robot_state_publisher_node,      # 3s - Robot description
            bridge,                          # 4s - Communication bridge
            spawn_robot_delayed,             # 5s - Spawn robot
            joint_state_broadcaster_spawner, # 8s - Basic controller
            forward_velocity_controller_spawner, # 10s - Motion controller
            camera_info_relay,               # 11s - Camera setup
            twist_servo_node,                # 12s - Advanced control
            random_fruits_spawner,          # 20s - Spawn random fruits
        ]
    )