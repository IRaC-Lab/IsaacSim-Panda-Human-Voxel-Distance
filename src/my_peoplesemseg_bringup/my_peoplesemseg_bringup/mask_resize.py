#!/usr/bin/env python3

import cv2
import numpy as np
import rclpy

from rclpy.node import Node
from rclpy.qos import (
    DurabilityPolicy,
    HistoryPolicy,
    QoSProfile,
    ReliabilityPolicy,
)
from sensor_msgs.msg import Image
from rclpy.executors import ExternalShutdownException


class MaskResizeNode(Node):

    def __init__(self) -> None:
        super().__init__('mask_resize_node')

        qos = QoSProfile(
            history=HistoryPolicy.KEEP_LAST,
            depth=10,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.VOLATILE,
        )

        self.publisher = self.create_publisher(
            Image,
            '/unet/raw_segmentation_mask_640x480',
            qos,
        )

        self.subscription = self.create_subscription(
            Image,
            '/unet/raw_segmentation_mask',
            self.callback,
            qos,
        )

        self.target_width = 640
        self.target_height = 480
        self.first_frame = True

    def callback(self, msg: Image) -> None:
        if msg.encoding not in ('mono8', '8UC1'):
            self.get_logger().error(
                f'Unsupported mask encoding: {msg.encoding}'
            )
            return

        mask = np.frombuffer(
            msg.data,
            dtype=np.uint8,
        ).reshape(msg.height, msg.width)

        
        # 640x480 -> 960x544 변환 시
        # keep_aspect_ratio=true, disable_padding=false이므로
        # 좌우 padding이 추가됨
        content_width = 726
        pad_left = (msg.width - content_width) // 2  # 117

        unpadded_mask = mask[
            :,
            pad_left:pad_left + content_width,
        ]

        resized = cv2.resize(
            unpadded_mask,
            (self.target_width, self.target_height),
            interpolation=cv2.INTER_NEAREST,
        )
        
        output = Image()
        output.header = msg.header
        output.height = self.target_height
        output.width = self.target_width
        output.encoding = 'mono8'
        output.is_bigendian = False
        output.step = self.target_width
        output.data = resized.tobytes()

        self.publisher.publish(output)

        if self.first_frame:
            self.get_logger().info(
                f'Mask resized: {msg.width}x{msg.height} '
                f'-> {output.width}x{output.height}'
            )
            self.first_frame = False


def main(args=None) -> None:
    rclpy.init(args=args)
    node = MaskResizeNode()

    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()

        if rclpy.ok():
            rclpy.shutdown()
            

if __name__ == '__main__':
    main()
