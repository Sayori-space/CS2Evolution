import os
import sys
from pathlib import Path


class PathManager:
    @staticmethod
    def get_root_dir():
        """获取项目根目录"""
        if getattr(sys, 'frozen', False):
            # EXE 运行模式
            return Path(sys._MEIPASS)
        return Path(__file__).resolve().parent.parent.parent

    @staticmethod
    def get_data_dir():
        """获取数据存储根目录 (在项目根目录下创建一个 data 文件夹)"""
        root = PathManager.get_root_dir()
        data_path = root / "data"
        # 确保目录存在
        data_path.mkdir(parents=True, exist_ok=True)
        return data_path

    @staticmethod
    def get_db_path():
        """获取数据库路径"""
        # 对应：data/db/tradeup_db.json
        return PathManager.get_root_dir() / "data" / "db" / "tradeup_db.json"

    @staticmethod
    def get_report_dir():
        """获取报告输出路径 (存放在用户文档或EXE旁边)"""
        if getattr(sys, 'frozen', False):
            base = Path(sys.executable).parent
        else:
            base = PathManager.get_root_dir()

        report_path = base / "CS2_Reports"
        report_path.mkdir(exist_ok=True)
        return report_path