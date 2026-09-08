#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from rclpy.qos import (
    QoSProfile,
    ReliabilityPolicy,
    DurabilityPolicy,
    HistoryPolicy,
    qos_profile_sensor_data,
)
from sensor_msgs.msg import CameraInfo

class CameraInfoFixNode(Node):

    def __init__(self) -> None:
        super().__init__('camera_info_fix_node')

        publisher_qos = QoSProfile(
            history=HistoryPolicy.KEEP_LAST,
            depth=10,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.VOLATILE,
        )

        self.publisher = self.create_publisher(
            CameraInfo,
            '/front_stereo_camera/left/camera_info_plumb_bob',
            publisher_qos,
        )

        self.subscription = self.create_subscription(
            CameraInfo,
            '/front_stereo_camera/left/camera_info',
            self.camera_info_callback,
            qos_profile_sensor_data,
        )

        self.warned = False

    def camera_info_callback(self, msg: CameraInfo) -> None:
        original_model = msg.distortion_model

        msg.distortion_model = 'plumb_bob'

        # Isaac Sim pinhole 카메라에 별도 렌즈 왜곡이 없는 경우
        if len(msg.d) == 0:
            msg.d = [0.0, 0.0, 0.0, 0.0, 0.0]

        self.publisher.publish(msg)

        if not self.warned:
            self.get_logger().info(
                f'CameraInfo distortion model converted: '
                f'{original_model!r} -> {msg.distortion_model!r}'
            )
            self.warned = True


def main(args=None) -> None:
    rclpy.init(args=args)
    node = CameraInfoFixNode()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
