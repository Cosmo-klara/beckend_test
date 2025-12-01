"""
北京理工大学招生信息爬虫
专门用于爬取北京理工大学历年招生信息
"""
import requests
import json
import time
import logging
from typing import List, Dict, Optional
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BITCrawler:
    """北京理工大学招生信息爬虫类"""
    
    def __init__(self):
        self.base_url = 'https://admission.bit.edu.cn'
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'Referer': 'https://admission.bit.edu.cn/static/front/bit/basic/html_web/lnfs.html',
            'X-Requested-With': 'XMLHttpRequest'
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        self.school_name = '北京理工大学'
        self.school_code = '10007'  # 北京理工大学招生代码
    
    def _get_url(self, path: str) -> str:
        """构建完整URL"""
        if path.startswith('http'):
            return path
        if path.startswith('/'):
            return self.base_url + path
        return f"{self.base_url}/{path}"
    
    def get_filter_params(self) -> Optional[Dict]:
        """
        获取筛选参数（省份、年份、科类等）
        
        Returns:
            筛选参数字典，包含可选的省份、年份、科类列表
        """
        try:
            url = self._get_url('f/ajax_lnfs_param')
            response = self.session.post(url, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            if data.get('state') == 1:
                filter_data = data.get('data', {})
                logger.info("成功获取筛选参数")
                return filter_data
            else:
                logger.error(f"获取筛选参数失败: {data.get('msg', '未知错误')}")
                return None
        except Exception as e:
            logger.error(f"获取筛选参数时出错: {e}")
            return None
    
    def get_admission_data(self, params: Dict) -> Optional[Dict]:
        """
        获取招生数据
        
        Args:
            params: 请求参数，包含省份(ssmc)、年份(zsnf)、科类(klmc)等
            
        Returns:
            包含招生数据的字典
        """
        try:
            url = self._get_url('f/ajax_lnfs')
            response = self.session.post(url, data=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            if data.get('state') == 1:
                return data.get('data', {})
            else:
                logger.warning(f"获取数据失败: {data.get('msg', '未知错误')}")
                return None
        except Exception as e:
            logger.error(f"获取招生数据时出错: {e}")
            return None
    
    def parse_batch_data(self, batch_list: List[Dict], year: int, province: str) -> List[Dict]:
        """
        解析普通批录取情况数据
        
        Args:
            batch_list: 普通批录取数据列表
            year: 年份
            province: 省份
            
        Returns:
            解析后的招生信息列表
        """
        # 辅助函数：如果值为空则返回 'NA'
        def get_value_or_na(value, default=''):
            result = value if value is not None else default
            return result if result else 'NA'
        
        admission_list = []
        
        for item in batch_list:
            # 提取分数和排名
            min_score = item.get('minScore', '')
            min_rank = item.get('minRank') or item.get('minOrder', '')
            
            # 处理分数：如果是浮点数，转换为整数字符串
            if isinstance(min_score, (int, float)):
                min_score = str(int(min_score))
            elif min_score:
                min_score = str(min_score)
            else:
                min_score = 'NA'
            
            # 处理排名：如果是数字，转换为字符串
            if isinstance(min_rank, (int, float)):
                min_rank = str(int(min_rank))
            elif min_rank:
                min_rank = str(min_rank)
            else:
                min_rank = 'NA'
            
            admission_info = {
                '年份': str(item.get('nf', year)) if item.get('nf', year) else 'NA',
                '学校': self.school_name if self.school_name else 'NA',
                '科类': get_value_or_na(item.get('klmc')),
                '批次': '普通批',  # 普通批录取情况
                '专业': 'NA',  # 普通批不包含专业信息
                '最低分': min_score,
                '最低分排名': min_rank,
                '全国统一招生代码': self.school_code if self.school_code else 'NA',
                '招生类型': get_value_or_na(item.get('zslx'), '普通类'),
                '生源地': get_value_or_na(item.get('ssmc', province))
            }
            admission_list.append(admission_info)
        
        return admission_list
    
    def parse_major_data(self, major_list: List[Dict], year: int, province: str) -> List[Dict]:
        """
        解析分专业录取情况数据
        
        Args:
            major_list: 分专业录取数据列表
            year: 年份
            province: 省份
            
        Returns:
            解析后的招生信息列表
        """
        # 辅助函数：如果值为空则返回 'NA'
        def get_value_or_na(value, default=''):
            result = value if value is not None else default
            return result if result else 'NA'
        
        admission_list = []
        
        for item in major_list:
            # 提取分数
            min_score = item.get('minScore', '')
            
            # 处理分数：如果是浮点数，转换为整数字符串
            if isinstance(min_score, (int, float)):
                min_score = str(int(min_score))
            elif min_score:
                min_score = str(min_score)
            else:
                min_score = 'NA'
            
            admission_info = {
                '年份': str(item.get('nf', year)) if item.get('nf', year) else 'NA',
                '学校': self.school_name if self.school_name else 'NA',
                '科类': get_value_or_na(item.get('klmc')),
                '批次': '普通批',  # 默认批次
                '专业': get_value_or_na(item.get('zymc')),
                '最低分': min_score,
                '最低分排名': 'NA',  # 分专业数据中没有排名信息
                '全国统一招生代码': self.school_code if self.school_code else 'NA',
                '招生类型': get_value_or_na(item.get('zslx'), '普通类'),
                '生源地': get_value_or_na(item.get('ssmc', province))
            }
            admission_list.append(admission_info)
        
        return admission_list
    
    def crawl_by_year_and_province(self, year: int, province: str = '') -> List[Dict]:
        """
        爬取指定年份和省份的招生信息
        
        Args:
            year: 年份
            province: 省份，如果为空则爬取所有省份
            
        Returns:
            招生信息列表
        """
        all_data = []
        
        # 构建请求参数
        params = {
            'zsnf': str(year),  # 招生年份
            'ssmc': province if province else '',  # 省市名称
            'klmc': '',  # 科类名称，空表示全部
            'sex': '',  # 性别
            'campus': '',  # 校区
            'zslx': ''  # 招生类型
        }
        
        logger.info(f"正在爬取 {year}年 {province if province else '全部省份'} 的招生信息...")
        
        # 获取数据
        data = self.get_admission_data(params)
        if not data:
            logger.warning(f"未获取到 {year}年 {province} 的数据")
            return []
        
        # 解析普通批录取情况
        batch_list = data.get('zsSsgradeList', [])
        if batch_list:
            batch_data = self.parse_batch_data(batch_list, year, province)
            all_data.extend(batch_data)
            logger.info(f"普通批录取情况: {len(batch_data)} 条")
        
        # 解析分专业录取情况
        major_list = data.get('sszygradeList', [])
        if major_list:
            major_data = self.parse_major_data(major_list, year, province)
            all_data.extend(major_data)
            logger.info(f"分专业录取情况: {len(major_data)} 条")
        
        # 避免请求过快
        time.sleep(0.5)
        
        return all_data
    
    def crawl_by_year(self, year: int, provinces: List[str] = None) -> List[Dict]:
        """
        爬取指定年份的招生信息
        
        Args:
            year: 年份
            provinces: 省份列表，如果为None则获取所有可用省份
            
        Returns:
            招生信息列表
        """
        all_data = []
        
        # 获取筛选参数，获取可用的省份列表
        filter_params = self.get_filter_params()
        if filter_params:
            # 从筛选参数中提取省份列表
            filter_list = filter_params.get('ssmc_nf_klmc_sex_campus_zslx_list', {})
            available_provinces = []
            
            # 尝试从数据中提取省份列表
            if isinstance(filter_list, dict):
                ssmc_list = filter_list.get('ssmc', [])
                if ssmc_list:
                    available_provinces = [item.get('name', '') for item in ssmc_list if item.get('name')]
            
            if not available_provinces:
                # 如果无法获取，使用默认省份列表
                available_provinces = [
                    '北京', '天津', '河北', '山西', '内蒙古', '辽宁', '吉林', '黑龙江',
                    '上海', '江苏', '浙江', '安徽', '福建', '江西', '山东', '河南',
                    '湖北', '湖南', '广东', '广西', '海南', '重庆', '四川', '贵州',
                    '云南', '西藏', '陕西', '甘肃', '青海', '宁夏', '新疆'
                ]
        else:
            # 如果无法获取筛选参数，使用默认省份列表
            available_provinces = [
                '北京', '天津', '河北', '山西', '内蒙古', '辽宁', '吉林', '黑龙江',
                '上海', '江苏', '浙江', '安徽', '福建', '江西', '山东', '河南',
                '湖北', '湖南', '广东', '广西', '海南', '重庆', '四川', '贵州',
                '云南', '西藏', '陕西', '甘肃', '青海', '宁夏', '新疆'
            ]
        
        # 如果指定了省份列表，使用指定的
        if provinces:
            available_provinces = provinces
        
        # 如果province列表为空，尝试爬取所有省份
        if not available_provinces:
            # 直接爬取全部数据（不指定省份）
            data = self.crawl_by_year_and_province(year, '')
            all_data.extend(data)
        else:
            # 逐个省份爬取
            for province in available_provinces:
                if province:  # 确保省份名称不为空
                    data = self.crawl_by_year_and_province(year, province)
                    all_data.extend(data)
        
        logger.info(f"共爬取 {year}年 {len(all_data)} 条招生信息")
        return all_data
    
    def crawl_current_year(self) -> List[Dict]:
        """
        爬取当前年份的招生信息
        
        Returns:
            招生信息列表
        """
        current_year = datetime.now().year
        return self.crawl_by_year(current_year)

