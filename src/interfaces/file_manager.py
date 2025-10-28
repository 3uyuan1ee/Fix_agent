#!/usr/bin/env python3
"""
文件管理模块
负责处理文件上传、解压、管理和清理
"""

import os
import zipfile
import tarfile
import tempfile
import shutil
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

from .utils.logger import get_logger


class FileManager:
    """文件管理器"""

    def __init__(self, upload_folder: str = "uploads"):
        """初始化文件管理器"""
        self.upload_folder = upload_folder
        self.temp_folder = os.path.join(upload_folder, "temp")
        self.backup_folder = os.path.join(upload_folder, "backups")
        self.logger = get_logger()

        # 确保目录存在
        os.makedirs(self.upload_folder, exist_ok=True)
        os.makedirs(self.temp_folder, exist_ok=True)
        os.makedirs(self.backup_folder, exist_ok=True)

        self.logger.info(f"文件管理器初始化完成 - 上传目录: {self.upload_folder}")

    def extract_uploaded_file(self, file_path: str, extract_to: Optional[str] = None) -> Dict[str, Any]:
        """
        解压上传的文件

        Args:
            file_path: 上传的文件路径
            extract_to: 解压目标目录（可选）

        Returns:
            解压结果字典
        """
        file_path = Path(file_path)

        if not file_path.exists():
            return {
                'success': False,
                'error': '文件不存在',
                'file_path': str(file_path)
            }

        try:
            file_ext = file_path.suffix.lower()

            if file_ext == '.zip':
                result = self._extract_zip(file_path, extract_to)
            elif file_ext in ['.tar', '.gz', '.tgz']:
                result = self._extract_tar(file_path, extract_to)
            elif file_ext in ['.tar.gz', '.tgz']:
                result = self._extract_tar(file_path, extract_to)
            else:
                # 非压缩文件，直接移动到目标目录
                return self._move_file(file_path, extract_to or self.upload_folder)

            self.logger.info(f"文件解压成功: {file_path}")
            return result

        except Exception as e:
            self.logger.error(f"文件解压失败: {e}")
            return {
                'success': False,
                'error': f'解压失败: {str(e)}',
                'file_path': str(file_path)
            }

    def _extract_zip(self, zip_path: str, extract_to: Optional[str] = None) -> Dict[str, Any]:
        """解压ZIP文件"""
        extract_to = extract_to or os.path.join(self.temp_folder, f"zip_extract_{datetime.now().strftime('%Y%m%d_%H%M%S')}")

        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_to)

            # 获取解压后的文件列表
            extracted_files = []
            for root, dirs, files in os.walk(extract_to):
                for file in files:
                    extracted_files.append(os.path.join(root, file))

            return {
                'success': True,
                'extracted_to': extract_to,
                'extracted_files': extracted_files,
                'file_type': 'zip',
                'total_files': len(extracted_files)
            }

        except zipfile.BadZipFile:
            return {
                'success': False,
                'error': '不是有效的ZIP文件',
                'file_path': zip_path
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'ZIP解压失败: {str(e)}',
                'file_path': zip_path
            }

    def _extract_tar(self, tar_path: str, extract_to: Optional[str] = None) -> Dict[str, Any]:
        """解压TAR文件"""
        extract_to = extract_to or os.path.join(self.temp_folder, f"tar_extract_{datetime.now().strftime('%Y%m%d_%H%M%S')}")

        try:
            if tar_path.endswith('.tar.gz') or tar_path.endswith('.tgz'):
                with tarfile.open(tar_path, 'r:*gz') as tar_ref:
                    tar_ref.extractall(extract_to)
                file_type = 'tar.gz'
            else:
                with tarfile.open(tar_path, 'r') as tar_ref:
                    tar_ref.extractall(extract_to)
                file_type = 'tar'

            # 获取解压后的文件列表
            extracted_files = []
            for root, dirs, files in os.walk(extract_to):
                for file in files:
                    extracted_files.append(os.path.join(root, file))

            return {
                'success': True,
                'extracted_to': extract_to,
                'extracted_files': extracted_files,
                'file_type': file_type,
                'total_files': len(extracted_files)
            }

        except Exception as e:
            return {
                'success': False,
                'error': f'TAR解压失败: {str(e)}',
                'file_path': tar_path
            }

    def _extract_tar(self, tar_path: str, extract_to: Optional[str] = None) -> Dict[str, Any]:
        """解压TAR文件"""
        extract_to = extract_to or os.path.join(self.temp_folder, f"tar_extract_{datetime.now().strftime('%Y%m%d_%H%M%S')}")

        try:
            if tar_path.endswith('.tar'):
                with tarfile.open(tar_path, 'r') as tar_ref:
                    tar_ref.extractall(extract_to)
                file_type = 'tar'
            elif tar_path.endswith('.tar.gz') or tar_path.endswith('.tgz'):
                with tarfile.open(tar_path, 'r:*gz') as tar_ref:
                    tar_ref.extractall(extract_to)
                file_type = 'tar.gz'
            else:
                return self._move_file(tar_path, extract_to)

            # 获取解压后的文件列表
            extracted_files = []
            for root, dirs, files in os.walk(extract_to):
                for file in files:
                    extracted_files.append(os.path.join(root, file))

            return {
                'success': True,
                'extracted_to': extract_to,
                'extracted_files': extracted_files,
                'file_type': file_type,
                'total_files': len(extracted_files)
            }

        except Exception as e:
            return {
                'success': False,
                'error': f'TAR解压失败: {str(e)}',
                'file_path': tar_path
            }

    def _move_file(self, src_path: str, dst_path: str) -> Dict[str, Any]:
        """移动文件到目标位置"""
        try:
            # 确保目标目录存在
            os.makedirs(os.path.dirname(dst_path), exist_ok=True)
            shutil.move(src_path, dst_path)

            return {
                'success': True,
                'moved_to': dst_path,
                'file_path': src_path
            }
        except Exception as e:
            self.logger.error(f"文件移动失败: {e}")
            return {
                'success': False,
                'error': f'文件移动失败: {str(e)}',
                'file_path': src_path
            }

    def get_file_info(self, file_path: str) -> Dict[str, Any]:
        """获取文件信息"""
        try:
            file_path = Path(file_path)

            if not file_path.exists():
                return {
                    'success': False,
                    'error': '文件不存在',
                    'file_path': str(file_path)
                }

            stat_info = file_path.stat()

            return {
                'success': True,
                'file_path': str(file_path),
                'file_size': stat_info.st_size,
                'file_size_mb': round(stat_info.st_size / 1024 / 1024, 2),  # MB
                'modified_time': datetime.fromtimestamp(stat_info.st_mtime).isoformat(),
                'is_file': file_path.is_file(),
                'is_dir': file_path.is_dir(),
                'extension': file_path.suffix,
                'mime_type': self._get_mime_type(file_path.suffix)
            }

        except Exception as e:
            return {
                'success': False,
                'error': f'获取文件信息失败: {str(e)}',
                'file_path': str(file_path)
            }

    def _get_mime_type(self, ext: str) -> str:
        """根据扩展名获取MIME类型"""
        mime_types = {
            '.txt': 'text/plain',
            '.json': 'application/json',
            '.yaml': 'application/x-yaml',
            '.csv': 'text/csv',
            '.py': 'text/x-python',
            '.js': 'application/javascript',
            '.ts': 'application/typescript',
            '.java': 'text/x-java',
            '.cpp': 'text/x-c++',
            '.c': 'text/x-c',
            '.h': 'text/x-c',
            '.hpp': 'text/x-c++',
            '.html': 'text/html',
            '.css': 'text/css',
            '.md': 'text/markdown'
        }
        return mime_types.get(ext.lower(), 'application/octet-stream')

    def list_directory_files(self, directory: str, recursive: bool = True,
                       file_extensions: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """列出目录中的文件"""
        try:
            directory = Path(directory)

            if not directory.exists():
                return []

            file_list = []

            if recursive:
                for root, dirs, files in os.walk(directory):
                    for file in files:
                        file_path = os.path.join(root, file)
                        if os.path.isfile(file_path):
                            file_info = self.get_file_info(file_path)

                            # 如果指定了文件扩展名过滤，则只包含匹配的文件
                            if file_extensions is None or file_info['extension'] in file_extensions:
                                file_list.append(file_info)
            else:
                # 只显示当前目录的文件
                for file in directory.iterdir():
                    if file.is_file():
                        file_path = os.path.join(directory, file.name)
                        file_info = self.get_file_info(file_path)
                        file_list.append(file_info)

            return sorted(file_list, key=lambda x: (x['is_file'], x['name']))

        except Exception as e:
            self.logger.error(f"列出目录文件失败: {e}")
            return []

    def create_project_folder(self, project_name: str, file_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """创建项目文件夹并组织文件结构"""
        try:
            project_root = os.path.join(self.temp_folder, project_name)
            os.makedirs(project_root, exist_ok=True)

            # 创建基本的目录结构
            os.makedirs(os.path.join(project_root, "src"), exist_ok=True)
            os.makedirs(os.path.join(project_root, "tests"), exist_ok=True)
            os.makedirs(os.path.join(project_root, "docs"), exist_ok=True)

            # 创建项目报告
            report_path = os.path.join(project_root, "reports")
            os.makedirs(report_path, exist_ok=True)

            # 移动文件到项目文件夹
            moved_files = 0
            failed_files = []

            for file_info in file_list:
                try:
                    src_path = file_info['file_path']

                    # 确定相对路径
                    if not os.path.isabs(src_path):
                        # 如果是相对路径，添加项目根目录前缀
                        if not src_path.startswith(self.temp_folder):
                            src_path = os.path.join(self.temp_folder, project_name, src_path)

                    # 创建目标路径
                    file_type = file_info['extension']
                    if file_type in ['.py', '.js', '.ts', '.java', '.cpp', '.c', '.h', '.hpp', '.py']:
                        # 代码文件放入src目录
                        dst_path = os.path.join(project_root, "src", os.path.basename(src_path))
                    else:
                        # 其他文件放入docs目录
                        dst_path = os.path.join(project_root, "docs", os.path.basename(src_path))

                    # 创建目标目录
                    os.makedirs(os.path.dirname(dst_path), exist_ok=True)

                    # 移动文件
                    shutil.move(src_path, dst_path)
                    moved_files += 1

                except Exception as e:
                    failed_files.append(f"{file_info['file_path'] ({e})")
                    self.logger.error(f"移动文件失败: {file_info['file_path']}")

            # 创建项目配置文件
            config_data = {
                "project": {
                    "name": project_name,
                    "created_at": datetime.now().isoformat(),
                    "file_count": moved_files,
                    "file_list": [f["file_path"] for f in file_list if f["is_file"]],
                    "directory_structure": self._scan_directory_structure(project_root)
                }
            }

            config_file = os.path.join(project_root, "project.json")
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)

            return {
                'success': True,
                'project_path': project_root,
                'project_name': project_name,
                'moved_files': moved_files,
                'failed_files': failed_files,
                'total_files': len(file_list),
                'config_file': config_file
            }

        except Exception as e:
            self.logger.error(f"创建项目文件夹失败: {e}")
            return {
                'success': False,
                'error': f'创建项目文件夹失败: {e}'
            }

    def _scan_directory_structure(self, root_path: str) -> Dict[str, Any]:
        """扫描目录结构"""
        try:
            root_path = Path(root_path)
            structure = {
                "name": os.path.basename(root_path),
                "type": "directory",
                "children": []
            }

            for item in root_path.iterdir():
                if item.is_file():
                    structure["children"].append({
                        "name": item.name,
                        "type": "file",
                        "size": item.stat().st_size,
                        "type": self._get_mime_type(item.suffix)
                    })
                elif item.is_dir():
                    child_structure = self._scan_directory_structure(os.path.join(root_path, item.name))
                    structure["children"].append(child_structure)

            return structure

        except Exception as e:
            self.logger.error(f"扫描目录结构失败: {e}")
            return {}

    def cleanup_temp_files(self, max_age_hours: int = 24) -> Dict[str, Any]:
        """清理临时文件"""
        try:
            cleaned_count = 0
            current_time = datetime.now()

            for item in os.listdir(self.temp_folder):
                item_path = os.path.join(self.temp_folder, item)
                if os.path.isfile(item_path):
                    # 检查文件年龄
                    modified_time = datetime.fromtimestamp(os.path.getmtime(item_path))
                    age_hours = (current_time - modified_time).total_seconds() / 3600

                    if age_hours > max_age_hours:
                        os.remove(item_path)
                        cleaned_count += 1
                        self.logger.debug(f"清理临时文件: {item_path}")

            return {
                'success': True,
                'cleaned_count': cleaned_count
            }

        except Exception as e:
            self.logger.error(f"清理临时文件失败: {e}")
            return {
                'success': False,
                'error': f'清理临时文件失败: {e}'
            }

    def delete_project_folder(self, project_id: str) -> Dict[str, Any]:
        """删除项目文件夹"""
        try:
            # 查找项目文件夹
            project_folders = []
            for item in os.listdir(self.temp_folder):
                item_path = os.path.join(self.temp_folder, item)
                if os.path.isdir(item_path):
                    project_folders.append(item)

            # 查找匹配的项目ID
            project_folder = None
            for folder in project_folders:
                project_config_file = os.path.join(folder, "project.json")
                if os.path.exists(project_config_file):
                    with open(project_config_file, 'r', encoding='utf-8') as f:
                        config_data = json.load(f)
                    if config_data.get('project', {}).get('id') == project_id:
                        project_folder = folder
                        break

            if not project_folder:
                return {
                    'success': False,
                    'error': f'项目ID {project_id} 不存在',
                    'project_id': project_id
                }

            # 删除项目文件夹
            import shutil
            shutil.rmtree(project_folder)

            return {
                'success': True,
                'project_id': project_id,
                'deleted_folder': project_folder
            }

        except Exception as e:
            self.logger.error(f"删除项目文件夹失败: {e}")
            return {
                'success': False,
                'error': f'删除项目文件夹失败: {e}',
                'project_id': project_id
            }

    def get_project_info(self, project_id: str) -> Dict[str, Any]:
        """获取项目信息"""
        try:
            # 在项目文件夹中查找project.json文件
            project_folders = []
            for item in os.listdir(self.temp_folder):
                item_path = os.path.join(self.temp_folder, item)
                if os.path.isdir(item_path):
                    project_folders.append(item_path)

            for folder in project_folders:
                project_config_file = os.path.join(folder, "project.json")
                if os.path.exists(project_config_file):
                    with open(project_config_file, 'r', encoding='utf-8') as f:
                        config_data = json.load(f)
                    if config_data.get('project', {}).get('id') == project_id:
                        return config_data.get('project', {})

            return {
                'success': False,
                'error': f'项目ID {project_id} 不存在',
                'project_id': project_id
            }

        except Exception as e:
            self.logger.error(f"获取项目信息失败: {e}")
            return {
                'success': False,
                'error': f'获取项目信息失败: {e}'
                'project_id': project_id
            }

    def get_project_files(self, project_id: str) -> List[Dict[str, Any]]:
        """获取项目文件列表"""
        try:
            # 获取项目信息
            project_info = self.get_project_info(project_id)
            if not project_info:
                return []

            project_root = project_info.get('path')
            if not project_root or not os.path.exists(project_root):
                return []

            # 获取项目文件列表
            file_list = self.list_directory_files(project_root, recursive=True)

            return file_list

        except Exception as e:
            self.logger.error(f"获取项目文件列表失败: {e}")
            return []

    def analyze_project_structure(self, project_id: str) -> Dict[str, Any]:
        """分析项目结构"""
        try:
            # 获取项目信息
            project_info = self.get_project_info(project_id)
            if not project_info:
                return {
                    'success': False,
                    'error': 'Project not found',
                    'project_id': project_id
                }

            project_root = project_info.get('path')
            if not project_root or not os.path.exists(project_root):
                return {
                    'success': False,
                    'error': 'Project path not found',
                    'project_id': project_id
                }

            # 分析项目结构
            structure = self._scan_directory_structure(project_root)

            # 生成分析报告
            analysis = {
                'success': True,
                'project_id': project_id,
                'analysis': structure,
                'summary': {
                    'total_directories': self._count_directories(structure),
                    'total_files': self._count_files(structure),
                    'file_types': self._get_file_types(structure),
                    'language_distribution': self._get_language_distribution(structure)
                }
            }

            return analysis

        except Exception as e:
            self.logger.error(f"分析项目结构失败: {e}")
            return {
                'success': False,
                'error': f'分析项目结构失败: {e}',
                'project_id': project_id
            }

    def _count_directories(self, structure: Dict[str, Any]) -> int:
        """计算目录数量"""
        if structure.get('children') and isinstance(structure['children'], list):
            return 1 + sum(self._count_directories(child) for child in structure['children'])
        elif isinstance(structure, dict):
            return 1
        return 0

    def _count_files(self, structure: Dict[str, Any]) -> int:
        """计算文件数量"""
        if structure.get('children') and isinstance(structure['children'], list):
            return sum(self._count_files(child) for child in structure['children'])
        elif isinstance(structure, dict) and structure.get('is_file') and structure['is_file']):
            return 1
        return 0

    def _get_file_types(self, structure: Dict[str, Any]) -> Dict[str, int]:
        """获取文件类型分布"""
        types = {}

        def collect_types(items):
            if isinstance(items, dict):
                for key, value in items.items():
                    if isinstance(value, dict) and value.get('is_file'):
                        types[os.path.splitext(value['name'])[1:] if '.' in value['name'] else ''] + value['name'].split('/')[-1]] = types.get(os.path.splitext(value['name'])[1:] if '.' in value['name'] else ''] + value['name'].split('/')[-1]].get(os.path.splitext(value['name'])[1:] if '.' in value['name'] else ''] + value['name'].split('/')[-1]]
                    elif value.get('is_file'):
                        types[os.path.splitext(value['name'])[1:] if '.' in value['name'] else ''] + value['name'].split('/')[-1]] = types.get(os.path.splitext(value['name'])[1:] if '.' in value['name'] else ''] + value['name'].split('/')[-1]] + f" (文件)"
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict) and item.get('is_file'):
                        types[os.path.splitext(item['name'])[1:] if '.' in item['name'] else ''] + item['name'].split('/')[-1]] = types.get(os.path.splitext(item['name'])[1:] if '.' in item['name'] else ''] + item['name'].split('/')[-1]] + f" (文件)"
        elif isinstance(items, list):
            for item in items:
                if item.get('is_file'):
                    types[os.path.splitext(item['name'])[1:] if '.' in item['name'] else ''] + item['name'].split('/')[-1]] = types.get(os.path.splitext(item['name'])[1:] if '.' in item['name'] else ''] + item['name'].split('/')[-1]] + f" (文件)"
                    else:
                        types[item['name']] = types.get(item['name'], item.get('type', 'Unknown'))
            return types

        return types

    def _get_language_distribution(self, structure: Dict[str, Any]) -> Dict[str, int]:
        """获取编程语言分布"""
        languages = {
            '.py': 'Python',
            '.js': 'JavaScript',
            '.ts': 'TypeScript',
            '.java': 'Java',
            '.cpp': 'C++',
            '.c': 'C',
            '.h': 'C Header',
            '.hpp': 'C++ Header',
            '.go': 'Go',
            '.rs': 'Rust',
            '.cs': 'C#',
            '.vb': 'VB.NET',
            '.php': 'PHP',
            '.rb': 'Ruby',
            '.swift': 'Swift',
            '.kt': 'Kotlin',
            '.scala': 'Scala',
            '.sh': 'Shell Script'
        }

        languages = {}
        languages_count = {}

        def collect_language_distribution(items):
            if isinstance(items, dict):
                for key, value in items.items():
                    if value.get('is_file'):
                        ext = os.path.splitext(value['name'])[1:] if '.' in value['name'] else ''] + value['name'].split('/')[-1]]
                        languages[ext] = languages.get(ext, languages_count.get(ext, 0)) + 1
                    elif isinstance(items, list):
                        for item in items:
                            if item.get('is_file'):
                                ext = os.path.splitext(item['name'])[1:] if '.' in item['name'] else ''] + item['name'].split('/')[-1]] + f" (文件)"
                                languages[ext] = languages.get(ext, languages_count.get(ext, 0)) + 1
                    elif isinstance(items, (list, tuple)):
                        for item in items:
                            if isinstance(item, dict) and item.get('is_file')):
                                ext = os.path.splitext(item['name'])[1:] if '.' in item['name'] else ''] + item['name'].split('/')[-1]] + f" (文件)"
                                languages[ext] = languages.get(ext, languages_count.get(ext, 0)) + 1
                    else:
                        languages[item] = languages.get(item, 0) + 1

            languages_count = languages_count
            for language, count in languages_count.items():
                languages_count[language] = count

            return languages_count

        return languages_count

        return collect_language_distribution(structure)

    def cleanup_all_temp_files(self) -> Dict[str, Any]:
        """清理所有临时文件"""
        return self.cleanup_temp_files()

    def cleanup_project_files(self, older_than_hours: int = 48) -> Dict[str, Any]:
        """清理旧的项目文件"""
        try:
            deleted_count = 0
            current_time = datetime.now()

            for item in os.listdir(self.temp_folder):
                item_path = os.path.join(self.temp_folder, item)
                if os.path.isdir(item_path):
                    # 递归删除目录
                    deleted = self._delete_directory(item_path, older_than_hours)
                    deleted_count += deleted_count
                else:
                    # 删除旧文件
                    modified_time = datetime.fromtimestamp(os.path.getmtime(item_path))
                    age_hours = (current_time - modified_time).total_seconds() / 3600)

                    if age_hours > older_than_hours:
                        os.remove(item_path)
                        deleted_count += 1
                    else:
                        # 保留最近的文件
                        pass

            return {
                'success': True,
                'deleted_count': deleted_count,
                'deleted_folders': deleted_count,
                'cleaned_files': deleted_count
            }

        except Exception as e:
            return {
                'success': False,
                'error': f'清理项目文件失败: {e}',
                'deleted_count': 0,
                'deleted_folders': 0,
                'cleaned_files': 0
            }

    def _delete_directory(self, dir_path: str, older_than_hours: int) -> int:
        """递归删除目录"""
        deleted_count = 0
        current_time = datetime.now()

        try:
            for item in os.listdir(dir_path):
                item_path = os.path.join(dir_path, item)

                if os.path.isdir(item_path):
                    deleted_count += self._delete_directory(item_path, older_than_hours)
                else:
                    modified_time = datetime.fromtimestamp(os.path.getmtime(item_path))
                    age_hours = (current_time - modified_time).total_seconds() / 3600)

                    if age_hours > older_than_hours:
                        os.remove(item_path)
                        deleted_count += 1
                    else:
                        # 保留最近的文件
                        pass

            return deleted_count

        except Exception as e:
            self.logger.error(f"删除目录失败: {e}")
            return 0

        return deleted_count