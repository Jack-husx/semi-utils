# coding: utf-8
# generate_pdf_doc.py
# Run: .venv\Scripts\python generate_pdf_doc.py

import os, subprocess, sys, time

BASE   = os.path.dirname(os.path.abspath(__file__))
HTML_F = os.path.join(BASE, "使用说明_temp.html")
PDF_F  = os.path.join(BASE, "使用说明.pdf")

EDGE   = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

# ── HTML 内容 ───────────────────────────────────────────────
HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8"/>
<title>照片水印工具 · 使用说明</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: "Microsoft YaHei", "微软雅黑", "PingFang SC", sans-serif;
    font-size: 11pt;
    color: #1e1e1e;
    line-height: 1.7;
    padding: 0;
  }

  /* ── 封面 ── */
  .cover {
    background: #3478F6;
    height: 78mm;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    page-break-after: always;
  }
  .cover h1 { color: #fff; font-size: 28pt; font-weight: 700; margin-bottom: 6px; }
  .cover h2 { color: #fff; font-size: 16pt; font-weight: 400; margin-bottom: 8px; }
  .cover p  { color: #c8dcff; font-size: 9pt; }

  /* ── 封面下方内容 ── */
  .cover-body { padding: 16mm 20mm 0; page-break-after: always; }

  /* ── 正文页 ── */
  .page-body { padding: 14mm 20mm 14mm; }

  /* ── 页眉 ── */
  .header-line {
    border-bottom: 0.5px solid #d2d6dc;
    padding-bottom: 4px;
    margin-bottom: 12px;
    font-size: 8pt;
    color: #d2d6dc;
  }

  /* ── 章节标题 ── */
  .ch {
    font-size: 14pt;
    font-weight: 700;
    color: #3478F6;
    border-left: 4px solid #3478F6;
    padding-left: 8px;
    margin: 18px 0 10px;
  }

  /* ── 简介框 ── */
  .intro-box {
    background: #EBF4FF;
    border: 1.5px solid #3478F6;
    border-radius: 6px;
    padding: 12px 14px;
    margin: 14px 0;
  }
  .intro-box .intro-h { color: #3478F6; font-weight: 700; font-size: 12pt; margin-bottom: 5px; }

  /* ── 警告框 ── */
  .warn {
    background: #FFF3CD;
    border: 1px solid #FFC107;
    border-radius: 4px;
    padding: 8px 12px;
    font-size: 9.5pt;
    color: #785000;
    margin: 10px 0;
  }
  .warn::before { content: "[!]  "; font-weight: 700; }

  /* ── 步骤框 ── */
  .step {
    background: #EBF4FF;
    border: 1px solid #3478F6;
    border-radius: 5px;
    padding: 8px 12px 10px;
    margin: 8px 0;
  }
  .step-title {
    font-weight: 700;
    color: #3478F6;
    font-size: 12pt;
    margin-bottom: 5px;
  }
  .step-num {
    display: inline-block;
    background: #3478F6;
    color: #fff;
    border-radius: 50%;
    width: 22px;
    height: 22px;
    text-align: center;
    line-height: 22px;
    font-size: 11pt;
    font-weight: 700;
    margin-right: 6px;
    vertical-align: middle;
  }
  .step ul { margin: 0; padding-left: 18px; font-size: 10.5pt; }
  .step li { margin: 2px 0; }

  /* ── 代码块 ── */
  pre {
    background: #F5F7FA;
    border: 0.5px solid #d2d6dc;
    border-radius: 4px;
    padding: 8px 12px;
    font-family: Consolas, "Courier New", monospace;
    font-size: 9pt;
    color: #3C3C3C;
    margin: 8px 0;
    white-space: pre;
  }

  /* ── 表格 ── */
  table {
    width: 100%;
    border-collapse: collapse;
    margin: 8px 0 14px;
    font-size: 10.5pt;
  }
  thead th {
    background: #3478F6;
    color: #fff;
    font-weight: 700;
    padding: 6px 10px;
    text-align: center;
  }
  tbody td {
    padding: 5px 10px;
  }
  tbody tr:nth-child(even) td { background: #F5F7FA; }
  tbody tr:nth-child(odd)  td { background: #fff; }
  table, th, td { border: none; }
  tbody tr:last-child { border-bottom: 0.5px solid #d2d6dc; }

  /* ── Q&A ── */
  .qa-q {
    font-weight: 700;
    color: #3478F6;
    font-size: 11pt;
    margin-top: 12px;
    margin-bottom: 4px;
  }
  .qa-a {
    font-size: 10.5pt;
    padding-left: 12px;
    margin: 2px 0;
  }
  hr.thin {
    border: none;
    border-top: 0.5px solid #d2d6dc;
    margin: 12px 0;
  }

  .small-gray { font-size: 9.5pt; color: #6B7280; margin-top: 8px; }

  /* ── 打印设置 ── */
  @media print {
    @page {
      size: A4;
      margin: 14mm 20mm 14mm;
    }
    @page :first { margin: 0; }
    body { padding: 0; }
    .cover { -webkit-print-color-adjust: exact; print-color-adjust: exact; height: 100vh; }
    .cover-body { padding: 16mm 20mm 0; }
    .intro-box, .warn, .step, pre, table thead {
      -webkit-print-color-adjust: exact;
      print-color-adjust: exact;
    }
    .ch { page-break-after: avoid; }
    .step { page-break-inside: avoid; }
  }
</style>
</head>
<body>

<!-- ══ 封面 ══ -->
<div class="cover">
  <h1>照片水印工具</h1>
  <h2>使用说明</h2>
  <p>semi-utils-win &nbsp;·&nbsp; Windows 独立版，无需安装 Python</p>
</div>

<!-- ══ 封面下方 ══ -->
<div class="cover-body">
  <div class="intro-box">
    <div class="intro-h">本工具可做什么？</div>
    <p>自动读取照片的 EXIF 信息（GPS 经纬度、拍摄时间），在照片底部生成白色水印区域，输出适合打印的成品照片。无需安装 Python，双击 start.bat 即可使用。</p>
  </div>

  <div class="ch">一、系统要求</div>
  <table>
    <thead><tr><th style="width:28%">项目</th><th>要求</th></tr></thead>
    <tbody>
      <tr><td>操作系统</td><td>Windows 10 / 11（64 位）</td></tr>
      <tr><td>磁盘空间</td><td>解压后约 200 MB</td></tr>
      <tr><td>网络</td><td>不需要</td></tr>
      <tr><td>其他依赖</td><td>无需安装 Python，无需安装任何额外软件</td></tr>
    </tbody>
  </table>
</div>

<!-- ══ 第 2 页：解压 & 步骤 ══ -->
<div class="page-body">
  <div class="header-line">照片水印工具 · 使用说明</div>

  <div class="ch">二、解压安装</div>
  <p>1. 将收到的 <b>semi-utils-win.zip</b> 解压到任意文件夹，例如 <code>D:\\semi-utils-win\\</code></p>
  <p style="margin-top:8px"><b>2. 解压后目录结构如下：</b></p>
<pre>semi-utils-win\
    +-- semi-utils.exe      &lt;-- 主程序
    +-- start.bat           &lt;-- 启动脚本（双击这个）
    +-- config\             &lt;-- 字体、Logo、水印模板
    +-- exiftool\           &lt;-- EXIF 读取工具（自动调用）</pre>
  <div class="warn">请勿将程序放在含中文或空格的路径下，推荐放在 C:\\ 或 D:\\ 根目录下的纯英文文件夹内（如 D:\\semi-utils-win\\）。</div>

  <div class="ch">三、使用步骤</div>

  <div class="step">
    <div class="step-title"><span class="step-num">1</span> 启动程序</div>
    <ul>
      <li>双击 <b>start.bat</b></li>
      <li>首次运行会自动创建 <code>input\</code> 和 <code>output\</code> 文件夹</li>
      <li>随后自动打开浏览器，访问 <b>http://localhost:15050</b></li>
      <li>启动后出现黑色命令行窗口，运行期间请勿关闭它</li>
      <li>若浏览器未自动打开，请手动输入地址：http://localhost:15050</li>
    </ul>
  </div>

  <div class="step">
    <div class="step-title"><span class="step-num">2</span> 放入照片</div>
    <ul><li>将需要处理的照片复制到 <b>input\</b> 文件夹中</li></ul>
  </div>

  <p style="margin:8px 0 4px"><b>支持的格式：</b></p>
  <table>
    <thead><tr><th style="width:28%">格式</th><th>说明</th></tr></thead>
    <tbody>
      <tr><td>.jpg / .jpeg</td><td>常见相机 / 手机照片</td></tr>
      <tr><td>.png</td><td>PNG 图片</td></tr>
      <tr><td>.heic</td><td>iPhone 拍摄的 HEIC 格式</td></tr>
      <tr><td>.tiff</td><td>高质量 TIFF 格式</td></tr>
      <tr><td>.webp</td><td>WebP 格式</td></tr>
    </tbody>
  </table>

  <div class="step">
    <div class="step-title"><span class="step-num">3</span> 在浏览器中处理</div>
    <ul>
      <li>① 打开浏览器页面（http://localhost:15050）</li>
      <li>② 点击文件列表右上角的【刷新】按钮，加载 input\ 中的照片</li>
      <li>③ 勾选需要处理的文件（默认全选）</li>
      <li>④ 点击【开始处理】按钮</li>
      <li>⑤ 等待进度完成，右下角显示成功 / 失败数量</li>
    </ul>
  </div>

  <div class="step">
    <div class="step-title"><span class="step-num">4</span> 取走成品</div>
    <ul><li>处理完成的照片自动保存到 <b>output\</b> 文件夹，文件名与原图相同</li></ul>
  </div>

  <div class="ch">四、水印内容说明</div>
  <p>程序读取照片 EXIF 信息，在照片底部生成白色水印区域，内容如下：</p>
  <table style="margin-top:8px">
    <thead><tr><th style="width:20%">位置</th><th>内容</th></tr></thead>
    <tbody>
      <tr><td>左侧</td><td>GPS 经纬度（无 GPS 信息时为空）</td></tr>
      <tr><td>右侧</td><td>拍摄时间</td></tr>
    </tbody>
  </table>
  <div class="warn">使用微信、QQ 等转发的照片通常已压缩并丢失 EXIF，导致经纬度和时间无法读取。请务必使用相机 / 手机直出的原图。</div>

  <div class="ch">五、常见问题</div>

  <div class="qa-q">Q1：双击 start.bat 窗口一闪而过，程序没有启动？</div>
  <div class="qa-a">· 检查解压路径是否含有中文或空格，如有请移到纯英文路径。</div>
  <div class="qa-a">· 确认 input\ 和 output\ 文件夹已存在（首次运行后自动创建）。</div>
  <hr class="thin"/>

  <div class="qa-q">Q2：浏览器打开后，刷新文件列表显示为空？</div>
  <div class="qa-a">· 确认照片已复制到 input\ 文件夹，而不是其他位置。</div>
  <div class="qa-a">· 点击文件列表右侧的【刷新图标】重新加载。</div>
  <hr class="thin"/>

  <div class="qa-q">Q3：处理完成但照片显示「失败」？</div>
  <div class="qa-a">· 照片格式不在支持列表内。</div>
  <div class="qa-a">· 照片文件已损坏或被其他程序占用。</div>
  <div class="qa-a">· 照片路径含有特殊字符。</div>
  <hr class="thin"/>

  <div class="qa-q">Q4：output 里的照片水印区域没有经纬度和时间（空白）？</div>
  <div class="qa-a">· 照片不含 EXIF 信息。请使用相机原图，不要使用微信 / 截图传输的照片。</div>
  <hr class="thin"/>

  <div class="qa-q">Q5：杀毒软件提示 semi-utils.exe 有风险？</div>
  <div class="qa-a">· 这是 Python 程序打包为 exe 后的常见误报（PyInstaller 触发启发式检测）。</div>
  <div class="qa-a">· 程序不含任何恶意代码，将程序所在文件夹添加到杀毒白名单即可正常使用。</div>
  <hr class="thin"/>

  <div class="qa-q">Q6：如何退出程序？</div>
  <div class="qa-a">· 关闭黑色命令行窗口，或在窗口中按 Ctrl+C 退出。</div>
  <div class="qa-a">· 仅关闭浏览器标签页不会停止程序。</div>

  <div class="ch">六、目录结构速查</div>
<pre>semi-utils-win\
    +-- start.bat           &lt;-- 每次使用前双击此文件启动
    +-- semi-utils.exe      &lt;-- 主程序（勿删除）
    +-- config\             &lt;-- 配置（勿删除）
    |   +-- fonts\          &lt;-- 字体文件
    |   +-- logos\          &lt;-- 相机品牌 Logo
    |   +-- templates\      &lt;-- 水印样式模板
    +-- exiftool\           &lt;-- EXIF 工具（勿删除）
    +-- input\              &lt;-- 放入原始照片
    +-- output\             &lt;-- 取走处理后的照片</pre>

  <p class="small-gray">如遇到以上未列出的问题，请将命令行窗口中的错误信息截图发给技术支持。</p>
</div>

</body>
</html>
"""


def main():
    # 1. 写 HTML 临时文件（UTF-8 with BOM，确保 Edge 正确识别编码）
    with open(HTML_F, "w", encoding="utf-8-sig") as f:
        f.write(HTML)
    print(f"HTML written: {HTML_F}")

    # 2. 用 Edge 无头模式打印为 PDF
    html_url = "file:///" + HTML_F.replace("\\", "/")
    cmd = [
        EDGE,
        "--headless=new",
        "--disable-gpu",
        "--no-sandbox",
        f"--print-to-pdf={PDF_F}",
        "--print-to-pdf-no-header",
        "--run-all-compositor-stages-before-draw",
        "--virtual-time-budget=5000",
        html_url,
    ]
    print("Running Edge headless...")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        print("STDERR:", result.stderr[:500])
        sys.exit(1)

    # 3. 清理临时 HTML
    time.sleep(1)
    if os.path.exists(PDF_F):
        size_kb = os.path.getsize(PDF_F) // 1024
        print(f"PDF generated: {PDF_F}  ({size_kb} KB)")
        try:
            os.remove(HTML_F)
        except Exception:
            pass
    else:
        print("ERROR: PDF file not found after conversion.")
        sys.exit(1)


if __name__ == "__main__":
    main()
