"""
华中科技大学招生信息爬虫
专门用于爬取华中科技大学历年招生信息
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


class HUSTCrawler:
    """华中科技大学招生信息爬虫类"""
    
    def __init__(self):
        self.base_url = 'https://zsb.hust.edu.cn'
        self.list_url = 'https://zsb.hust.edu.cn/bkzn/lqqk.htm'
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Referer': 'https://zsb.hust.edu.cn/'
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        self.school_name = '华中科技大学'
        self.school_code = '10487'  # 华中科技大学招生代码
    
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
            # 方法1: 查找所有链接
            links = soup.find_all('a', href=True)
            
            # 方法2: 查找特定区域（如果有列表结构）
            content_area = soup.find('div', class_=re.compile(r'content|list|main|news', re.I))
            if content_area:
                links.extend(content_area.find_all('a', href=True))
            
            # 方法3: 查找表格中的链接
            tables = soup.find_all('table')
            for table in tables:
                links.extend(table.find_all('a', href=True))
            
            for link in links:
                text = link.get_text(strip=True)
                href = link.get('href', '')
                
                # 匹配年份链接，例如："2024年录取情况"、"华中科技大学2024年录取分数线"
                # 也匹配 "2024-07-13 华中科技大学2024年各省各批次录取分数线" 这种格式
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
            
            # 如果没有找到链接，尝试从URL模式推断
            if not year_links:
                # 尝试查找包含年份的URL模式
                for link in links:
                    href = link.get('href', '')
                    # 匹配URL中的年份，如 /bkzn/lqqk/2024.htm
                    url_year_match = re.search(r'(\d{4})', href)
                    if url_year_match:
                        year = url_year_match.group(1)
                        full_url = self._get_url(href)
                        if not any(item['year'] == year for item in year_links):
                            year_links.append({
                                'year': year,
                                'url': full_url,
                                'title': link.get_text(strip=True) or f'{year}年录取情况'
                            })
            
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
            
            # 查找内容区域
            content_div = soup.find('div', id=re.compile(r'content|main|article|vsb', re.I))
            if not content_div:
                content_div = soup.find('div', class_=re.compile(r'content|main|article|text|body|vsb', re.I))
            
            # 优先查找表格
            tables = soup.find_all('table')
            if tables:
                logger.info(f"找到 {len(tables)} 个table标签，使用表格解析")
                return self._parse_table_format(soup, year, tables)
            
            # 如果有内容区域，尝试段落解析
            if content_div:
                logger.info("找到内容区域，尝试段落格式解析")
                return self._parse_paragraph_format(content_div, year)
            
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
    
    def _parse_table_format(self, soup, year: int, tables) -> List[Dict]:
        """
        解析表格格式的数据
        
        表格结构：
        - 表头：省份 | 科类批次 | 最高分 | 最低分
        - 分类标题行：如"艺术类"、"国家专项"、"高校专项"等（colspan=4）
        - 数据行：省份（可能有rowspan） | 专业/批次 | 最高分 | 最低分
        
        Args:
            soup: BeautifulSoup对象
            year: 年份
            tables: 表格列表
            
        Returns:
            解析后的招生信息列表
        """
        admission_list = []
        current_batch = '本科一批'  # 默认批次
        current_province = ''  # 当前省份（处理rowspan）
        
        # 批次关键词列表
        batch_keywords = ['国家专项', '高校专项', '艺术类', '提前批', '本科一批', '本科二批', '普通批']
        
        for table in tables:
            # 查找表头
            headers = []
            header_row = table.find('tr', class_='firstRow') or table.find('tr')
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
                
                # 检查是否是分类标题行（colspan=4或包含批次关键词）
                first_cell = cells[0]
                colspan = first_cell.get('colspan', '')
                first_cell_text = first_cell.get_text(strip=True)
                
                # 如果是分类标题行
                if colspan == '4' or any(keyword in first_cell_text for keyword in batch_keywords):
                    # 更新当前批次
                    if '艺术类' in first_cell_text:
                        current_batch = '艺术类'
                    elif '国家专项' in first_cell_text:
                        current_batch = '国家专项计划'
                    elif '高校专项' in first_cell_text:
                        current_batch = '高校专项计划'
                    elif '提前批' in first_cell_text:
                        current_batch = '提前批'
                    elif '本科一批' in first_cell_text or '一批' in first_cell_text:
                        current_batch = '本科一批'
                    elif '本科二批' in first_cell_text or '二批' in first_cell_text:
                        current_batch = '本科二批'
                    elif '普通批' in first_cell_text:
                        current_batch = '普通批'
                    else:
                        # 尝试从文本中提取批次名称
                        current_batch = first_cell_text.replace('录取情况', '').replace('分数线', '').strip()
                        if not current_batch:
                            current_batch = '本科一批'
                    logger.info(f"识别到批次: {current_batch}")
                    current_province = ''  # 重置省份
                    continue
                
                # 解析数据行
                # 列结构：省份 | 科类批次 | 最高分 | 最低分
                cell_texts = []
                cell_index = 0
                
                for cell in cells:
                    cell_text = cell.get_text(strip=True)
                    rowspan = cell.get('rowspan', '')
                    
                    # 第一列：省份（可能有rowspan）
                    if cell_index == 0:
                        if cell_text and not any(keyword in cell_text for keyword in batch_keywords):
                            current_province = cell_text
                        cell_texts.append(current_province)
                    else:
                        cell_texts.append(cell_text)
                    
                    # 如果当前单元格没有rowspan，移动到下一列
                    if not rowspan or rowspan == '1':
                        cell_index += 1
                
                # 确保有足够的列
                while len(cell_texts) < 4:
                    cell_texts.append('')
                
                # 提取数据
                province = cell_texts[0] if len(cell_texts) > 0 else ''
                category_batch_col = cell_texts[1] if len(cell_texts) > 1 else ''  # 科类批次列
                max_score = cell_texts[2] if len(cell_texts) > 2 else ''  # 最高分
                min_score = cell_texts[3] if len(cell_texts) > 3 else ''  # 最低分
                
                # 清洗省份名称
                province = province.replace('省', '').replace('市', '').replace('自治区', '').replace('特别行政区', '').strip()
                # 处理特殊省份名称
                if '（' in province:
                    province = province.split('（')[0]
                if '汉族' in province or '少数民族' in province:
                    province = province.replace('（汉族）', '').replace('（少数民族）', '').strip()
                
                # 判断"科类批次"列是专业还是批次
                major = 'NA'
                batch = current_batch
                
                # 检查是否是批次名称
                if any(keyword in category_batch_col for keyword in batch_keywords):
                    # 是批次名称
                    if '国家专项' in category_batch_col:
                        batch = '国家专项计划'
                    elif '高校专项' in category_batch_col:
                        batch = '高校专项计划'
                    elif '艺术类' in category_batch_col:
                        batch = '艺术类'
                    else:
                        batch = category_batch_col
                    major = 'NA'
                else:
                    # 是专业名称
                    major = category_batch_col
                    batch = current_batch
                
                # 处理分数（使用最低分）
                def clean_score(score_str):
                    if not score_str or score_str == '-' or score_str == '—' or score_str == 'NA':
                        return None
                    # 提取数字（包括小数）
                    score_match = re.search(r'(\d+(?:\.\d+)?)', str(score_str))
                    if score_match:
                        score_value = float(score_match.group(1))
                        # 如果是小数，转换为整数（去掉小数部分）
                        return str(int(score_value))
                    return None
                
                # 从专业名称中提取科类信息
                category_type = self._extract_category_from_major(major)
                
                # 创建记录
                if province and min_score and clean_score(min_score):
                    score_value = clean_score(min_score)
                    admission_info = self._create_admission_info(
                        year, province, category_type, score_value, batch, major, 'NA'
                    )
                    if admission_info:
                        admission_list.append(admission_info)
        
        logger.info(f"从表格格式解析出 {len(admission_list)} 条记录")
        return admission_list
    
    def _extract_category_from_major(self, major: str) -> str:
        """
        从专业名称中提取科类信息
        
        Args:
            major: 专业名称
            
        Returns:
            科类：'理工'、'文史'、'综合改革'、'艺术类'、'NA'
        """
        if not major or major == 'NA':
            return 'NA'
        
        major_lower = major.lower()
        
        # 艺术类专业
        art_keywords = ['设计学', '音乐表演', '播音与主持', '舞蹈表演', '艺术']
        if any(keyword in major for keyword in art_keywords):
            return '艺术类'
        
        # 物理类/历史类（新高考）
        if '物理' in major or '物化' in major:
            return '综合改革'
        if '历史' in major:
            return '综合改革'
        
        # 理科/文科
        if '理科' in major or '理工' in major:
            return '理工'
        if '文科' in major or '文史' in major:
            return '文史'
        
        # 默认返回NA
        return 'NA'
    
    def _parse_paragraph_format(self, content_div, year: int) -> List[Dict]:
        """
        解析段落格式的录取分数线数据
        
        Args:
            content_div: 包含内容的div元素
            year: 年份
            
        Returns:
            解析后的招生信息列表
        """
        admission_list = []
        current_batch = '本科一批'  # 默认批次
        
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
            text = p.get_text(separator=' ', strip=True)
            if not text:
                continue
            
            # 检查是否是批次标题
            strong_tag = p.find('strong')
            if strong_tag:
                batch_text = strong_tag.get_text(strip=True)
                if '批次' in batch_text or '分数线' in batch_text:
                    batch_text_clean = batch_text.replace('【', '').replace('】', '').replace('[', '').replace(']', '').strip()
                    
                    if '提前批次' in batch_text_clean or '提前批' in batch_text_clean:
                        current_batch = '提前批'
                    elif '国家专项' in batch_text_clean:
                        current_batch = '国家专项计划'
                    elif '本科一批' in batch_text_clean or '一批次' in batch_text_clean:
                        current_batch = '本科一批'
                    elif '本科二批' in batch_text_clean or '二批次' in batch_text_clean:
                        current_batch = '本科二批'
                    else:
                        current_batch = batch_text_clean.replace('录取分数线', '').replace('：', '').replace(':', '').strip()
                    logger.info(f"识别到批次: {current_batch}")
                    continue
            
            # 处理文本：移除HTML标签，统一格式
            text = re.sub(r'(\d+)\.\d+', r'\1', text)
            
            # 匹配省份和分数
            # 格式1：省份：科类/专业 分数；科类/专业 分数；（多个分数项）
            # 格式2：省份：分数分（单个分数）
            
            # 先尝试格式1：包含多个分数项（有分号分隔）
            if '；' in text or ';' in text:
                province_pattern = rf'({"|".join(provinces)})(?:省|市|自治区|特别行政区)?[：:]([^；；]+?)(?=({"|".join(provinces)})[：:]|$)'
                matches = list(re.finditer(province_pattern, text))
                
                if matches:
                    for match in matches:
                        province_name = match.group(1)
                        data_part = match.group(2)
                        
                        # 解析该省份的多个分数项
                        items = re.findall(r'([^；；\d]+?)(\d+)\s*分', data_part)
                        
                        if items:
                            for item in items:
                                category_or_major = item[0].strip()
                                score = item[1]
                                
                                category_type = self._extract_category_from_major(category_or_major)
                                admission_info = self._create_admission_info(
                                    year, province_name, category_type, score, current_batch, category_or_major, 'NA'
                                )
                                if admission_info:
                                    admission_list.append(admission_info)
            
            # 格式2：单个分数
            province_score_pattern = rf'({"|".join(provinces)})(?:省|市|自治区|特别行政区)?[：:]\s*(\d+)\s*分'
            matches2 = re.findall(province_score_pattern, text)
            
            if matches2:
                for province_name, score in matches2:
                    admission_info = self._create_admission_info(
                        year, province_name, 'NA', score, current_batch, 'NA', 'NA'
                    )
                    if admission_info:
                        admission_list.append(admission_info)
        
        logger.info(f"从段落格式解析出 {len(admission_list)} 条记录")
        return admission_list
    
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
            text = element.get_text(separator='\n', strip=True)
            lines = text.split('\n')
            
            provinces = [
                '北京', '天津', '河北', '山西', '内蒙古', '辽宁', '吉林', '黑龙江',
                '上海', '江苏', '浙江', '安徽', '福建', '江西', '山东', '河南',
                '湖北', '湖南', '广东', '广西', '海南', '重庆', '四川', '贵州',
                '云南', '西藏', '陕西', '甘肃', '青海', '宁夏', '新疆'
            ]
            
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
                                '批次': '本科一批',
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
                    if score_match and len(score_match.group(1)) >= 3:
                        score = score_match.group(1)
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
                                '批次': '本科一批',
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
    
    def _create_admission_info(self, year: int, province_name: str, category: str, 
                                score: str, batch: str, major: str = 'NA', rank: str = 'NA') -> Optional[Dict]:
        """
        创建招生信息字典
        
        Args:
            year: 年份
            province_name: 省份名称
            category: 科类（已提取）
            score: 分数
            batch: 批次
            major: 专业
            rank: 排名
            
        Returns:
            招生信息字典，如果无效则返回None
        """
        # 标准化省份名称（移除后缀）
        province_name = province_name.replace('省', '').replace('市', '').replace('自治区', '').replace('特别行政区', '').strip()
        
        # 处理特殊省份名称
        if '（' in province_name:
            province_name = province_name.split('（')[0]
        if '汉族' in province_name or '少数民族' in province_name:
            province_name = province_name.replace('（汉族）', '').replace('（少数民族）', '').strip()
        
        if not province_name or not score:
            return None
        
        # 判断招生类型
        admission_type = '统招'
        if '国家专项' in batch:
            admission_type = '国家专项计划'
        elif '高校专项' in batch:
            admission_type = '高校专项计划'
        elif '定向' in batch or '定向' in major:
            admission_type = '定向生'
        elif '艺术类' in batch or category == '艺术类':
            admission_type = '艺术类'
        
        # 如果科类是NA，尝试从批次或专业推断
        if category == 'NA':
            if '艺术类' in batch or '艺术' in major:
                category = '艺术类'
            elif '物理' in major or '物化' in major:
                category = '综合改革'
            elif '历史' in major:
                category = '综合改革'
        
        return {
            '年份': str(year),
            '学校': self.school_name,
            '_985': '1',
            '_211': '1',
            '双一流': '1',
            '科类': category,
            '批次': batch,
            '专业': major if major != 'NA' else 'NA',
            '最低分': score,
            '最低分排名': rank if rank != 'NA' else 'NA',
            '全国统一招生代码': self.school_code,
            '招生类型': admission_type,
            '生源地': province_name
        }
    
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

