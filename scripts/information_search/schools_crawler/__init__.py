"""
学校爬虫模块
包含各高校的招生信息爬虫实现
"""

from .bit_crawler import BITCrawler
from .buaa_crawler import BUAACrawler
from .tsinghua_crawler import TsinghuaCrawler
from .pku_crawler import PKUCrawler
from .hust_crawler import HUSTCrawler
from .nankai_crawler import NankaiCrawler

__all__ = [
    'BITCrawler',
    'BUAACrawler',
    'TsinghuaCrawler',
    'PKUCrawler',
    'HUSTCrawler',
    'NankaiCrawler',
]

