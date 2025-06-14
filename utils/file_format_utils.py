import os
import platform
import shutil
import subprocess
from pathlib import Path
from pdf2image import convert_from_path
from openpyxl import load_workbook
from openpyxl.styles import Side, Border
import logging

logger = logging.getLogger(__name__)


def set_excel_landscape_format(xlsx_path: str, sheetname: str = None):
    """
    设置Excel文件为横向打印格式
    
    Args:
        xlsx_path: Excel文件路径
        sheetname: 工作表名称，可选
    """
    try:
        wb = load_workbook(xlsx_path)
        ws = wb[sheetname] if sheetname else wb.active
        
        # 横向 & A4
        ws.page_setup.orientation = ws.ORIENTATION_LANDSCAPE
        ws.page_setup.paperSize = ws.PAPERSIZE_A4
        
        # 一页宽（不限行数）
        ws.page_setup.fitToWidth = 1
        ws.page_setup.fitToHeight = 0
        
        # 内容水平居中
        ws.print_options.horizontalCentered = True
        
        # 自动设置打印区域（所有已用单元格）
        min_row = ws.min_row
        max_row = ws.max_row
        min_col = ws.min_column
        max_col = ws.max_column
        start_cell = ws.cell(row=min_row, column=min_col).coordinate
        end_cell = ws.cell(row=max_row, column=max_col).coordinate
        ws.print_area = f"{start_cell}:{end_cell}"
        
        # 修复A1:L1标题区右侧边框加粗问题
        # 如果你的标题区不是A1:L1，请相应修改
        right_title_cell = ws['L1']
        # 用现有边框信息，右侧设为medium
        right_title_cell.border = Border(
            left=right_title_cell.border.left,
            right=Side(style='medium'),
            top=right_title_cell.border.top,
            bottom=right_title_cell.border.bottom
        )
        
        wb.save(xlsx_path)
        logger.info(f"Excel文件格式设置完成: {xlsx_path}")
        
    except Exception as e:
        logger.error(f"设置Excel格式时出错: {str(e)}")
        raise


def find_soffice_executable() -> str:
    """
    动态寻找LibreOffice的soffice可执行文件
    
    Returns:
        str: soffice可执行文件路径
        
    Raises:
        FileNotFoundError: 未找到soffice可执行文件
    """
    sys_name = platform.system()
    candidates = []
    
    if sys_name == "Windows":
        candidates += [
            r"C:\Program Files\LibreOffice\program\soffice.exe",
            r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
        ]
    elif sys_name == "Darwin":  # macOS
        candidates += [
            "/Applications/LibreOffice.app/Contents/MacOS/soffice",
            shutil.which("soffice"),
        ]
    else:  # Linux
        candidates += [shutil.which("soffice"), shutil.which("libreoffice")]
    
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            logger.info(f"找到LibreOffice可执行文件: {candidate}")
            return candidate
    
    raise FileNotFoundError("无法找到 LibreOffice 的 soffice，可执行文件未安装或不在 PATH")


def convert_xlsx_to_pdf(xlsx_path: Path, output_dir: Path = None) -> Path:
    """
    将Excel文件转换为PDF
    
    Args:
        xlsx_path: Excel文件路径
        output_dir: 输出目录，如果不指定则使用Excel文件所在目录
        
    Returns:
        Path: 生成的PDF文件路径
    """
    try:
        if output_dir is None:
            output_dir = xlsx_path.parent
        
        soffice_path = find_soffice_executable()
        
        subprocess.run([
            soffice_path, "--headless",
            "--convert-to", "pdf",
            "--outdir", str(output_dir),
            str(xlsx_path)
        ], check=True)
        
        pdf_path = output_dir / xlsx_path.with_suffix('.pdf').name
        logger.info(f"PDF文件生成完成: {pdf_path}")
        return pdf_path
        
    except Exception as e:
        logger.error(f"Excel转PDF时出错: {str(e)}")
        raise


def get_poppler_path() -> str:
    """
    获取Poppler工具路径，仅Windows需要显式指定
    
    Returns:
        str: Poppler路径，非Windows系统返回None
    """
    if platform.system() == "Windows":
        # Windows系统需要指定Poppler路径
        return r"D:\Program Files\poppler-24.08.0\Library\bin"
    return None


def convert_pdf_to_png(pdf_path: Path, output_path: Path = None, dpi: int = 200) -> Path:
    """
    将PDF文件转换为PNG图片（仅转换第一页）
    
    Args:
        pdf_path: PDF文件路径
        output_path: 输出PNG文件路径，如果不指定则使用PDF文件名
        dpi: 图片分辨率，默认200
        
    Returns:
        Path: 生成的PNG图片路径
    """
    try:
        if output_path is None:
            output_path = pdf_path.with_suffix('.png')
        
        poppler_path = get_poppler_path()
        
        pages = convert_from_path(
            str(pdf_path), 
            dpi=dpi,
            poppler_path=poppler_path
        )
        
        # 只保存第一页
        pages[0].save(str(output_path), "PNG")
        logger.info(f"PNG图片生成完成: {output_path}")
        return output_path
        
    except Exception as e:
        logger.error(f"PDF转PNG时出错: {str(e)}")
        raise


def ensure_directory_exists(directory_path: str) -> Path:
    """
    确保目录存在，如果不存在则创建
    
    Args:
        directory_path: 目录路径
        
    Returns:
        Path: 目录路径对象
    """
    dir_path = Path(directory_path)
    dir_path.mkdir(parents=True, exist_ok=True)
    return dir_path 