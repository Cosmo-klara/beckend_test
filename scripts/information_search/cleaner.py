"""
数据清洗和验证模块
负责清洗爬取的数据，添加985/211/双一流标签
"""
import logging
from typing import List, Dict
UNIVERSITY_TAGS = {
    '北京大学': {'985': True, '211': True, '双一流': True},
    '清华大学': {'985': True, '211': True, '双一流': True},
    '复旦大学': {'985': True, '211': True, '双一流': True},
    '上海交通大学': {'985': True, '211': True, '双一流': True},
    '浙江大学': {'985': True, '211': True, '双一流': True},
    '南京大学': {'985': True, '211': True, '双一流': True},
    '北京理工大学': {'985': True, '211': True, '双一流': True},
    '北京航空航天大学': {'985': True, '211': True, '双一流': True},
    '华中科技大学': {'985': True, '211': True, '双一流': True},
    '南开大学': {'985': True, '211': True, '双一流': True},
}

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DataCleaner:

    def __init__(self):
        self.university_tags = UNIVERSITY_TAGS

    def add_university_tags(self, admission_info: Dict) -> Dict:
        school_name = admission_info.get('学校', '')

        # 查找院校标签信息
        tags = self.university_tags.get(school_name, {})

        # 添加标签（1表示是，0表示否）
        admission_info['_985'] = '1' if tags.get('985', False) else '0'
        admission_info['_211'] = '1' if tags.get('211', False) else '0'
        admission_info['双一流'] = '1' if tags.get('双一流', False) else '0'

        return admission_info

    def clean_score(self, score_str: str) -> str:
        if not score_str:
            return ''
        # 移除空格和特殊字符，只保留数字
        cleaned = ''.join(filter(str.isdigit, str(score_str)))
        return cleaned if cleaned else score_str.strip()

    def clean_ranking(self, ranking_str: str) -> str:
        if not ranking_str:
            return ''

        # 移除空格和特殊字符，只保留数字
        cleaned = ''.join(filter(str.isdigit, str(ranking_str)))
        return cleaned if cleaned else ranking_str.strip()

    def validate_data(self, admission_info: Dict) -> bool:
        required_fields = ['年份', '学校', '生源地']

        for field in required_fields:
            if not admission_info.get(field):
                logger.warning(f"数据缺少必需字段: {field}")
                return False

        # 验证年份格式
        year = admission_info.get('年份')
        if isinstance(year, str):
            if not year.isdigit() or len(year) != 4:
                logger.warning(f"年份格式错误: {year}")
                return False

        return True

    def clean_data(self, admission_list: List[Dict]) -> List[Dict]:
        cleaned_list = []

        for admission_info in admission_list:
            # 验证数据
            if not self.validate_data(admission_info):
                continue

            # 清洗分数和排名
            if '最低分' in admission_info:
                admission_info['最低分'] = self.clean_score(admission_info['最低分'])
            if '最低分排名' in admission_info:
                admission_info['最低分排名'] = self.clean_ranking(admission_info['最低分排名'])

            # 添加院校标签
            admission_info = self.add_university_tags(admission_info)

            cleaned_list.append(admission_info)

        logger.info(f"数据清洗完成，原始数据: {len(admission_list)} 条，清洗后: {len(cleaned_list)} 条")
        return cleaned_list

