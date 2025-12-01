"""
北京大学招生信息爬虫
专门用于爬取北京大学历年招生信息
通过解析HTML表格获取数据
"""
import requests
import re
import time
import logging
from typing import List, Dict, Optional
from datetime import datetime
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PKUCrawler:
    """北京大学招生信息爬虫类"""
    
    def __init__(self):
        self.base_url = 'https://www.gotopku.cn'
        # URL格式：/programa/admitline/7/{year}.html
        # 默认使用当前年份
        current_year = datetime.now().year
        self.list_url = f'https://www.gotopku.cn/programa/admitline/7/{current_year}.html'
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        self.school_name = '北京大学'
        self.school_code = '10001'  # 北京大学招生代码
        
        # URL格式：/programa/admitline/7/{year}.html
        # 其中7是固定的ID，年份直接作为路径的一部分
        self.base_path = '/programa/admitline/7'
    
    def _get_url(self, path: str) -> str:
        """构建完整URL"""
        if path.startswith('http'):
            return path
        if path.startswith('/'):
            return self.base_url + path
        return urljoin(self.base_url, path)
    
    def get_available_years(self) -> List[int]:
        """
        从页面获取可用的年份列表
        
        Returns:
            可用年份列表
        """
        try:
            # 使用当前年份的URL作为入口
            current_year = datetime.now().year
            url = f'{self.base_url}{self.base_path}/{current_year}.html'
            response = self.session.get(url, timeout=30)
            response.encoding = 'utf-8'
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            years = []
            
            # 查找年份选择器（通常在select或链接中）
            # 根据实际页面结构调整
            year_select = soup.find('select', {'name': 'year'}) or soup.find('select', id='year')
            if year_select:
                options = year_select.find_all('option')
                for option in options:
                    year_text = option.get_text(strip=True)
                    year_match = re.search(r'(\d{4})', year_text)
                    if year_match:
                        years.append(int(year_match.group(1)))
            
            # 如果没有找到select，尝试从链接中提取
            if not years:
                # 查找所有年份链接，格式可能是 /programa/admitline/7/{year}.html
                year_links = soup.find_all('a', href=re.compile(r'admitline/7/\d{4}\.html'))
                for link in year_links:
                    href = link.get('href', '')
                    year_match = re.search(r'admitline/7/(\d{4})\.html', href)
                    if year_match:
                        years.append(int(year_match.group(1)))
            
            if not years:
                # 如果无法获取，使用默认年份列表（2015-2025）
                years = list(range(2015, datetime.now().year + 2))
            
            years.sort(reverse=True)
            logger.info(f"找到可用年份: {years}")
            return years
            
        except Exception as e:
            logger.error(f"获取可用年份时出错: {e}")
            # 返回默认年份列表
            return list(range(2015, datetime.now().year + 2))
    
    def get_year_url(self, year: int) -> str:
        """
        获取指定年份的URL
        
        Args:
            year: 年份
            
        Returns:
            年份对应的URL
        """
        # URL格式：/programa/admitline/7/{year}.html
        return f'{self.base_url}{self.base_path}/{year}.html'
    
    def parse_score_page(self, url: str, year: int) -> List[Dict]:
        """
        解析指定年份的录取分数线页面
        
        Args:
            url: 页面URL
            year: 年份
            
        Returns:
            解析后的招生信息列表
        """
        try:
            response = self.session.get(url, timeout=30)
            response.encoding = 'utf-8'
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            admission_list = []
            
            logger.info(f"开始解析 {year} 年页面，URL: {url}")
            
            # 查找表格
            table = soup.find('table')
            if not table:
                logger.warning(f"{year}年页面未找到表格")
                return []
            
            # 查找表头
            headers = []
            header_row = table.find('tr')
            if header_row:
                header_cells = header_row.find_all(['th', 'td'])
                headers = [cell.get_text(strip=True) for cell in header_cells]
                logger.info(f"表头: {headers}")
            
            # 解析数据行
            rows = table.find_all('tr')[1:]  # 跳过表头
            logger.info(f"找到 {len(rows)} 行数据")
            
            for row in rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) < 2:
                    continue
                
                # 提取单元格文本
                cell_texts = [cell.get_text(strip=True) for cell in cells]
                
                # 根据表头映射数据
                province = ''
                category = ''  # 类别
                arts_score = ''  # 文科分数线
                science_score = ''  # 理科分数线
                other_score = ''  # 其它分数线
                
                # 如果没有表头，尝试根据位置推断
                if headers:
                    for idx, header in enumerate(headers):
                        if idx < len(cell_texts):
                            value = cell_texts[idx]
                            
                            if '省份' in header or '省' in header:
                                province = value
                            elif '类别' in header:
                                category = value
                            elif '文科' in header:
                                arts_score = value
                            elif '理科' in header:
                                science_score = value
                            elif '其它' in header or '其他' in header:
                                other_score = value
                else:
                    # 根据位置推断（通常第一列是省份，第二列是类别，后面是分数）
                    if len(cell_texts) >= 1:
                        province = cell_texts[0]
                    if len(cell_texts) >= 2:
                        category = cell_texts[1]
                    if len(cell_texts) >= 3:
                        arts_score = cell_texts[2]
                    if len(cell_texts) >= 4:
                        science_score = cell_texts[3]
                    if len(cell_texts) >= 5:
                        other_score = cell_texts[4]
                
                # 清洗省份名称
                province = province.replace('省', '').replace('市', '').replace('自治区', '').replace('特别行政区', '').strip()
                
                # 处理分数数据
                # 如果分数是"-"或空，跳过
                def clean_score(score_str):
                    if not score_str or score_str == '-' or score_str == '—':
                        return None
                    # 提取数字
                    score_match = re.search(r'(\d+)', str(score_str))
                    if score_match:
                        return score_match.group(1)
                    return None
                
                # 创建记录
                # 如果有文科分数
                if arts_score and clean_score(arts_score):
                    score = clean_score(arts_score)
                    admission_info = self._create_admission_info(
                        year, province, category, score, '本科一批', '文史'
                    )
                    if admission_info:
                        admission_list.append(admission_info)
                
                # 如果有理科分数
                if science_score and clean_score(science_score):
                    score = clean_score(science_score)
                    admission_info = self._create_admission_info(
                        year, province, category, score, '本科一批', '理工'
                    )
                    if admission_info:
                        admission_list.append(admission_info)
                
                # 如果有其它分数（通常是综合改革）
                if other_score and clean_score(other_score):
                    score = clean_score(other_score)
                    # 根据类别判断科类
                    category_type = '综合改革'
                    if '物理' in category or '物化' in category:
                        category_type = '综合改革'
                    elif '历史' in category:
                        category_type = '综合改革'
                    elif '不限' in category:
                        category_type = '综合改革'
                    
                    admission_info = self._create_admission_info(
                        year, province, category, score, '本科一批', category_type
                    )
                    if admission_info:
                        admission_list.append(admission_info)
            
            logger.info(f"从 {year} 年页面解析出 {len(admission_list)} 条记录")
            return admission_list
            
        except Exception as e:
            logger.error(f"解析 {year} 年页面时出错: {e}")
            return []
    
    def _create_admission_info(self, year: int, province: str, category: str, 
                                score: str, batch: str, category_type: str) -> Optional[Dict]:
        """
        创建招生信息字典
        
        Args:
            year: 年份
            province: 省份名称
            category: 类别（专业组等）
            score: 分数
            batch: 批次
            category_type: 科类（文史、理工、综合改革）
            
        Returns:
            招生信息字典，如果无效则返回None
        """
        if not province or not score:
            return None
        
        # 处理专业字段
        major = 'NA'
        if category and category not in ['-', '—', '']:
            major = category
        
        return {
            '年份': str(year),
            '学校': self.school_name,
            '_985': '1',
            '_211': '1',
            '双一流': '1',
            '科类': category_type,
            '批次': batch,
            '专业': major,
            '最低分': score,
            '最低分排名': 'NA',
            '全国统一招生代码': self.school_code,
            '招生类型': '统招',
            '生源地': province
        }
    
    def crawl_by_year(self, year: int) -> List[Dict]:
        """
        爬取指定年份的招生信息
        
        Args:
            year: 年份
            
        Returns:
            招生信息列表
        """
        url = self.get_year_url(year)
        logger.info(f"正在爬取 {year} 年的数据，URL: {url}")
        
        data = self.parse_score_page(url, year)
        
        # 避免请求过快
        time.sleep(1)
        
        logger.info(f"共爬取 {year}年 {len(data)} 条招生信息")
        return data
    
    def crawl_all_years(self) -> List[Dict]:
        """
        爬取所有可用年份的招生信息
        
        Returns:
            所有年份的招生信息列表
        """
        all_data = []
        years = self.get_available_years()
        
        for year in years:
            logger.info(f"正在爬取 {year} 年的数据...")
            year_data = self.crawl_by_year(year)
            all_data.extend(year_data)
            
            # 避免请求过快
            time.sleep(1)
        
        logger.info(f"共爬取 {len(all_data)} 条招生信息")
        return all_data
    
    def crawl_current_year(self) -> List[Dict]:
        """
        爬取当前年份的招生信息
        
        Returns:
            招生信息列表
        """
        current_year = datetime.now().year
        return self.crawl_by_year(current_year)

