"""
清华大学招生信息爬虫
专门用于爬取清华大学历年招生信息
通过解析HTML页面获取数据
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


class TsinghuaCrawler:
    """清华大学招生信息爬虫类"""
    
    def __init__(self):
        self.base_url = 'https://join-tsinghua.edu.cn'
        self.list_url = 'https://join-tsinghua.edu.cn/xxgk/lnlqfsx.htm'
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
        self.school_name = '清华大学'
        self.school_code = '10003'  # 清华大学招生代码
    
    def _get_url(self, path: str) -> str:
        """构建完整URL"""
        if path.startswith('http'):
            return path
        if path.startswith('/'):
            return self.base_url + path
        return urljoin(self.base_url, path)
    
    def get_year_links(self) -> List[Dict[str, str]]:
        """
        从列表页面获取所有年份的链接
        
        Returns:
            包含年份和链接的字典列表，格式：[{'year': '2024', 'url': '...'}, ...]
        """
        try:
            response = self.session.get(self.list_url, timeout=30)
            response.encoding = 'utf-8'
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            year_links = []
            
            # 查找包含年份链接的元素
            # 通常这些链接在列表或特定的div中
            # 根据实际页面结构调整选择器
            
            # 尝试多种选择器来查找链接
            # 方法1: 查找所有链接
            links = soup.find_all('a', href=True)
            
            # 方法2: 查找特定区域（如果有列表结构）
            content_area = soup.find('div', class_=re.compile(r'content|list|main', re.I))
            if content_area:
                links.extend(content_area.find_all('a', href=True))
            
            for link in links:
                text = link.get_text(strip=True)
                href = link.get('href', '')
                
                # 匹配年份链接，例如："清华大学2024年各省各批次录取分数线"
                # 也匹配 "2024-07-13 清华大学2024年各省各批次录取分数线" 这种格式
                year_match = re.search(r'(\d{4})年', text)
                if year_match:
                    year = year_match.group(1)
                    # 构建完整URL
                    full_url = self._get_url(href)
                    
                    # 避免重复
                    if not any(item['year'] == year for item in year_links):
                        year_links.append({
                            'year': year,
                            'url': full_url,
                            'title': text
                        })
                        logger.info(f"找到 {year} 年链接: {full_url}")
            
            # 按年份排序（降序）
            year_links.sort(key=lambda x: int(x['year']), reverse=True)
            logger.info(f"共找到 {len(year_links)} 个年份的链接")
            
            return year_links
            
        except Exception as e:
            logger.error(f"获取年份链接时出错: {e}")
            return []
    
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
            
            # 查找内容区域（清华大学页面使用vsb_content）
            content_div = soup.find('div', id='vsb_content')
            if not content_div:
                content_div = soup.find('div', class_='v_news_content')
            
            if content_div:
                logger.info("找到内容区域，开始解析段落格式数据")
                # 使用专门的段落解析方法
                return self._parse_paragraph_format(content_div, year)
            
            # 如果没找到内容区域，尝试查找表格（兼容其他格式）
            tables = soup.find_all('table')
            logger.info(f"找到 {len(tables)} 个table标签")
            
            if tables:
                # 使用表格解析方法
                return self._parse_table_format(soup, year, tables)
            
            # 如果都没有，尝试文本解析
            logger.warning("未找到标准格式，尝试文本解析")
            main_content = soup.find('div', id=re.compile(r'content|main|article', re.I))
            if not main_content:
                main_content = soup.find('div', class_=re.compile(r'content|main|article|text|body', re.I))
            
            if main_content:
                logger.info(f"找到主要内容区域，包含 {len(main_content.get_text())} 个字符")
                text_data = self._parse_text_content(main_content, year)
                if text_data:
                    logger.info(f"从文本内容中解析出 {len(text_data)} 条记录")
                    return text_data
            
            logger.error("无法找到可解析的数据格式")
            return []
            
        except Exception as e:
            logger.error(f"解析 {year} 年页面时出错: {e}")
            return []
    
    def _parse_paragraph_format(self, content_div, year: int) -> List[Dict]:
        """
        解析段落格式的录取分数线数据（清华大学格式）
        支持多种格式：
        1. 每个省份一行：省份：科类/专业 分数；科类/专业 分数；
        2. 多个省份一行：省份1：分数分；省份2：分数分；...
        
        Args:
            content_div: 包含内容的div元素
            year: 年份
            
        Returns:
            解析后的招生信息列表
        """
        admission_list = []
        current_batch = '普通批'  # 默认批次
        current_major_hint = ''  # 从批次标题中提取的专业提示（如"理科定向"、"马克思主义理论"）
        
        # 省份列表（按长度降序排列，避免短名称匹配到长名称的一部分）
        provinces = [
            '内蒙古', '黑龙江', '新疆', '西藏', '宁夏', '青海', '甘肃', '陕西',
            '云南', '贵州', '四川', '重庆', '海南', '广西', '广东', '湖南',
            '湖北', '河南', '山东', '江西', '福建', '安徽', '浙江', '江苏',
            '上海', '吉林', '辽宁', '河北', '山西', '天津', '北京'
        ]
        
        # 查找所有段落
        paragraphs = content_div.find_all('p')
        logger.info(f"找到 {len(paragraphs)} 个段落")
        
        for p in paragraphs:
            # 先移除HTML标签，但保留文本内容
            text = p.get_text(separator=' ', strip=True)
            if not text:
                continue
            
            # 检查是否是批次标题（包含"批次"或"分数线"）
            strong_tag = p.find('strong')
            if strong_tag:
                batch_text = strong_tag.get_text(strip=True)
                if '批次' in batch_text or '分数线' in batch_text or '统招批' in batch_text or '定向批' in batch_text:
                    # 去掉中括号和特殊字符
                    batch_text_clean = batch_text.replace('【', '').replace('】', '').replace('[', '').replace(']', '').strip()
                    
                    # 提取批次名称
                    if '提前批次' in batch_text_clean or '提前批' in batch_text_clean:
                        current_batch = '提前批'
                        # 从标题中提取专业提示
                        if '理科定向' in batch_text_clean:
                            current_major_hint = '理科定向'
                        elif '马克思主义理论' in batch_text_clean:
                            current_major_hint = '马克思主义理论'
                        elif '艺术史论' in batch_text_clean:
                            current_major_hint = '艺术史论'
                        else:
                            current_major_hint = ''
                    elif '国家专项' in batch_text_clean:
                        current_batch = '国家专项计划'
                        current_major_hint = ''
                    elif '定向批' in batch_text_clean:
                        current_batch = '提前批'  # 定向批属于提前批
                        current_major_hint = '定向生'
                    elif '本科一批' in batch_text_clean or '一批次' in batch_text_clean or '统招批' in batch_text_clean:
                        current_batch = '本科一批'
                        current_major_hint = ''
                    elif '本科二批' in batch_text_clean or '二批次' in batch_text_clean:
                        current_batch = '本科二批'
                        current_major_hint = ''
                    else:
                        # 提取批次名称，去掉"录取分数线"等后缀
                        current_batch = batch_text_clean.replace('录取分数线', '').replace('：', '').replace(':', '').strip()
                        current_major_hint = ''
                    logger.info(f"识别到批次: {current_batch}, 专业提示: {current_major_hint}")
                    continue
            
            # 处理文本：移除HTML标签，统一格式
            # 处理可能的小数分数（如690.139 -> 690）
            text = re.sub(r'(\d+)\.\d+', r'\1', text)
            
            # 解析数据行
            # 格式1：每个省份一行，包含多个科类/专业
            # 格式2：多个省份一行，每个省份只有一个分数
            
            # 匹配省份和分数
            # 格式1：省份：科类/专业 分数；科类/专业 分数；（多个分数项）
            # 格式2：省份：分数分（单个分数，可能多个省份一行或每个省份一行）
            
            # 先尝试格式1：包含多个分数项（有分号分隔）
            format1_matched = False
            if '；' in text or ';' in text:
                # 格式1：每个省份有多个分数项
                # 省份：科类/专业 分数；科类/专业 分数；
                province_pattern = rf'({"|".join(provinces)})(?:省|市|自治区|特别行政区)?[：:]([^；；]+?)(?=({"|".join(provinces)})[：:]|$)'
                matches = list(re.finditer(province_pattern, text))
                
                if matches:
                    format1_matched = True
                    for match in matches:
                        province_name = match.group(1)
                        data_part = match.group(2)
                        
                        # 解析该省份的多个分数项
                        # 匹配：科类/专业名称 + 数字 + 分
                        items = re.findall(r'([^；；\d]+?)(\d+)\s*分', data_part)
                        
                        if items:
                            for item in items:
                                category_or_major = item[0].strip()
                                score = item[1]
                                
                                # 如果没有科类/专业信息，使用批次标题中的提示
                                if not category_or_major or category_or_major in ['：', ':', '，', ',', '论']:
                                    category_or_major = current_major_hint
                                
                                admission_info = self._create_admission_info(
                                    year, province_name, category_or_major, score, current_batch
                                )
                                if admission_info:
                                    admission_list.append(admission_info)
            
            # 格式2：单个分数（没有分号，或格式1没有匹配到）
            # 匹配：省份：分数分（可能多个省份一行，或每个省份一行）
            if not format1_matched:
                province_score_pattern = rf'({"|".join(provinces)})(?:省|市|自治区|特别行政区)?[：:]\s*(\d+)\s*分'
                matches2 = re.findall(province_score_pattern, text)
                
                if matches2:
                    # 格式2：每个省份只有一个分数
                    for province_name, score in matches2:
                        # 使用批次标题中的专业提示
                        category_or_major = current_major_hint
                        
                        admission_info = self._create_admission_info(
                            year, province_name, category_or_major, score, current_batch
                        )
                        if admission_info:
                            admission_list.append(admission_info)
        
        logger.info(f"从段落格式解析出 {len(admission_list)} 条记录")
        return admission_list
    
    def _create_admission_info(self, year: int, province_name: str, category_or_major: str, 
                                score: str, current_batch: str) -> Optional[Dict]:
        """
        创建招生信息字典
        
        Args:
            year: 年份
            province_name: 省份名称
            category_or_major: 科类或专业名称
            score: 分数
            current_batch: 批次
            
        Returns:
            招生信息字典，如果无效则返回None
        """
        # 标准化省份名称（移除后缀）
        province_name = province_name.replace('省', '').replace('市', '').replace('自治区', '').replace('特别行政区', '').strip()
        
        if not province_name or not score:
            return None
        
        # 判断是科类还是专业
        category = 'NA'
        major = 'NA'
        admission_type = '统招'
        
        category_or_major = category_or_major.strip()
        
        # 常见的科类关键词
        if '理科' in category_or_major or '理工' in category_or_major:
            category = '理工'
            if '定向' in category_or_major:
                major = '定向生'
                admission_type = '定向生'
        elif '文科' in category_or_major or '文史' in category_or_major:
            category = '文史'
        elif '物理' in category_or_major or '物化' in category_or_major:
            category = '综合改革'
            if '物化' in category_or_major:
                major = '物化组'
            elif '物理' in category_or_major:
                major = '物理组'
        elif '历史' in category_or_major:
            category = '综合改革'
            major = '历史组'
        elif '不限' in category_or_major:
            category = '综合改革'
            major = '不限组'
        elif '通用' in category_or_major:
            category = '综合改革'
            major = '通用组'
        elif '医学' in category_or_major or '临床医学' in category_or_major:
            category = '综合改革'
            major = '医学类'
        elif '马克思主义理论' in category_or_major:
            major = '马克思主义理论'
            category = '综合改革'
        elif '艺术史论' in category_or_major:
            major = '艺术史论'
            category = '艺术类'
        elif category_or_major:
            # 可能是专业名称或其他描述
            major = category_or_major
            # 尝试推断科类
            if '定向' in category_or_major:
                admission_type = '定向生'
                category = '理工'  # 定向生通常是理科
        
        # 判断招生类型
        if '定向' in category_or_major or admission_type == '定向生':
            admission_type = '定向生'
        elif '国家专项' in current_batch:
            admission_type = '国家专项计划'
        
        return {
            '年份': str(year),
            '学校': self.school_name,
            '_985': '1',
            '_211': '1',
            '双一流': '1',
            '科类': category,
            '批次': current_batch,
            '专业': major,
            '最低分': score,
            '最低分排名': 'NA',
            '全国统一招生代码': self.school_code,
            '招生类型': admission_type,
            '生源地': province_name
        }
    
    def _parse_table_format(self, soup, year: int, tables) -> List[Dict]:
        """
        解析表格格式的数据（备用方法）
        
        Args:
            soup: BeautifulSoup对象
            year: 年份
            tables: 表格列表
            
        Returns:
            解析后的招生信息列表
        """
        # 这里可以保留原来的表格解析逻辑，如果需要的话
        logger.warning("表格格式解析暂未实现")
        return []
    
    def _parse_text_content(self, element, year: int) -> List[Dict]:
        """
        从文本内容中解析录取分数线数据（备用方法）
        
        Args:
            element: BeautifulSoup元素或soup对象
            year: 年份
            
        Returns:
            解析后的招生信息列表
        """
        admission_list = []
        
        try:
            # 获取所有文本内容
            text = element.get_text(separator='\n', strip=True)
            lines = text.split('\n')
            
            # 辅助函数：如果值为空则返回 'NA'
            def get_value_or_na(value, default=''):
                if value is None:
                    return default if default else 'NA'
                value_str = str(value).strip()
                return value_str if value_str else (default if default else 'NA')
            
            # 省份列表
            provinces = [
                '北京', '天津', '河北', '山西', '内蒙古', '辽宁', '吉林', '黑龙江',
                '上海', '江苏', '浙江', '安徽', '福建', '江西', '山东', '河南',
                '湖北', '湖南', '广东', '广西', '海南', '重庆', '四川', '贵州',
                '云南', '西藏', '陕西', '甘肃', '青海', '宁夏', '新疆'
            ]
            
            # 尝试从文本中提取省份和分数
            current_province = None
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # 检查是否是省份行
                for province in provinces:
                    if province in line:
                        current_province = province
                        # 尝试从同一行提取分数
                        score_match = re.search(r'(\d{3,})', line)
                        if score_match:
                            score = score_match.group(1)
                            admission_info = {
                                '年份': str(year),
                                '学校': self.school_name,
                                '_985': '1',
                                '_211': '1',
                                '双一流': '1',
                                '科类': 'NA',
                                '批次': '普通批',
                                '专业': 'NA',
                                '最低分': score,
                                '最低分排名': 'NA',
                                '全国统一招生代码': self.school_code,
                                '招生类型': '统招',
                                '生源地': current_province
                            }
                            admission_list.append(admission_info)
                        break
                
                # 如果当前有省份，尝试从行中提取分数
                if current_province:
                    score_match = re.search(r'(\d{3,})', line)
                    if score_match and len(score_match.group(1)) >= 3:  # 至少3位数
                        score = score_match.group(1)
                        # 检查是否已经添加过这个省份的记录
                        existing = any(item['生源地'] == current_province and item['最低分'] == score 
                                     for item in admission_list)
                        if not existing:
                            admission_info = {
                                '年份': str(year),
                                '学校': self.school_name,
                                '_985': '1',
                                '_211': '1',
                                '双一流': '1',
                                '科类': 'NA',
                                '批次': '普通批',
                                '专业': 'NA',
                                '最低分': score,
                                '最低分排名': 'NA',
                                '全国统一招生代码': self.school_code,
                                '招生类型': '统招',
                                '生源地': current_province
                            }
                            admission_list.append(admission_info)
            
            return admission_list
            
        except Exception as e:
            logger.error(f"从文本内容解析数据时出错: {e}")
            return []
    
    def crawl_by_year(self, year: int) -> List[Dict]:
        """
        爬取指定年份的招生信息
        
        Args:
            year: 年份
            
        Returns:
            招生信息列表
        """
        # 获取所有年份链接
        year_links = self.get_year_links()
        
        # 查找指定年份的链接
        target_link = None
        for link_info in year_links:
            if int(link_info['year']) == year:
                target_link = link_info
                break
        
        if not target_link:
            logger.warning(f"未找到 {year} 年的链接")
            return []
        
        # 解析该年份的页面
        data = self.parse_score_page(target_link['url'], year)
        
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
        year_links = self.get_year_links()
        
        for link_info in year_links:
            year = int(link_info['year'])
            logger.info(f"正在爬取 {year} 年的数据...")
            
            year_data = self.parse_score_page(link_info['url'], year)
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

