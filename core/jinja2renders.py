import re

from jinja2 import pass_context

from core.configs import logos_dir

# 匹配 ExifTool / 部分相机在无 GPS 时输出的 0 度 0 分占位
_ZERO_DMS = re.compile(r"0\s*deg\s*0\s*['\u2032]?\s*0(?:\.0+)?", re.I)


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


def gps_display(value):
    """水印用：无有效 GPS 时不显示（过滤 0°0′0″ 占位串），再应用 gps_safe。"""
    if not value:
        return ''
    s = gps_safe(str(value)).strip()
    if not s:
        return ''
    if len(_ZERO_DMS.findall(s)) >= 2:
        return ''
    if _ZERO_DMS.search(s) and re.search(
        r"0\s*deg\s*0\s*['\u2032]?\s*0(?:\.0+)?\s*['\u2032]?\s*[NSEW]\s*[,，]?\s*"
        r"0\s*deg\s*0",
        s,
        re.I,
    ):
        return ''
    return s
