import os
import pandas as pd
import logging
from datetime import datetime
from typing import List, Dict
OUTPUT_CONFIG = {
    'output_dir': 'output',
    'filename_prefix': 'admission_info',
}

CSV_FIELDS = [
    '年份',
    '学校',
    '_985',
    '_211',
    '双一流',
    '科类',
    '批次',
    '专业',
    '最低分',
    '最低分排名',
    '全国统一招生代码',
    '招生类型',
    '生源地'
]

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CSVExporter:
    def __init__(self):
        self.output_dir = OUTPUT_CONFIG['output_dir']
        self.filename_prefix = OUTPUT_CONFIG['filename_prefix']
        self.ensure_output_dir()

    def ensure_output_dir(self):
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
            logger.info(f"创建输出目录: {self.output_dir}")

    def generate_filename(self, school_name: str, year: int = None) -> str:
        if year is None:
            year = datetime.now().year

        # 创建学校名称目录
        school_dir = os.path.join(self.output_dir, school_name)
        if not os.path.exists(school_dir):
            os.makedirs(school_dir)
            logger.info(f"创建学校目录: {school_dir}")

        # 生成文件名：学校名称_年份.csv
        filename = f"{school_name}_{year}.csv"
        return os.path.join(school_dir, filename)

    def export_to_csv(self, data: List[Dict], filename: str = None, year: int = None, school_name: str = None) -> str:
        if not data:
            logger.warning("没有数据可导出")
            return None

        # 从数据中提取学校名称（如果未提供）
        if school_name is None:
            school_name = data[0].get('学校', '未知学校')
            # 如果数据中有多个学校，使用第一个学校的名称
            logger.info(f"从数据中提取学校名称: {school_name}")

        # 从数据中提取年份（如果未提供）
        if year is None:
            year = data[0].get('年份', datetime.now().year)
            if isinstance(year, str):
                try:
                    year = int(year)
                except ValueError:
                    year = datetime.now().year

        # 生成文件名
        if filename is None:
            filename = self.generate_filename(school_name, year)

        # 确保数据包含所有必需字段
        df_data = []
        for item in data:
            row = {}
            for field in CSV_FIELDS:
                row[field] = item.get(field, '')
            df_data.append(row)

        # 创建DataFrame
        df = pd.DataFrame(df_data, columns=CSV_FIELDS)

        # 导出到CSV
        df.to_csv(filename, index=False, encoding='utf-8-sig')  # utf-8-sig确保Excel能正确打开中文

        logger.info(f"成功导出 {len(data)} 条记录到文件: {filename}")
        return filename

    def export_by_year(self, data: List[Dict], year: int, school_name: str = None) -> str:

        return self.export_to_csv(data, year=year, school_name=school_name)

