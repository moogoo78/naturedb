from pathlib import Path
from tempfile import NamedTemporaryFile
import io
import re

from PIL import Image
from PIL import (
    ExifTags,
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
    if not pil_image._getexif():
        return exif

    def sanity(text):
        '''via: chatgpt
        Remove \x00, \x01 and other similar control characters
        '''
        return re.sub(r'[\x00-\x1F]', '', text)

    for k, v in pil_image._getexif().items():
        if k in tags:
            t = tags[k]
            #print(t, v, type(v), flush=True)
            if (t in ['MakerNote', 'PrintImageMatching']):
                # massy binary
                pass
            elif isinstance(v, int):
                exif[t] = v
            elif isinstance(v, str):
                exif[t] = sanity(v)
            elif isinstance(v, TiffImagePlugin.IFDRational):
                #print ('---------', v.denominator, v.numerator)
                exif[t] = sanity(str(v))
            elif isinstance(v, bytes):
                exif[t] = sanity(v.decode('ascii'))

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
    if ext.lower() not in ('.png', '.jpg', '.jpeg'):
        ret.update({'message': 'failed', 'error': 'source image file format not support'})
        return ret

    with NamedTemporaryFile() as temp:
        temp.write(file_.read())

        if upload_conf['storage'] == 'aws':
            s3_client = boto3.client(
                's3',
                aws_access_key_id=service_keys['accessKeyID'],
                aws_secret_access_key=service_keys['secretAccessKey'],
                region_name=upload_conf['region'],
            )

        h = gen_time_hash()
        ret['file_url'] = f"https://{upload_conf['bucket']}.s3.{upload_conf['region']}.amazonaws.com/{upload_conf['prefix']}/{item_id}-{h}-m.jpg"

        one_exif = {}
        # make thumb
        for thumb in THUMB_MAP:
            #stem = Path(filename).stem
            #target_path = thumb_source_path.joinpath(Path(target_filename))
            #print (source_path, target_path)
            #target_path = Path(current_app.config['UPLOAD_FOLDER'], target_filename)
            #file.save(Path(current_app.config['UPLOAD_FOLDER'], filename))
            object_key = f'{item_id}-{h}-{thumb[0]}.jpg'
            if pref := upload_conf['prefix']:
                object_key = f'{pref}/{object_key}'

            img = Image.open(temp.name)
            if len(one_exif) == 0:
                exif = get_exif(img)
                if len(exif):
                    ret['exif'] = exif

            img.thumbnail(thumb[1] , Image.LANCZOS)
            if img.mode != 'RGB': # RGBA?
                img = img.convert('RGB')
            in_memory_file = io.BytesIO()
            img.save(in_memory_file, 'JPEG')
            in_memory_file.seek(0)

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
