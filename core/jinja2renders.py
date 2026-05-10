from jinja2 import pass_context

from core.configs import logos_dir


@pass_context
def vw(context, percent):
    exif = context.get('exif', {})
    return int(int(exif.get('ImageWidth', 0)) * percent / 100)


@pass_context
def vh(context, percent):
    exif = context.get('exif', {})
    return int(int(exif.get('ImageHeight', 0)) * percent / 100)


@pass_context
def auto_logo(context, brand: str = None):
    exif = context.get('exif', {})
    brand = (brand or exif.get('Make', 'default')).lower()


    for f in logos_dir.iterdir():
        if f.suffix.lower() in {'.png', '.jpg', '.jpeg'} and f.stem.lower() in brand:
            return str(f.absolute()).replace('\\', '/')
    return None


def gps_safe(value):
    """将 GPS DMS 格式中的双引号（秒标记 "）替换为单引号，避免 JSON 模板解析失败。
    例: 30 deg 35' 12.56" N  →  30 deg 35' 12.56' N
    """
    if not value:
        return ''
    return str(value).replace('"', "'")
