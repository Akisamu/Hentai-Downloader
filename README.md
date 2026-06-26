# ERO-Downloader

从 nhentai.com 和 eromanga-show.com 下载漫画并打包为 PDF，附带 Gradio 图形界面。

## 安装

```bash
git clone --recurse-submodules https://github.com/Akisamu/ERO-Downloader.git
cd ERO-Downloader
python -m venv .venv
.venv\Scripts\activate      # Windows
pip install -r requirements.txt
```

额外依赖（可选，用于 PDF 后处理压缩）：[Ghostscript](https://ghostscript.com/)

## 使用

### Web 界面（推荐）

```bash
python app.py
# 浏览器打开 http://127.0.0.1:7860
# 局域网其他设备访问 http://<本机IP>:7860
```

三个标签页：

| 标签 | 功能 |
|------|------|
| hentai-comics | 输入 nhentai.com 漫画链接，自动爬取元数据、下载、生成 PDF |
| eromanga | 输入 eromanga-show.com 文章链接，同上 |
| History | 下载历史，支持缩略图预览、PDF 在线查看、单条删除 |

支持调整 JPEG 质量（30-95）和最大分辨率（720p / 1080p / 1600p / 原始）。

### 终端模式

编辑 `main.py` 中的 URL 列表后直接运行：

```bash
python main.py
```

三种输入模式：

```python
# Mode A: nhentai.com 链接（自动爬取）
nhentai_urls = ['https://nhentai.com/en/comic/...']

# Mode B: eromanga-show.com 文章链接（自动爬取）
eromanga_urls = ['https://eromanga-show.com/articles/...']

# Mode C: 手动指定元数据
infos = [{'name': '...', 'final': 70, 'id': 616696, 'format': 'webp'}]
```

### PowerShell 快捷方式（Windows）

将 `D:\Akisamu\Documents\PowerShell` 添加到 PATH 后，打开 PowerShell 输入：

```powershell
ero
```

## 文件结构

```
outputs/
  .history/
    info              ← 下载历史（JSON Lines）
    thumbnails/       ← 封面缩略图
  *.pdf               ← 生成的 PDF
```

## 依赖

`beautifulsoup4` `gradio` `natsort` `pillow` `reportlab` `requests` `tqdm`
