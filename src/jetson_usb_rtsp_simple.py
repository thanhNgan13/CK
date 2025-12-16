#!/usr/bin/env python3
import os
import sys

import gi
gi.require_version('Gst', '1.0')
gi.require_version('GstRtspServer', '1.0')

from gi.repository import Gst, GstRtspServer, GObject

# ================== CẤU HÌNH ==================
CAM_DEV = os.environ.get('CAM_DEV', '/dev/video0')
WIDTH = int(os.environ.get('WIDTH', '1920'))
HEIGHT = int(os.environ.get('HEIGHT', '1080'))
FPS = int(os.environ.get('FPS', '30'))          # phải khớp 30/1
BITRATE = int(os.environ.get('BITRATE', '4000'))  # kbps
PORT = os.environ.get('PORT', '8554')
MOUNT_POINT = os.environ.get('MOUNT_POINT', '/cam')
# ==============================================


def main():
    Gst.init(None)

    server = GstRtspServer.RTSPServer()
    server.props.service = PORT

    factory = GstRtspServer.RTSPMediaFactory()

    # MJPEG -> jpegdec -> raw -> x264enc -> RTP
    pipeline_str = (
        f'( v4l2src device={CAM_DEV} ! '
        f'image/jpeg,width={WIDTH},height={HEIGHT},framerate={FPS}/1 ! '
        'jpegdec ! '
        'videoconvert ! '
        'video/x-raw,format=I420 ! '
        f'x264enc tune=zerolatency speed-preset=ultrafast bitrate={BITRATE} key-int-max={FPS} ! '
        'rtph264pay name=pay0 pt=96 config-interval=1 )'
    )

    print(f'[GST] launch: {pipeline_str}')
    factory.set_launch(pipeline_str)
    factory.set_shared(True)

    mounts = server.get_mount_points()
    mounts.add_factory(MOUNT_POINT, factory)

    server.attach(None)

    rtsp_url = f'rtsp://<IP_JETSON>:{PORT}{MOUNT_POINT}'
    print('==============================================')
    print('   JETSON USB CAMERA RTSP SERVER (MJPEG->H264)')
    print('==============================================')
    print(f'- Device  : {CAM_DEV}')
    print(f'- Size    : {WIDTH}x{HEIGHT}')
    print(f'- FPS     : {FPS}')
    print(f'- Bitrate : {BITRATE} kbps')
    print(f'- RTSP URL: {rtsp_url}')
    print('==============================================')
    print('Nhấn Ctrl+C để dừng.')

    loop = GObject.MainLoop()
    try:
        loop.run()
    except KeyboardInterrupt:
        print('\n[INFO] Dừng RTSP server...')
        loop.quit()
        sys.exit(0)


if __name__ == '__main__':
    main()

