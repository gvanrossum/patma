import argparse
import os
import pathlib
import sys
import subprocess
import textwrap
from typing import Callable

"""
This is an example command line application that uses matching syntax to
call appropriate function to display various file types.

The command line syntax for this application is:
python file_opener.py </path/filename.extension>
"""


def display_video(file_path: str):
    """Displays a video file

    This function falls back to using system open calls in this example
    to avoid needing to install python packages to display movies. These
    may not be available for development versions of python
    """
    match sys.platform:
        case "win32":
            os.startfile(file_path)
        case "darwin":
            subprocess.call(["open", file_path])
        case _:
            subprocess.call(["xdg-open", file_path])



def display_image(file_path: str):
    try:
        from PIL import Image
    except ModuleNotFoundError:
        print("Displaying images requires Pillow/PIL to be installed")
        sys.exit(1)
    with Image.open(file_path) as im:
        im.show()


def display_txt(file_path: str):
    with open(file_path, 'r') as f:
        print(f.read())


def process_file(filename: str):
    file_path = pathlib.Path(filename).resolve()
    if not file_path.exists():
        print(f"{file_path} cannot be found on the filesystem")
        sys.exit(1)
    displayer: Callable
    match file_path.suffix:
        case '.mp4':
            displayer = display_video
        case '.jpg'|'.jpeg'|'.png':
            displayer = display_image
        case '.txt':
            displayer = display_txt
        case _:
            print(f"{file_path} is not a supported file type")
            sys.exit(1)
    displayer(str(file_path))


if __name__ == '__main__':
    description = textwrap.dedent("""This is a python application
    that shows the contents of a file. Supported file extensions are
    * mp4
    * jpg
    * jpeg
    * png
    * txt
    """)
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("filename", type=str, help="Path of file to open")
    args = parser.parse_args()
    process_file(args.filename)
