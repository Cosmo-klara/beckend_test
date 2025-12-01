import argparse
import logging
from datetime import datetime

from schools_crawler import (
    BITCrawler,
    BUAACrawler,
    TsinghuaCrawler,
    PKUCrawler,
    HUSTCrawler,
    NankaiCrawler
)
from cleaner import DataCleaner
from exporter import CSVExporter


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 可用的学校爬虫映射
AVAILABLE_SCHOOLS = {
    'bit': ('北京理工大学', BITCrawler),
    'buaa': ('北京航空航天大学', BUAACrawler),
    'tsinghua': ('清华大学', TsinghuaCrawler),
    'pku': ('北京大学', PKUCrawler),
    'hust': ('华中科技大学', HUSTCrawler),
    'nankai': ('南开大学', NankaiCrawler),
}


def run_once(year: int = None, school: str = None):
    if year is None:
        year = datetime.now().year

    # 确定要爬取的学校列表
    if school is None:
        # 如果没有指定学校，爬取所有可用学校
        schools_to_crawl = list(AVAILABLE_SCHOOLS.keys())
        logger.info(f"未指定学校，将爬取所有可用学校: {[AVAILABLE_SCHOOLS[s][0] for s in schools_to_crawl]}")
    else:
        # 只爬取指定的学校
        schools_to_crawl = [school]

    cleaner = DataCleaner()
    exporter = CSVExporter()

    # 遍历所有要爬取的学校
    for current_school in schools_to_crawl:
        try:
            logger.info(f"开始执行爬取任务，年份: {year}, 学校: {AVAILABLE_SCHOOLS[current_school][0] if current_school in AVAILABLE_SCHOOLS else current_school}")

            # 初始化爬虫
            if current_school not in AVAILABLE_SCHOOLS:
                logger.error(f"不支持的学校标识: {current_school}")
                continue
            school_name, crawler_class = AVAILABLE_SCHOOLS[current_school]
            crawler = crawler_class()

            # 执行爬取任务
            raw_data = crawler.crawl_by_year(year)
            if not raw_data:
                logger.warning(f"未获取到任何数据（学校: {current_school or '模拟数据'}）")
                continue

            cleaned_data = cleaner.clean_data(raw_data)
            if not cleaned_data:
                logger.warning(f"数据清洗后为空（学校: {current_school or '模拟数据'}）")
                continue

            output_file = exporter.export_by_year(cleaned_data, year)
            logger.info(f"任务执行完成，输出文件: {output_file}")

        except Exception as e:
            logger.error(f"任务执行失败（学校: {current_school or '模拟数据'}）: {e}", exc_info=True)




def main():
    parser = argparse.ArgumentParser(description='高考志愿填报系统 - 招生信息爬虫')
    parser.add_argument(
        '--mode',
        choices=['once'],
        default='once',
        help='运行模式：once=执行一次'
    )
    parser.add_argument(
        '--year',
        type=int,
        default=None,
        help='指定年份（仅用于once模式）'
    )

    parser.add_argument(
        '--use-real',
        action='store_true',
        help='使用真实爬虫（需要配置数据源）'
    )
    parser.add_argument(
        '--school',
        choices=['bit', 'buaa', 'tsinghua', 'pku', 'hust', 'nankai'],
        default=None,
        help='学校标识：bit=北京理工大学，buaa=北京航空航天大学，tsinghua=清华大学，pku=北京大学，hust=华中科技大学，nankai=南开大学。如果不指定，则爬取所有可用学校（仅用于use-real模式）'
    )


    args = parser.parse_args()

    if args.mode == 'once':
        run_once(year=args.year, school=args.school)


if __name__ == '__main__':
    main()

