"""render_sizes: the JPEG size set (THUMB_MAP) an uploaded image is stored as."""
import io

from PIL import Image

from app.helpers_image import THUMB_MAP, render_sizes


def _jpeg(size, orientation=None, mode='RGB'):
    img = Image.new(mode, size, 'white' if mode != 'RGBA' else (255, 255, 255, 0))
    exif = Image.Exif()
    if orientation:
        exif[0x0112] = orientation
    buf = io.BytesIO()
    img.convert('RGB').save(buf, 'JPEG', exif=exif.tobytes()) if mode == 'RGB' else img.save(buf, 'PNG')
    buf.seek(0)
    return buf


def _open(data):
    return Image.open(io.BytesIO(data))


def test_one_jpeg_per_size_within_its_box():
    sizes = render_sizes(_jpeg((5000, 2500)))
    assert [code for code, _ in sizes] == [code for code, _ in THUMB_MAP]
    for (code, data), (_, box) in zip(sizes, THUMB_MAP):
        img = _open(data)
        assert img.format == 'JPEG'
        assert img.width <= box[0] and img.height <= box[1], code
        assert img.width == box[0]  # landscape: fills the box width


def test_exif_orientation_is_applied():
    """a phone photo stored sideways (Orientation=6) comes out upright, with no
    orientation tag left to rotate it twice"""
    for _, data in render_sizes(_jpeg((400, 200), orientation=6)):
        img = _open(data)
        assert img.height == 2 * img.width  # portrait, as stored 400x200 landscape
        assert img.getexif().get(0x0112) in (None, 1)


def test_small_image_is_not_enlarged():
    for _, data in render_sizes(_jpeg((100, 80))):
        assert _open(data).size == (100, 80)


def test_png_with_alpha_becomes_rgb_jpeg():
    for _, data in render_sizes(_jpeg((300, 300), mode='RGBA')):
        img = _open(data)
        assert img.format == 'JPEG' and img.mode == 'RGB'
