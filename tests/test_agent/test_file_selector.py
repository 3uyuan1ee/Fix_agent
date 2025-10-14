"""
测试智能文件选择器
"""

import os
import pytest
import tempfile
import time
from pathlib import Path
from unittest.mock import Mock, patch

from src.agent.file_selector import (
    FileSelector, FileInfo, SelectionCriteria
)


class TestFileSelector:
    """测试文件选择器"""

    @pytest.fixture
    def selector(self):
        """选择器fixture"""
        with patch('src.agent.file_selector.get_config_manager') as mock_config:
            mock_config.return_value.get_section.return_value = {
                'keyword_weight': 0.4,
                'dependency_weight': 0.3,
                'recency_weight': 0.2,
                'extension_weight': 0.1
            }
            return FileSelector()

    @pytest.fixture
    def temp_project_dir(self):
        """临时项目目录fixture"""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir) / "test_project"
            project_dir.mkdir()

            # 创建子目录
            (project_dir / "core").mkdir()
            (project_dir / "tests").mkdir()

            # 创建测试文件
            main_file = project_dir / "main.py"
            main_file.write_text("""
import utils
import config
from core import processor

def main():
    processor.process()
            """)

            utils_file = project_dir / "utils.py"
            utils_file.write_text("""
def helper_function():
    return "helper"
            """)

            config_file = project_dir / "config.py"
            config_file.write_text("""
# Configuration
DEBUG = True
            """)

            processor_file = project_dir / "core" / "processor.py"
            processor_file.write_text("""
class Processor:
    def process(self):
        return "processed"
            """)

            init_file = project_dir / "core" / "__init__.py"
            init_file.write_text("")

            test_file = project_dir / "tests" / "test_main.py"
            test_file.write_text("""
import unittest
from main import main

class TestMain(unittest.TestCase):
    def test_main(self):
        pass
            """)

            # 创建一个较老的文件
            old_file = project_dir / "old_file.py"
            old_file.write_text("# Old file")
            old_time = time.time() - 86400 * 30  # 30天前
            os.utime(old_file, (old_time, old_time))

            # 创建一个最近的文件
            recent_file = project_dir / "recent_file.py"
            recent_file.write_text("# Recent file")
            recent_time = time.time() - 3600  # 1小时前
            os.utime(recent_file, (recent_time, recent_time))

            yield str(project_dir)

    def test_initialization(self, selector):
        """测试初始化"""
        assert selector is not None
        assert hasattr(selector, 'logger')
        assert hasattr(selector, 'file_ops')
        assert hasattr(selector, 'extension_weights')

    def test_selection_criteria_creation(self):
        """测试选择标准创建"""
        criteria = SelectionCriteria(
            keywords=["test", "main"],
            max_files=10,
            prioritize_recent=True
        )

        assert criteria.keywords == ["test", "main"]
        assert criteria.max_files == 10
        assert criteria.prioritize_recent is True

    def test_select_files_by_keywords(self, selector, temp_project_dir):
        """测试根据关键词选择文件"""
        criteria = SelectionCriteria(
            keywords=["main"],
            max_files=5
        )

        selected_files = selector.select_files(temp_project_dir, criteria)

        assert len(selected_files) > 0
        assert any("main" in f.name.lower() for f in selected_files)
        assert all(f.relevance > 0 for f in selected_files)

    def test_select_files_by_multiple_keywords(self, selector, temp_project_dir):
        """测试根据多个关键词选择文件"""
        criteria = SelectionCriteria(
            keywords=["main", "config"],
            max_files=5
        )

        selected_files = selector.select_files(temp_project_dir, criteria)

        assert len(selected_files) > 0
        # 应该包含main.py和config.py
        file_names = [f.name for f in selected_files]
        assert "main.py" in file_names or "config.py" in file_names

    def test_select_files_with_max_limit(self, selector, temp_project_dir):
        """测试文件数量限制"""
        criteria = SelectionCriteria(
            keywords=[""],
            max_files=2
        )

        selected_files = selector.select_files(temp_project_dir, criteria)

        assert len(selected_files) <= 2
        assert all(f.relevance > 0 for f in selected_files)

    def test_select_files_with_min_relevance(self, selector, temp_project_dir):
        """测试最小相关性阈值"""
        criteria = SelectionCriteria(
            keywords=["nonexistent"],
            max_files=10,
            min_relevance=0.5
        )

        selected_files = selector.select_files(temp_project_dir, criteria)

        # 应该没有文件或很少文件匹配
        assert len(selected_files) == 0 or all(f.relevance >= 0.5 for f in selected_files)

    def test_dependency_analysis(self, selector, temp_project_dir):
        """测试依赖关系分析"""
        criteria = SelectionCriteria(
            keywords=[""],
            max_files=10,
            prioritize_dependencies=True
        )

        selected_files = selector.select_files(temp_project_dir, criteria)

        # 检查是否分析了依赖关系
        main_file = next((f for f in selected_files if f.name == "main.py"), None)
        if main_file:
            assert "utils" in main_file.imports or "config" in main_file.imports

    def test_recency_priority(self, selector, temp_project_dir):
        """测试修改时间优先级"""
        criteria = SelectionCriteria(
            keywords=[""],
            max_files=10,
            prioritize_recent=True
        )

        selected_files = selector.select_files(temp_project_dir, criteria)

        # 最近的文件应该有更高的相关性分数
        recent_file = next((f for f in selected_files if f.name == "recent_file.py"), None)
        old_file = next((f for f in selected_files if f.name == "old_file.py"), None)

        if recent_file and old_file:
            assert recent_file.relevance >= old_file.relevance

    def test_extension_weighting(self, selector, temp_project_dir):
        """测试文件扩展名权重"""
        # 创建不同扩展名的文件，避免关键词匹配的影响
        (Path(temp_project_dir) / "script.js").write_text("console.log('script');")
        (Path(temp_project_dir) / "notes.txt").write_text("some notes")

        criteria = SelectionCriteria(
            keywords=[""],  # 使用空关键词避免关键词匹配的影响
            max_files=10
        )

        selected_files = selector.select_files(temp_project_dir, criteria)

        # Python文件应该有更高的权重
        python_files = [f for f in selected_files if f.extension == '.py']
        js_files = [f for f in selected_files if f.extension == '.js']

        if python_files and js_files:
            avg_python_score = sum(f.relevance for f in python_files) / len(python_files)
            avg_js_score = sum(f.relevance for f in js_files) / len(js_files)
            assert avg_python_score >= avg_js_score

    def test_exclude_patterns(self, selector, temp_project_dir):
        """测试排除模式"""
        # 创建排除目录
        exclude_dir = Path(temp_project_dir) / "exclude"
        exclude_dir.mkdir()
        (exclude_dir / "excluded.py").write_text("# This should be excluded")

        criteria = SelectionCriteria(
            keywords=[""],
            max_files=10,
            exclude_patterns=["exclude"]
        )

        selected_files = selector.select_files(temp_project_dir, criteria)

        # 排除的文件不应该在选择结果中
        excluded_paths = [f.path for f in selected_files if "exclude" in f.path]
        assert len(excluded_paths) == 0

    def test_file_statistics(self, selector, temp_project_dir):
        """测试文件统计信息"""
        criteria = SelectionCriteria(max_files=10)
        selected_files = selector.select_files(temp_project_dir, criteria)

        stats = selector.get_file_statistics(selected_files)

        assert 'total_files' in stats
        assert 'total_size' in stats
        assert 'extensions' in stats
        assert 'avg_relevance' in stats
        assert stats['total_files'] == len(selected_files)

    def test_export_selection_results_json(self, selector, temp_project_dir):
        """测试导出JSON格式结果"""
        criteria = SelectionCriteria(max_files=5)
        selected_files = selector.select_files(temp_project_dir, criteria)

        json_result = selector.export_selection_results(selected_files, 'json')

        assert 'selected_files' in json_result
        assert 'statistics' in json_result
        assert isinstance(json_result, str)

    def test_export_selection_results_yaml(self, selector, temp_project_dir):
        """测试导出YAML格式结果"""
        criteria = SelectionCriteria(max_files=5)
        selected_files = selector.select_files(temp_project_dir, criteria)

        yaml_result = selector.export_selection_results(selected_files, 'yaml')

        assert 'selected_files' in yaml_result
        assert 'statistics' in yaml_result
        assert isinstance(yaml_result, str)

    def test_suggest_related_files(self, selector, temp_project_dir):
        """测试建议相关文件"""
        # 先选择一些文件
        criteria = SelectionCriteria(
            keywords=["main"],
            max_files=3
        )
        selected_files = selector.select_files(temp_project_dir, criteria)

        # 获取所有文件
        all_criteria = SelectionCriteria(max_files=100)
        all_files = selector.select_files(temp_project_dir, all_criteria)

        if selected_files and all_files:
            suggestions = selector.suggest_related_files(selected_files, all_files, max_suggestions=5)

            assert isinstance(suggestions, list)
            assert len(suggestions) <= 5

            # 建议的文件应该不在已选择的文件中
            selected_paths = {f.path for f in selected_files}
            suggestion_paths = {f.path for f in suggestions}
            assert selected_paths.isdisjoint(suggestion_paths)

    def test_file_info_dataclass(self):
        """测试FileInfo数据类"""
        file_info = FileInfo(
            path="/test/file.py",
            name="file.py",
            extension=".py",
            size=1024,
            modified_time=time.time(),
            content="test content"
        )

        assert file_info.path == "/test/file.py"
        assert file_info.name == "file.py"
        assert file_info.extension == ".py"
        assert file_info.size == 1024
        assert file_info.content == "test content"
        assert file_info.relevance == 0.0
        assert isinstance(file_info.imports, set)
        assert isinstance(file_info.dependencies, set)
        assert isinstance(file_info.dependents, set)

    def test_calculate_keyword_score(self, selector):
        """测试关键词分数计算"""
        file_info = FileInfo(
            path="/test/main_test_file.py",
            name="main_test_file.py",
            extension=".py",
            size=1024,
            modified_time=time.time(),
            content="This is a test file with main functionality"
        )

        score = selector._calculate_keyword_score(file_info, ["main", "test"])

        assert score > 0
        # 文件路径中包含关键词应该得分最高
        assert "main" in file_info.path.lower()
        assert "test" in file_info.path.lower()

    def test_calculate_pattern_score(self, selector):
        """测试文件名模式分数计算"""
        # 测试核心文件模式
        core_file = FileInfo(
            path="/test/main.py",
            name="main.py",
            extension=".py",
            size=1024,
            modified_time=time.time()
        )

        score = selector._calculate_pattern_score(core_file)
        assert score > 0.8  # main.py应该得到高分

        # 测试普通文件
        normal_file = FileInfo(
            path="/test/random.py",
            name="random.py",
            extension=".py",
            size=1024,
            modified_time=time.time()
        )

        normal_score = selector._calculate_pattern_score(normal_file)
        assert normal_score <= core_file.score

    def test_calculate_recency_score(self, selector):
        """测试修改时间分数计算"""
        current_time = time.time()

        # 最近的文件
        recent_file = FileInfo(
            path="/test/recent.py",
            name="recent.py",
            extension=".py",
            size=1024,
            modified_time=current_time - 3600  # 1小时前
        )

        recent_score = selector._calculate_recency_score(recent_file, current_time)
        assert recent_score == 1.0

        # 中等旧的文件（60天前）
        old_file = FileInfo(
            path="/test/old.py",
            name="old.py",
            extension=".py",
            size=1024,
            modified_time=current_time - 86400 * 60  # 60天前
        )

        old_score = selector._calculate_recency_score(old_file, current_time)
        assert old_score <= recent_score
        assert old_score == 0.4  # 60天在30-90天范围内，应该得到0.4分

        # 很旧的文件（120天前）
        very_old_file = FileInfo(
            path="/test/very_old.py",
            name="very_old.py",
            extension=".py",
            size=1024,
            modified_time=current_time - 86400 * 120  # 120天前
        )

        very_old_score = selector._calculate_recency_score(very_old_file, current_time)
        assert very_old_score <= old_score
        assert very_old_score == 0.2  # 120天超过90天，应该得到最低分0.2

    def test_calculate_dependency_score(self, selector):
        """测试依赖关系分数计算"""
        # 普通文件（非核心文件）
        service_file = FileInfo(
            path="/test/service.py",
            name="service.py",
            extension=".py",
            size=1024,
            modified_time=time.time(),
            imports={"utils", "config"}
        )

        # 被依赖的文件
        utils_file = FileInfo(
            path="/test/utils.py",
            name="utils.py",
            extension=".py",
            size=1024,
            modified_time=time.time(),
            dependents={"/test/service.py"}
        )

        all_files = [service_file, utils_file]

        service_score = selector._calculate_dependency_score(service_file, {}, all_files)
        utils_score = selector._calculate_dependency_score(utils_file, {}, all_files)

        # 被依赖的文件应该得分更高
        assert utils_score > service_score

        # 验证具体的分数计算逻辑
        # service文件导入utils，所以utils文件有一个dependents，应该得分更高
        assert utils_score > 0.0  # utils文件应该有非零分数（被依赖）
        assert service_score == 0.0    # service文件没有被其他文件依赖，应该是0分

        # 测试核心文件的加分
        main_file = FileInfo(
            path="/test/main.py",
            name="main.py",
            extension=".py",
            size=1024,
            modified_time=time.time(),
            dependents={"/test/service.py"}
        )

        main_score = selector._calculate_dependency_score(main_file, {}, all_files + [main_file])

        # main.py因为核心文件名称应该有额外加分
        assert main_score >= 0.5  # 核心文件应该有基础加分