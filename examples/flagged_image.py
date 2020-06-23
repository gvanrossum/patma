import array
from enum import IntFlag, auto
from dataclasses import dataclass
from random import randint

"""
The example creates two simple classes which might represent image data
in one dimensional arrays and flags associated with their data quality.

Each image type is then instantiated and a random instance is used in a
match statement representing possible code execution paths.
"""


class ImageFlags(IntFlag):
    """Flags that describe the quality of data
    """
    NO_FLAG = 0
    HAS_NAN = auto()
    SATURATED = auto()


@dataclass
class Image:
    """A basic 1D 'image' class with a field to flag the quality of the data
    """
    flags: ImageFlags
    data: array.array


@dataclass
class MaskedImage:
    """A 1D 'image' class with a flag associated with each pixel, referred to
    as a mask.

    There is a property named flags to describe the union of all flags in the
    mask.
    """
    __match_args__ = ("flags", "flags_mask", "data")
    flags_mask: array.array
    data: array.array

    @property
    def flags(self):
        flag_union = 0
        for value in self.flags_mask:
            flag_union |= value
        return ImageFlags(flag_union)


# Set some constants
data_len = 10
flag_len = len(ImageFlags)
bad_flags = (ImageFlags.HAS_NAN | ImageFlags.SATURATED)

# Create some data to put in an image
image_data = array.array('d', range(data_len))
# Create an Image with a random mask bit set
image = Image(ImageFlags(randint(0, flag_len)), image_data)

# Create a MaskedImage with random bits set in the mask
mask = array.array('i', (randint(0, flag_len) for _ in range(data_len)))
masked_image = MaskedImage(mask, image_data)

# Create a tuple of the image objects such that they can be randomly selected
image_instances = (image, masked_image)

# Match a randomly selected image to decide how it should be processed
match image_instances[randint(0, 1)]:
    case Image(flag, data) if flag & bad_flags:
        print("Is an Image")
        print(f"Call a function to handle flagged image data with flag {flag}")
    case MaskedImage(flag, mask, data) if flag & bad_flags:
        print("Is a MaskedImage")
        sub_data = [data[i] for i, v in enumerate(mask)
                    if v == ImageFlags.NO_FLAG]

        if sub_data:
            print(f"The good pixels are {sub_data}")
        else:
            print(f"There are no good pixels")
    case Image(flag, data) | MaskedImage(flag, _, data)\
            if flag is ImageFlags.NO_FLAG:
        print("Call a function for ok image data")
