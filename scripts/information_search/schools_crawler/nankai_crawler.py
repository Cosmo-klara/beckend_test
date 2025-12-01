"""
南开大学招生信息爬虫
专门用于爬取南开大学历年招生信息
通过API接口获取数据
"""
import requests
import json
import time
import logging
import re
from typing import List, Dict, Optional
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class NankaiCrawler:
    """南开大学招生信息爬虫类"""

    def __init__(self):
        self.base_url = 'https://lqcx.nankai.edu.cn'
        self.list_url = 'https://lqcx.nankai.edu.cn/zsw/lnfs.html'
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0',
            'Accept': '*/*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Connection': 'keep-alive',
            'Origin': 'https://lqcx.nankai.edu.cn',
            'Referer': 'https://lqcx.nankai.edu.cn/zsw/lnfs.html',
            'X-Requested-With': 'XMLHttpRequest',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'sec-ch-ua': '"Chromium";v="142", "Microsoft Edge";v="142", "Not_A Brand";v="99"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"'
        }
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
        self.school_name = '南开大学'
        self.school_code = '10055'  # 南开大学招生代码
        self.csrf_token = None  # CSRF token

        # 先访问主页面建立Session和Cookie
        self._init_session()

    def _get_url(self, path: str, add_timestamp: bool = False) -> str:
        """
        构建完整URL

        Args:
            path: URL路径
            add_timestamp: 是否添加时间戳参数（某些API需要）
        """
        if path.startswith('http'):
            url = path
        elif path.startswith('/'):
            url = self.base_url + path
        else:
            url = f"{self.base_url}/{path}"

        # 如果需要时间戳参数（如ajax_lnfs需要ts参数）
        if add_timestamp:
            import time
            timestamp = int(time.time() * 1000)
            separator = '&' if '?' in url else '?'
            url = f"{url}{separator}ts={timestamp}"

        return url

    def _init_session(self):
        """
        初始化Session，先访问主页面建立Cookie并获取CSRF Token
        """
        try:
            logger.info("初始化Session，访问主页面...")
            response = self.session.get(self.list_url, timeout=30)
            response.encoding = 'utf-8'
            response.raise_for_status()

            # 尝试从响应头获取CSRF Token
            csrf_token = response.headers.get('Csrf-Token') or response.headers.get('X-Csrf-Token')
            if csrf_token:
                self.csrf_token = csrf_token
                logger.info(f"获取到CSRF Token: {csrf_token[:10]}...")

            # 尝试从HTML中提取CSRF Token
            if not self.csrf_token:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(response.text, 'html.parser')
                # 查找meta标签中的csrf token
                csrf_meta = soup.find('meta', {'name': re.compile(r'csrf', re.I)})
                if csrf_meta:
                    self.csrf_token = csrf_meta.get('content', '')
                # 查找script中的csrf token
                if not self.csrf_token:
                    scripts = soup.find_all('script')
                    for script in scripts:
                        script_text = script.string or ''
                        csrf_match = re.search(r'csrf[_-]?token["\']?\s*[:=]\s*["\']([^"\']+)["\']', script_text, re.I)
                        if csrf_match:
                            self.csrf_token = csrf_match.group(1)
                            break

            logger.info("Session初始化成功")

            # 更新请求头为API请求格式
            self.session.headers.update(self.headers)

            # 尝试先调用获取筛选参数的API来获取CSRF Token
            if not self.csrf_token:
                try:
                    logger.info("尝试通过获取筛选参数API获取CSRF Token...")
                    filter_url = self._get_url('f/ajax_lnfs_param')
                    filter_headers = {
                        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                        'Referer': self.list_url,
                        'Origin': self.base_url,
                        'X-Requested-With': 'XMLHttpRequest'
                    }
                    filter_response = self.session.post(filter_url, headers=filter_headers, timeout=30)
                    # 从响应头获取CSRF Token
                    new_token = filter_response.headers.get('Csrf-Token') or filter_response.headers.get('X-Csrf-Token')
                    if new_token:
                        self.csrf_token = new_token
                        logger.info(f"通过API获取到CSRF Token: {new_token[:10]}...")
                except Exception as e:
                    logger.debug(f"通过API获取CSRF Token失败: {e}")
        except Exception as e:
            logger.warning(f"初始化Session时出错: {e}，将继续尝试")
            # 即使失败也更新请求头
            self.session.headers.update(self.headers)

    def get_filter_params(self) -> Optional[Dict]:
        """
        获取筛选参数（省份、年份、科类等）

        Returns:
            筛选参数字典，包含可选的省份、年份、科类列表
        """
        try:
            url = self._get_url('f/ajax_lnfs_param')
            logger.info(f"获取筛选参数，URL: {url}")

            # 确保使用正确的请求头
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'Referer': self.list_url,
                'Origin': self.base_url,
                'X-Requested-With': 'XMLHttpRequest'
            }

            # 添加CSRF Token到请求头（必须在请求头中）
            if self.csrf_token:
                headers['Csrf-Token'] = self.csrf_token

            # 添加时间戳请求头
            import time
            headers['X-Requested-Time'] = str(int(time.time() * 1000))

            # 更新Session的请求头（包括Sec-Fetch-*等）
            headers.update({k: v for k, v in self.headers.items() if k not in headers})

            response = self.session.post(url, headers=headers, timeout=30)

            # 从响应头获取CSRF Token（如果还没有）
            if not self.csrf_token:
                new_token = response.headers.get('Csrf-Token') or response.headers.get('X-Csrf-Token')
                if new_token:
                    self.csrf_token = new_token
                    logger.info(f"从响应获取CSRF Token: {new_token[:10]}...")

            # 如果返回403，尝试从响应头获取新的CSRF Token并重试
            if response.status_code == 403:
                new_token = response.headers.get('Csrf-Token') or response.headers.get('X-Csrf-Token')
                if new_token:
                    logger.info(f"从403响应获取新的CSRF Token: {new_token[:10]}...")
                    self.csrf_token = new_token
                    headers['Csrf-Token'] = self.csrf_token
                    headers['X-Csrf-Token'] = self.csrf_token
                    post_data['_token'] = self.csrf_token
                    post_data['csrf_token'] = self.csrf_token
                    # 重试一次
                    response = self.session.post(url, data=post_data, headers=headers, timeout=30)

            response.raise_for_status()

            data = response.json()
            if data.get('state') == 1:
                filter_data = data.get('data', {})
                logger.info("成功获取筛选参数")
                return filter_data
            else:
                logger.error(f"获取筛选参数失败: {data.get('msg', '未知错误')}")
                return None
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 403:
                logger.error(f"403错误：访问被拒绝。可能需要更新请求头或Cookie")
                logger.error(f"响应头: {dict(e.response.headers)}")
            logger.error(f"获取筛选参数时出错: {e}")
            return None
        except Exception as e:
            logger.error(f"获取筛选参数时出错: {e}")
            return None

    def get_admission_data(self, params: Dict) -> Optional[Dict]:
        """
        获取录取分数数据

        Args:
            params: 请求参数，包含省份(ssmc)、年份(zsnf)、科类(klmc)等

        Returns:
            包含录取分数数据的字典
        """
        try:
            # URL需要添加时间戳参数
            url = self._get_url('f/ajax_lnfs', add_timestamp=True)
            logger.debug(f"获取录取分数数据，URL: {url}, 参数: {params}")

            # 确保使用正确的请求头
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'Referer': self.list_url,
                'Origin': self.base_url,
                'X-Requested-With': 'XMLHttpRequest'
            }

            # 添加CSRF Token到请求头（必须在请求头中）
            if self.csrf_token:
                headers['Csrf-Token'] = self.csrf_token

            # 添加时间戳请求头（重要！）
            import time
            timestamp = int(time.time() * 1000)
            headers['X-Requested-Time'] = str(timestamp)

            # 更新Session的请求头（包括Sec-Fetch-*等）
            headers.update({k: v for k, v in self.headers.items() if k not in headers})

            response = self.session.post(url, data=params, headers=headers, timeout=30)

            # 从响应头获取CSRF Token（用于下次请求）
            new_token = response.headers.get('Csrf-Token') or response.headers.get('X-Csrf-Token')
            if new_token:
                self.csrf_token = new_token
                logger.debug(f"从响应获取CSRF Token: {new_token[:10]}...")

            # 如果返回403，尝试从响应头获取新的CSRF Token并重试
            if response.status_code == 403:
                new_token = response.headers.get('Csrf-Token') or response.headers.get('X-Csrf-Token')
                if new_token:
                    logger.info(f"从403响应获取新的CSRF Token: {new_token[:10]}...")
                    self.csrf_token = new_token
                    headers['Csrf-Token'] = self.csrf_token
                    # 更新时间戳
                    import time
                    timestamp = int(time.time() * 1000)
                    headers['X-Requested-Time'] = str(timestamp)
                    # 更新URL时间戳
                    url = self._get_url('f/ajax_lnfs', add_timestamp=True)
                    # 重试一次
                    response = self.session.post(url, data=params, headers=headers, timeout=30)

            response.raise_for_status()

            data = response.json()
            if data.get('state') == 1:
                result_data = data.get('data', {})
                logger.info("成功获取录取分数数据")
                return result_data
            else:
                logger.warning(f"获取数据失败: {data.get('msg', '未知错误')}")
                return None
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 403:
                logger.error(f"403错误：访问被拒绝。可能需要更新请求头或Cookie")
                logger.error(f"响应头: {dict(e.response.headers)}")
            logger.error(f"获取录取分数数据时出错: {e}")
            return None
        except Exception as e:
            logger.error(f"获取录取分数数据时出错: {e}")
            return None

    def parse_batch_data(self, batch_list: List[Dict], year: int, province: str) -> List[Dict]:
        """
        解析普通批录取情况数据（zsSsgradeList）

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
                '年份': str(item.get('nf', year)) if item.get('nf', year) else str(year),
                '学校': self.school_name if self.school_name else 'NA',
                '_985': '1',
                '_211': '1',
                '双一流': '1',
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
        解析分专业录取情况数据（sszygradeList）

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
                '年份': str(item.get('nf', year)) if item.get('nf', year) else str(year),
                '学校': self.school_name if self.school_name else 'NA',
                '_985': '1',
                '_211': '1',
                '双一流': '1',
                '科类': get_value_or_na(item.get('klmc')),
                '批次': '普通批',  # 默认批次
                '专业': get_value_or_na(item.get('zymc')),  # 专业名称
                '最低分': min_score,
                '最低分排名': 'NA',  # 分专业数据中没有排名信息
                '全国统一招生代码': self.school_code if self.school_code else 'NA',
                '招生类型': get_value_or_na(item.get('zslx'), '普通类'),
                '生源地': get_value_or_na(item.get('ssmc', province))
            }
            admission_list.append(admission_info)

        return admission_list

    def crawl_by_year_and_province(self, year: int, province: str = '', klmc: str = '', zslx: str = '') -> List[Dict]:
        """
        爬取指定年份和省份的招生信息

        Args:
            year: 年份
            province: 省份，如果为空则爬取所有省份
            klmc: 科类，如果为空则爬取所有科类
            zslx: 招生类型，如果为空则爬取所有类型

        Returns:
            招生信息列表
        """
        all_data = []

        # 如果没有CSRF Token，先获取筛选参数来获取Token
        if not self.csrf_token:
            logger.info("未找到CSRF Token，先获取筛选参数...")
            self.get_filter_params()

        # 构建请求参数（根据实际API格式）
        params = {
            'ssmc': province if province else '',  # 省市名称
            'zsnf': str(year),  # 招生年份
            'klmc': klmc if klmc else '',  # 科类名称
            'sex': '',  # 性别（可选）
            'campus': '',  # 校区（可选）
            'zslx': zslx if zslx else ''  # 招生类型
        }

        logger.info(f"正在爬取 {year}年 {province if province else '全部省份'} {klmc if klmc else '全部科类'} {zslx if zslx else '全部类型'} 的招生信息...")

        # 获取数据
        data = self.get_admission_data(params)
        if not data:
            logger.warning(f"未获取到 {year}年 {province} {klmc} {zslx} 的数据")
            return []

        # 解析普通批录取情况（zsSsgradeList）
        batch_list = data.get('zsSsgradeList', [])
        if batch_list:
            batch_data = self.parse_batch_data(batch_list, year, province)
            all_data.extend(batch_data)
            logger.info(f"普通批录取情况: {len(batch_data)} 条")

        # 解析分专业录取情况（sszygradeList）
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
                    available_provinces = [item.get('name', '') or item for item in ssmc_list if item.get('name') or item]
            elif isinstance(filter_list, list):
                available_provinces = [item.get('name', '') or item for item in filter_list if item.get('name') or item]

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

        # 如果province列表为空，尝试爬取全部数据（不指定省份）
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

