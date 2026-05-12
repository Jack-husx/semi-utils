import io
import json
import os
import platform
import re
import shutil
import subprocess
import time
from functools import wraps
from pathlib import Path

from PIL import Image, ExifTags
from jinja2 import Template

from core.configs import templates_dir
from core.jinja2renders import vh, vw, auto_logo, gps_safe, gps_display
from core.logger import logger

if platform.system() == 'Windows':
    import ctypes
    EXIFTOOL_PATH = Path('./exiftool/exiftool.exe')
    ENCODING = 'gbk'
    _CREATE_NO_WINDOW = 0x08000000
    # 在进程启动时就抑制 Windows Error Reporting 对话框（系统级）
    # SEM_FAILCRITICALERRORS | SEM_NOGPFAULTERRORBOX | SEM_NOOPENFILEERRORBOX
    _WER_SUPPRESS_FLAGS = 0x0001 | 0x0002 | 0x8000
    ctypes.windll.kernel32.SetErrorMode(_WER_SUPPRESS_FLAGS)
else:
    EXIFTOOL_PATH = shutil.which('exiftool') or Path('./exiftool/exiftool')
    ENCODING = 'utf-8'
    _CREATE_NO_WINDOW = 0


# ── Pillow 降级：将 GPS IFD 转成度分秒字符串 ──────────────────
def _dms_to_str(dms, ref) -> str:
    """把 Pillow 返回的 ((d,1),(m,1),(s,100)) 格式转成可读字符串"""
    try:
        def to_float(v):
            return v.numerator / v.denominator if hasattr(v, 'numerator') else float(v[0]) / float(v[1])
        d = to_float(dms[0])
        m = to_float(dms[1])
        s = to_float(dms[2])
        return f"{int(d)} deg {int(m)}' {s:.2f}' {ref}"
    except Exception:
        return ''


def _gps_rational_all_zero(dms) -> bool:
    """GPS DMS 三元组是否全为 0（无定位信息）。"""
    try:
        def tf(v):
            return v.numerator / v.denominator if hasattr(v, 'numerator') else float(v[0]) / float(v[1])
        return abs(tf(dms[0])) + abs(tf(dms[1])) + abs(tf(dms[2])) < 1e-9
    except Exception:
        return False


def _get_exif_from_pillow(path) -> dict:
    """用 Pillow 读取 EXIF，作为 ExifTool 不可用时的降级方案。
    覆盖水印模板实际用到的字段：
    GPSLatitude, GPSLongitude, GPSPosition,
    DateTimeOriginal, Make, Model, LensModel,
    ExposureTime, FNumber, ISO。
    """
    result = {}
    try:
        with Image.open(path) as img:
            raw = img._getexif()
        if not raw:
            return result

        # 把 tag id 转成名字
        by_name = {}
        for tag_id, val in raw.items():
            name = ExifTags.TAGS.get(tag_id, str(tag_id))
            by_name[name] = val

        # ── 拍摄时间 ──
        for dt_key in ('DateTimeOriginal', 'DateTime', 'DateTimeDigitized'):
            if dt_key in by_name:
                # Pillow 返回 "2024:01:15 12:30:00"，转成 "2024-01-15 12:30:00"
                dt_str = str(by_name[dt_key]).replace(':', '-', 2)
                result['DateTimeOriginal'] = dt_str
                result['CreateDate'] = dt_str
                break

        # ── 相机信息 ──
        if 'Make' in by_name:
            result['Make'] = str(by_name['Make']).strip('\x00')
        if 'Model' in by_name:
            result['Model'] = str(by_name['Model']).strip('\x00')

        # ── 曝光参数 ──
        if 'ExposureTime' in by_name:
            et = by_name['ExposureTime']
            num = et.numerator if hasattr(et, 'numerator') else et[0]
            den = et.denominator if hasattr(et, 'denominator') else et[1]
            result['ExposureTime'] = f"1/{int(den/num)}s" if num == 1 else f"{num}/{den}s"
        if 'FNumber' in by_name:
            fn = by_name['FNumber']
            val = fn.numerator / fn.denominator if hasattr(fn, 'numerator') else fn[0] / fn[1]
            result['FNumber'] = f"f/{val:.1f}"
        if 'ISOSpeedRatings' in by_name:
            result['ISO'] = str(by_name['ISOSpeedRatings'])

        # ── GPS ──
        gps_raw = by_name.get('GPSInfo', {})
        gps = {}
        for gps_id, gps_val in gps_raw.items():
            gps_name = ExifTags.GPSTAGS.get(gps_id, str(gps_id))
            gps[gps_name] = gps_val

        if 'GPSLatitude' in gps and 'GPSLatitudeRef' in gps \
                and not _gps_rational_all_zero(gps['GPSLatitude']):
            lat_str = _dms_to_str(gps['GPSLatitude'], gps['GPSLatitudeRef'])
            result['GPSLatitude'] = lat_str
        if 'GPSLongitude' in gps and 'GPSLongitudeRef' in gps \
                and not _gps_rational_all_zero(gps['GPSLongitude']):
            lon_str = _dms_to_str(gps['GPSLongitude'], gps['GPSLongitudeRef'])
            result['GPSLongitude'] = lon_str
        if 'GPSLatitude' in result and 'GPSLongitude' in result:
            result['GPSPosition'] = f"{result['GPSLatitude']}  {result['GPSLongitude']}"

    except Exception as e:
        logger.warning(f'Pillow EXIF fallback error: {path} : {e}')

    return result


def _sanitize_exif_gps(exif: dict) -> None:
    """清除无 GPS 时常见的 0°0′ 占位字段，避免水印显示假坐标。"""
    if not exif:
        return
    combo = (
        exif.get('GPSPosition')
        or (str(exif.get('GPSLatitude', '')).strip() + '  ' + str(exif.get('GPSLongitude', '')).strip())
    ).strip()
    if combo and not gps_display(combo):
        for k in ('GPSPosition', 'GPSLatitude', 'GPSLongitude', 'GPSAltitude'):
            exif[k] = ''


def get_exif_batch(paths: list) -> dict[str, dict]:
    """
    批量读取多个文件的 EXIF，只启动一次 Perl 进程（高效、稳定）。
    返回 {文件路径: exif_dict} 的字典。
    若 ExifTool 失败，逐个降级到 Pillow 读取。
    """
    if not paths:
        return {}

    result = {p: {} for p in paths}

    try:
        kwargs = {
            'timeout': 60,
            'stderr': subprocess.DEVNULL,
        }
        if platform.system() == 'Windows':
            kwargs['creationflags'] = _CREATE_NO_WINDOW

        # ExifTool 支持一次传入多个路径，用 -p 分组输出
        # 用 -json 格式输出，每个文件是一个 JSON 对象，最方便解析
        cmd = [EXIFTOOL_PATH, '-d', '%Y-%m-%d %H:%M:%S%3f%z', '-json'] + list(paths)
        output_bytes = subprocess.check_output(cmd, **kwargs)
        output = output_bytes.decode('utf-8', errors='ignore')

        records = json.loads(output)  # list of dicts
        for record in records:
            source = record.get('SourceFile', '')
            if not source:
                continue
            # 找到对应的原始路径（ExifTool 可能把路径正规化）
            matched = source
            if matched not in result:
                # 尝试大小写不敏感匹配
                for p in paths:
                    if os.path.normcase(p) == os.path.normcase(source):
                        matched = p
                        break
            exif = {}
            for k, v in record.items():
                if k == 'SourceFile':
                    continue
                key = re.sub(r'\s+', '', k)
                key = re.sub(r'/', '', key)
                val = ''.join(c for c in str(v) if ord(c) < 128)
                exif[key] = val
            result[matched] = exif
            _sanitize_exif_gps(exif)

        logger.info(f'ExifTool 批量读取成功: {len(records)}/{len(paths)} 个文件')

    except subprocess.TimeoutExpired:
        logger.warning('ExifTool 批量超时，逐个降级到 Pillow')
        for p in paths:
            result[p] = _get_exif_from_pillow(p)
    except FileNotFoundError:
        logger.warning('ExifTool 不存在，逐个降级到 Pillow')
        for p in paths:
            result[p] = _get_exif_from_pillow(p)
    except Exception as e:
        logger.warning(f'ExifTool 批量失败 ({e})，逐个降级到 Pillow')
        for p in paths:
            result[p] = _get_exif_from_pillow(p)

    # 对 ExifTool 返回为空的条目，用 Pillow 补充；并统一清理假 GPS
    for p, exif in result.items():
        if not exif:
            result[p] = _get_exif_from_pillow(p)
        _sanitize_exif_gps(result[p])

    # 绝对路径别名，避免请求里的路径写法与缓存键不一致时读不到 EXIF
    for p, exif in list(result.items()):
        try:
            result[str(Path(p).resolve())] = exif
        except Exception:
            pass

    return result


def get_exif(path) -> dict:
    """
    获取单个文件的 EXIF 信息（兼容旧接口）。
    优先使用 ExifTool；若崩溃或超时，自动降级到 Pillow。
    """
    exif_dict = {}
    exiftool_ok = False

    try:
        kwargs = {
            'timeout': 20,           # 超时 20 秒，防止 Perl 进程挂死
            'stderr': subprocess.DEVNULL,
        }
        if platform.system() == 'Windows':
            kwargs['creationflags'] = _CREATE_NO_WINDOW  # 禁止弹出控制台/错误框

        output_bytes = subprocess.check_output(
            [EXIFTOOL_PATH, '-d', '%Y-%m-%d %H:%M:%S%3f%z', path],
            **kwargs
        )
        output = output_bytes.decode('utf-8', errors='ignore')

        for line in output.splitlines():
            kv_pair = line.split(':')
            if len(kv_pair) < 2:
                continue
            key = kv_pair[0].strip()
            value = ':'.join(kv_pair[1:]).strip()
            key = re.sub(r'\s+', '', key)
            key = re.sub(r'/', '', key)
            exif_dict[key] = value

        for key, value in exif_dict.items():
            exif_dict[key] = ''.join(c for c in value if ord(c) < 128)

        exiftool_ok = bool(exif_dict)

    except subprocess.TimeoutExpired:
        logger.warning(f'ExifTool 超时，降级到 Pillow 读取 EXIF: {path}')
    except FileNotFoundError:
        logger.warning(f'ExifTool 不存在，降级到 Pillow 读取 EXIF: {path}')
    except Exception as e:
        logger.warning(f'ExifTool 失败 ({e})，降级到 Pillow 读取 EXIF: {path}')

    if not exiftool_ok:
        exif_dict = _get_exif_from_pillow(path)
        if exif_dict:
            logger.info(f'Pillow EXIF fallback 成功: {path}')
        else:
            logger.warning(f'EXIF 读取完全失败（ExifTool + Pillow 均无结果）: {path}')

    _sanitize_exif_gps(exif_dict)
    return exif_dict


def list_files(path: str, suffixes: set[str], depth: int = 0, max_depth: int = 20):
    """
    使用 pathlib 实现的版本

    Args:
        path: 要扫描的路径
        suffixes: 支持的文件后缀
        depth: 当前递归深度（内部使用）
        max_depth: 最大递归深度，防止无限递归
    """
    result = []
    root = Path(path).resolve()

    if not root.exists():
        return result

    # 防止递归过深
    if depth > max_depth:
        logger.warning(f"list_files: 达到最大递归深度 {max_depth}，跳过 {path}")
        return result

    try:
        # 分离文件夹和文件，分别排序
        items = list(root.iterdir())
        dirs = sorted([i for i in items if i.is_dir()], key=lambda x: x.name.lower(), reverse=True)
        files = sorted([i for i in items if i.is_file()], key=lambda x: (x.stat().st_mtime, x.name.lower()),
                       reverse=True)

        # 先处理文件夹
        for item in dirs:
            if item.name.startswith('.'):
                continue
            # 跳过符号链接，避免无限递归
            if item.is_symlink():
                continue
            children = list_files(str(item), suffixes, depth + 1, max_depth)
            if children:
                result.append({
                    'label': item.name,
                    'value': str(item),
                    'children': children,
                })

        # 再处理文件
        for item in files:
            if item.name.startswith('.'):
                continue
            if item.suffix.lower() in suffixes:
                result.append({
                    'label': item.name,
                    'value': str(item),
                    'is_file': True
                })

    except PermissionError:
        logger.debug(f"list_files: 权限不足，跳过 {path}")
    except Exception as e:
        logger.error(f"list_files: 扫描失败 {path}: {e}")

    return result


def log_rt(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()  # 记录开始时间
        result = func(*args, **kwargs)  # 调用被装饰的函数
        end_time = time.time()  # 记录结束时间
        elapsed_time = (end_time - start_time) * 1000  # 计算运行时间

        logger.debug(f"[monitor]api#{func.__name__} cost {elapsed_time:.2f}ms")
        return result

    return wrapper


def convert_heic_to_jpeg(path: str, quality: int = 90) -> io.BytesIO:
    """转换 HEIC 为 JPEG 字节流"""
    with Image.open(path) as img:
        if img.mode in ('RGBA', 'P', 'LA'):
            img = img.convert('RGB')

        buffer = io.BytesIO()
        img.save(buffer, format='JPEG', quality=quality)
        buffer.seek(0)
        return buffer


# ==================== 模板管理相关方法 ====================

def get_template_path(template_name: str) -> Path:
    """
    获取模板文件的完整路径

    Args:
        template_name: 模板名称（不含扩展名），如 "standard1"

    Returns:
        模板文件的完整 Path 对象
    """
    return templates_dir / f"{template_name}.json"


def get_template(template_name: str) -> Template:
    """
    读取并解析模板文件为 Jinja2 Template 对象

    Args:
        template_name: 模板名称（不含扩展名），如 "standard1"

    Returns:
        Jinja2 Template 对象，已注册 vh, vw, auto_logo 全局函数
    """
    template_path = get_template_path(template_name)
    with open(template_path, encoding='utf-8') as f:
        template_str = f.read()
    template = Template(template_str)
    template.globals['vh'] = vh
    template.globals['vw'] = vw
    template.globals['auto_logo'] = auto_logo
    template.globals['gps_safe'] = gps_safe
    template.globals['gps_display'] = gps_display
    return template


def get_template_content(template_name: str) -> str:
    """
    获取模板文件的内容（原始字符串）

    Args:
        template_name: 模板名称（不含扩展名），如 "standard1"

    Returns:
        模板文件的原始内容字符串
    """
    template_path = get_template_path(template_name)
    with open(template_path, encoding='utf-8') as f:
        return f.read()


def save_template(template_name: str, content: str) -> None:
    """
    保存模板文件

    Args:
        template_name: 模板名称（不含扩展名），如 "standard1"
        content: 模板内容（JSON 字符串）
    """
    template_path = get_template_path(template_name)
    # 确保目录存在
    template_path.parent.mkdir(parents=True, exist_ok=True)
    with open(template_path, 'w', encoding='utf-8') as f:
        f.write(content)


def create_template(template_name: str, content: str = '[]') -> None:
    """
    创建新的模板文件

    Args:
        template_name: 模板名称（不含扩展名），如 "my_template"
        content: 模板内容（JSON 字符串），默认为空数组 '[]'

    Raises:
        FileExistsError: 如果模板文件已存在
    """
    template_path = get_template_path(template_name)
    if template_path.exists():
        raise FileExistsError(f"模板 '{template_name}' 已存在")
    save_template(template_name, content)


def list_templates() -> list[str]:
    """
    列出所有可用的模板名称

    Returns:
        模板名称列表（不含扩展名）
    """
    if not templates_dir.exists():
        return []
    return [f.stem for f in templates_dir.glob('*.json')]
