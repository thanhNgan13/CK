#!/usr/bin/env python3

from pathlib import Path
import sys

try:
    from playsound3 import playsound
except ImportError:
    print('Chua cai dat playsound3. Hay chay: pip install playsound3')
    sys.exit(1)


def main():
    # Neu truyen duong dan file am thanh qua tham so:
    #   python play_sound.py /duong/dan/toi/file.mp3
    # thi dung file do.
    # Neu khong, mac dinh dung ./audio/sample.mp3
    if len(sys.argv) > 1:
        audio_path = Path(sys.argv[1])
    else:
        audio_path = Path(__file__).parent.parent / 'assets' / 'audios' / 'sample.mp3'

    if not audio_path.exists():
        print(f'Khong tim thay file am thanh: {audio_path}')
        print('Hay truyen duong dan file mp3 khi chay lenh, hoac tao file assets/audios/sample.mp3')
        sys.exit(1)

    print(f'Dang phat: {audio_path}')
    playsound(str(audio_path))


if __name__ == '__main__':
    main()
