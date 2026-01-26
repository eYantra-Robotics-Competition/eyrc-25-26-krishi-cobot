#!/usr/bin/env python3
# -*- coding: utf-8 -*-
''' 
*****************************************************************************************
*  Filename:       task3.launch.py
*  Description:    Launch Ignition Gazebo Fortress world, eBot and UR5 arm
*  Modified by:    Joel Devasia, Sahil
*  Author:         e-Yantra Team
*****************************************************************************************
'''

import os
from os.path import join
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    IncludeLaunchDescription,
    AppendEnvironmentVariable,
    TimerAction,
)
from launch.substitutions import LaunchConfiguration, PythonExpression
from launch.launch_description_sources import PythonLaunchDescriptionSource
from ament_index_python.packages import get_package_share_directory
from launch_ros.actions import Node


def generate_launch_description():
    eyantra_warehouse = get_package_share_directory("eyantra_warehouse")
    gz_sim_share = get_package_share_directory("ros_gz_sim")
    ebot_description_pkg = get_package_share_directory("ebot_description")
    ur_simulation_gz_pkg = get_package_share_directory("ur_simulation_gz")

    world_file = LaunchConfiguration(
        "world_file", 
        default=join(eyantra_warehouse, "worlds", "eyantra_warehouse_task2.world")
    )

    gz_sim = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            join(gz_sim_share, "launch", "gz_sim.launch.py")
        ),
        launch_arguments={
            "gz_args": PythonExpression(["'", world_file, " -r'"])
        }.items(),
    )

    spawn_ebot = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            join(ebot_description_pkg, "launch", "spawn_ebot.launch.py")
        ),
    )

    spawn_arm = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            join(ur_simulation_gz_pkg, "launch", "spawn_arm.launch.py")
        ),
    )

    bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        name='ebot_bridge',
        parameters=[{
            'config_file': os.path.join(eyantra_warehouse, 'config', 'bridge.yaml'),
            'qos_overrides./tf_static.publisher.durability': 'transient_local',
            'use_sim_time': True
        }],
        output='screen'
    )

    armed0 = TimerAction(
        period=2.0,
        actions=[
            Node(
                package="eyantra_warehouse",
                executable="armed0.py",
                name="_armed0",
                output="screen",
                parameters=[{"use_sim_time": True}],
            )
        ]
    )

    return LaunchDescription([
        # Set resource paths for Gazebo
        AppendEnvironmentVariable(
            name="IGN_GAZEBO_RESOURCE_PATH",
            value=join(eyantra_warehouse, "worlds")
        ),
        AppendEnvironmentVariable(
            name="IGN_GAZEBO_RESOURCE_PATH",
            value=join(eyantra_warehouse, "models")
        ),
        # Declare launch arguments
        DeclareLaunchArgument("world_file", default_value=world_file),
        gz_sim,
        bridge,
        armed0,
        spawn_ebot,
        spawn_arm
    ])
