from __future__ import unicode_literals, division

import math
from sorl.thumbnail.engines.base import EngineBase
from sorl.thumbnail.compat import BufferIO

# try to spot two common install problems

try:
    from gi.repository import Vips
except Exception, e:
    raise Exception("typelib for libvips not found --- make sure Vips-x.y.typelib is on your GI_TYPELIB_PATH " + str(e))

try:
    x = Vips.Image.new_from_array([1,2,3])
except Exception:
    raise Exception("overrides for libvips not found --- make sure Vips.py is copied to your gi/overrides area")

class Engine(EngineBase):
    def get_image(self, source):
        # we need to keep the string around until we've finished with the 
        # image ... vips does not take a copy of the data, it will keep pointers
        # into this string as long as the image is active
        self.image_data = source.read()
        return Vips.Image.new_from_buffer(self.image_data)

    def get_image_size(self, image):
        return (image.width, image.height)

    def get_image_info(self, image):
        # vips has image.summary() (a one-line summary of the object) and 
        # image.dump() (everything known about the object), but they are not
        # exposed to Python ... fix this
        return ""

    def is_valid_image(self, raw_data):
        try:
            image = Vips.Image.new_from_buffer(raw_data)
        except Exception:
            return False
        return True

    def _cropbox(self, image, x, y, x2, y2):
        return image.crop(x, y, x2 - x, y2 - y)

    def _orientation(self, image):
        return image.autorot()

    def _colorspace(self, image, colorspace):
        if colorspace == 'RGB':
            return image.colourspace(Vips.Interpretation.sRGB)
        if colorspace == 'GRAY':
            return image.colourspace(Vips.Interpretation.B_W)

        return image

    def _scale(self, image, width, height):
        # libvips resize can look a little soft, perhaps add a sharpening stage
        # here
        hscale = width / image.width
        vscale = height / image.height
        scale = max(hscale, vscale)
        return image.resize(scale)

    def _crop(self, image, width, height, x_offset, y_offset):
        return image.crop(x_offset, y_offset, width, height)

    def _blur(self, image, radius):
        # the parameter to gaussblur is actually sigma
        return image.gaussblur(radius)

    def _padding(self, image, geometry, options):
        x_image, y_image = self.get_image_size(image)
        left = int((geometry[0] - x_image) / 2)
        top = int((geometry[1] - y_image) / 2)
        color = options.get('padding_color')

        return image.embed(left, top, geometry[0], geometry[1],
                           extend = "background", background = color)

    def _get_raw_data(self, image, format_, quality, image_info=None, progressive=False):
        if format_ == "JPEG":
            format_string = ".jpg"
        elif format_ == "PNG":
            format_string = ".png"
        else:
            # vips supports other formats, but I don't know what strings 
            # sorl can pass down ... add more to this list as we discover them
            raise Exception("unrecognised sorl format_ " + format_)

        format_options = []
        if quality != None:
            format_options.append("Q=%d" % quality)
        if progressive:
            format_options.append("interlace=True")
        # remove all metadata, like exif, ipct, xmp etc
        format_options.append("strip=True")
        format_string += "[%s]" % join(",").format_options

        # not sure what to do about this:
        # if 'icc_profile' in image_info:
        #    params['icc_profile'] = image_info['icc_profile']
        # we should probably transform to sRGB before this point and not attach
        # a profile at all

        return image.write_to_buffer(format_string)
