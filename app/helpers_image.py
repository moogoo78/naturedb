from pathlib import Path
from tempfile import NamedTemporaryFile
import io
import re

from PIL import Image
from PIL import (
    ExifTags,
    ImageOps,
    TiffImagePlugin,
    UnidentifiedImageError,
)
import boto3
from botocore.exceptions import ClientError
from boto3.exceptions import S3UploadFailedError

from werkzeug.utils import secure_filename
from flask import current_app

from app.utils import (
    gen_time_hash,
    decode_key
)

THUMB_MAP = (
    #('q', (75, 75)),
    ('s', (240, 240)),
    ('m', (500, 500)),
    #('l', (1280, 1280)),
    ('l', (1024, 1024)),
    ('x', (2048, 2048)),
    ('o', (4096, 4096)),
)


def render_sizes(source):
    '''[(size code, JPEG bytes)] for each THUMB_MAP box, from a file path or
    file object. The copies carry no EXIF, so the EXIF orientation is applied
    first: phone photos are stored sideways with an Orientation tag.'''
    sizes = []
    with Image.open(source) as img:
        img = ImageOps.exif_transpose(img)
        if img.mode != 'RGB':  # RGBA, P, CMYK, 16-bit TIFF
            img = img.convert('RGB')
        for code, box in THUMB_MAP:
            thumb = img.copy()
            thumb.thumbnail(box, Image.LANCZOS)
            buf = io.BytesIO()
            thumb.save(buf, 'JPEG', quality=85)
            sizes.append((code, buf.getvalue()))
    return sizes


def delete_image(upload_conf, service_keys, file_url):
    ret = {
        'message': 'ok',
        'error': '',
    }

    if upload_conf['storage'] == 'aws':
        s3_client = boto3.client(
            's3',
            aws_access_key_id=service_keys['accessKeyID'],
            aws_secret_access_key=service_keys['secretAccessKey'],
            region_name=upload_conf['region'],
        )

        file_prefix = f"https://{upload_conf['bucket']}.s3.{upload_conf['region']}.amazonaws.com/{upload_conf['prefix']}/"

        filename = file_url.replace(file_prefix, '')
        for thumb in THUMB_MAP:
            k = filename.replace('-m.jpg', f'-{thumb[0]}.jpg')
            object_key = f"{upload_conf['prefix']}/{k}"
            # print(object_key, flush=True)
            response = s3_client.delete_object(
                Bucket=upload_conf['bucket'],
                Key=object_key,
            )



def get_exif(pil_image):
    exif = {}
    tags = ExifTags.TAGS

    def sanity(text):
        '''via: chatgpt
        Remove \x00, \x01 and other similar control characters
        '''
        return re.sub(r'[\x00-\x1F]', '', text)

    def _parse_tags(raw_items):
        for k, v in raw_items:
            if k in tags:
                t = tags[k]
                if (t in ['MakerNote', 'PrintImageMatching']):
                    pass
                elif isinstance(v, int):
                    exif[t] = v
                elif isinstance(v, str):
                    exif[t] = sanity(v)
                elif isinstance(v, TiffImagePlugin.IFDRational):
                    exif[t] = sanity(str(v))
                elif isinstance(v, bytes):
                    try:
                        exif[t] = sanity(v.decode('ascii'))
                    except UnicodeDecodeError:
                        pass

    # Try JPEG EXIF first
    try:
        raw_exif = pil_image._getexif()
        if raw_exif:
            _parse_tags(raw_exif.items())
            return exif
    except (AttributeError, Exception):
        pass

    # Fallback: TIFF IFD tags (tag_v2 for TIFF/TIF files)
    if hasattr(pil_image, 'tag_v2') and pil_image.tag_v2:
        _parse_tags(pil_image.tag_v2.items())

    return exif


def upload_image(upload_conf, service_keys, file_, item_id):
    # default upload to cloud storage

    ret = {
        'message': 'ok',
        'error': '',
        'exif': {},
    }
    # save to uploads
    #filename = secure_filename(file_.filename)
    #f.save(Path(current_app.config['UPLOAD_FOLDER'], filename))
    ext = Path(file_.filename).suffix
    if ext.lower() not in ('.png', '.jpg', '.jpeg', '.tif', '.tiff'):
        ret.update({'message': 'failed', 'error': 'source image file format not support'})
        return ret

    with NamedTemporaryFile() as temp:
        temp.write(file_.read())
        temp.flush()

        if upload_conf['storage'] == 'aws':
            s3_client = boto3.client(
                's3',
                aws_access_key_id=service_keys['accessKeyID'],
                aws_secret_access_key=service_keys['secretAccessKey'],
                region_name=upload_conf['region'],
            )

        h = gen_time_hash()
        ret['file_url'] = f"https://{upload_conf['bucket']}.s3.{upload_conf['region']}.amazonaws.com/{upload_conf['prefix']}/{item_id}-{h}-m.jpg"

        with Image.open(temp.name) as img:
            if exif := get_exif(img):
                ret['exif'] = exif

        for code, data in render_sizes(temp.name):
            object_key = f'{item_id}-{h}-{code}.jpg'
            if pref := upload_conf['prefix']:
                object_key = f'{pref}/{object_key}'
            in_memory_file = io.BytesIO(data)

            if upload_conf['storage'] == 'aws':
                r = s3_client.upload_fileobj(
                    in_memory_file,
                    upload_conf['bucket'],
                    object_key,
                    ExtraArgs={'ACL': 'public-read'}
                )
                try:
                    current_app.logger.debug(f'upload to {object_key}')
                except:
                    print(f'upload to {object_key}')

            # except ClientError as e:
            #     #logging.error(e)
            #     #ret['error'] = 's3 upload client error'
            # except S3UploadFailedError as e:
            #     #print ('---------', e)
            #     ret['error'] = 's3 upload failed'
            # except Exception as e:
            #     ret['error'] = e
    return ret
