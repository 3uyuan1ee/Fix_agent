#!/usr/bin/env python3
"""
文件管理模块
负责处理文件上传、解压、管理和清理
"""

import json
import os
import shutil
import tarfile
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ..utils.logger import get_logger


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

    def extract_uploaded_file(
        self, file_path: str, extract_to: Optional[str] = None
    ) -> Dict[str, Any]:
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
                "success": False,
                "error": "文件不存在",
                "file_path": str(file_path),
            }

        try:
            file_ext = file_path.suffix.lower()

            if file_ext == ".zip":
                result = self._extract_zip(file_path, extract_to)
            elif file_ext in [".tar", ".gz", ".tgz"]:
                result = self._extract_tar(file_path, extract_to)
            elif file_ext in [".tar.gz", ".tgz"]:
                result = self._extract_tar(file_path, extract_to)
            else:
                # 非压缩文件，直接移动到目标目录
                return self._move_file(file_path, extract_to or self.upload_folder)

            self.logger.info(f"文件解压成功: {file_path}")
            return result

        except Exception as e:
            self.logger.error(f"文件解压失败: {e}")
            return {
                "success": False,
                "error": f"解压失败: {str(e)}",
                "file_path": str(file_path),
            }

    def _extract_zip(
        self, zip_path: str, extract_to: Optional[str] = None
    ) -> Dict[str, Any]:
        """解压ZIP文件"""
        extract_to = extract_to or os.path.join(
            self.temp_folder, f"zip_extract_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )

        try:
            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                zip_ref.extractall(extract_to)

            # 获取解压后的文件列表
            extracted_files = []
            for root, dirs, files in os.walk(extract_to):
                for file in files:
                    extracted_files.append(os.path.join(root, file))

            return {
                "success": True,
                "extracted_to": extract_to,
                "files": extracted_files,
                "file_type": "zip",
                "total_files": len(extracted_files),
            }

        except zipfile.BadZipFile:
            return {
                "success": False,
                "error": "不是有效的ZIP文件",
                "file_path": zip_path,
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"ZIP解压失败: {str(e)}",
                "file_path": zip_path,
            }

    def _extract_tar(
        self, tar_path: str, extract_to: Optional[str] = None
    ) -> Dict[str, Any]:
        """解压TAR文件"""
        extract_to = extract_to or os.path.join(
            self.temp_folder, f"tar_extract_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )

        try:
            if tar_path.endswith(".tar.gz") or tar_path.endswith(".tgz"):
                with tarfile.open(tar_path, "r:*gz") as tar_ref:
                    tar_ref.extractall(extract_to)
                file_type = "tar.gz"
            else:
                with tarfile.open(tar_path, "r") as tar_ref:
                    tar_ref.extractall(extract_to)
                file_type = "tar"

            # 获取解压后的文件列表
            extracted_files = []
            for root, dirs, files in os.walk(extract_to):
                for file in files:
                    extracted_files.append(os.path.join(root, file))

            return {
                "success": True,
                "extracted_to": extract_to,
                "files": extracted_files,
                "file_type": file_type,
                "total_files": len(extracted_files),
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"TAR解压失败: {str(e)}",
                "file_path": tar_path,
            }

    def _move_file(self, src_path: str, dst_path: str) -> Dict[str, Any]:
        """移动文件到目标位置"""
        try:
            # 确保目标目录存在
            os.makedirs(os.path.dirname(dst_path), exist_ok=True)
            shutil.move(src_path, dst_path)

            return {"success": True, "moved_to": dst_path, "file_path": src_path}
        except Exception as e:
            self.logger.error(f"文件移动失败: {e}")
            return {
                "success": False,
                "error": f"文件移动失败: {str(e)}",
                "file_path": src_path,
            }

    def get_file_info(self, file_path: str) -> Dict[str, Any]:
        """获取文件信息"""
        try:
            file_path = Path(file_path)

            if not file_path.exists():
                return {
                    "success": False,
                    "error": "文件不存在",
                    "file_path": str(file_path),
                }

            stat_info = file_path.stat()

            return {
                "success": True,
                "file_path": str(file_path),
                "file_size": stat_info.st_size,
                "file_size_mb": round(stat_info.st_size / 1024 / 1024, 2),  # MB
                "modified_time": datetime.fromtimestamp(stat_info.st_mtime).isoformat(),
                "is_file": file_path.is_file(),
                "is_dir": file_path.is_dir(),
                "extension": file_path.suffix,
                "mime_type": self._get_mime_type(file_path.suffix),
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"获取文件信息失败: {str(e)}",
                "file_path": str(file_path),
            }

    def _get_mime_type(self, ext: str) -> str:
        """根据扩展名获取MIME类型"""
        mime_types = {
            ".txt": "text/plain",
            ".json": "application/json",
            ".yaml": "application/x-yaml",
            ".csv": "text/csv",
            ".py": "text/x-python",
            ".js": "application/javascript",
            ".ts": "application/typescript",
            ".java": "text/x-java",
            ".cpp": "text/x-c++",
            ".c": "text/x-c",
            ".h": "text/x-c",
            ".hpp": "text/x-c++",
            ".html": "text/html",
            ".css": "text/css",
            ".md": "text/markdown",
        }
        return mime_types.get(ext.lower(), "application/octet-stream")

    def create_project_folder(
        self, project_name: str, file_list: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """创建项目文件夹并组织文件结构"""
        try:
            project_root = os.path.join(self.temp_folder, project_name)
            os.makedirs(project_root, exist_ok=True)

            # 创建基本的目录结构
            os.makedirs(os.path.join(project_root, "src"), exist_ok=True)
            os.makedirs(os.path.join(project_root, "tests"), exist_ok=True)
            os.makedirs(os.path.join(project_root, "docs"), exist_ok=True)

            # 移动文件到项目文件夹
            moved_files = 0
            failed_files = []

            for file_info in file_list:
                src_path = None
                try:
                    src_path = file_info["file_path"]

                    # 确定目标路径
                    file_ext = os.path.splitext(src_path)[1].lower()
                    if file_ext in [
                        ".py",
                        ".js",
                        ".ts",
                        ".java",
                        ".cpp",
                        ".c",
                        ".h",
                        ".hpp",
                    ]:
                        # 代码文件放入src目录
                        dst_path = os.path.join(
                            project_root, "src", os.path.basename(src_path)
                        )
                    else:
                        # 其他文件放入docs目录
                        dst_path = os.path.join(
                            project_root, "docs", os.path.basename(src_path)
                        )

                    # 创建目标目录
                    os.makedirs(os.path.dirname(dst_path), exist_ok=True)

                    # 移动文件
                    shutil.move(src_path, dst_path)
                    moved_files += 1

                except Exception as e:
                    file_desc = src_path if src_path else str(file_info)
                    failed_files.append(f"{file_desc} ({e})")
                    self.logger.error(f"移动文件失败: {file_desc}")

            # 创建项目配置文件
            config_data = {
                "project": {
                    "id": project_name,
                    "name": project_name,
                    "created_at": datetime.now().isoformat(),
                    "file_count": moved_files,
                    "path": project_root,
                }
            }

            config_file = os.path.join(project_root, "project.json")
            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)

            return {
                "success": True,
                "project_id": project_name,
                "project_path": project_root,
                "moved_files": moved_files,
                "failed_files": failed_files,
                "total_files": len(file_list),
            }

        except Exception as e:
            self.logger.error(f"创建项目文件夹失败: {e}")
            return {"success": False, "error": f"创建项目文件夹失败: {e}"}

    def analyze_project_structure(self, project_id: str) -> Dict[str, Any]:
        """分析项目结构"""
        try:
            project_path = os.path.join(self.temp_folder, project_id)

            if not os.path.exists(project_path):
                return {
                    "success": False,
                    "error": f"项目ID {project_id} 不存在",
                    "project_id": project_id,
                }

            # 扫描文件
            files = []
            total_size = 0
            file_types = {}

            for root, dirs, filenames in os.walk(project_path):
                for filename in filenames:
                    file_path = os.path.join(root, filename)
                    rel_path = os.path.relpath(file_path, project_path)

                    file_size = os.path.getsize(file_path)
                    total_size += file_size

                    file_ext = os.path.splitext(filename)[1].lower()
                    file_types[file_ext] = file_types.get(file_ext, 0) + 1

                    files.append(
                        {
                            "path": rel_path,
                            "size": file_size,
                            "extension": file_ext,
                            "type": self._get_mime_type(file_ext),
                        }
                    )

            return {
                "success": True,
                "project_id": project_id,
                "analysis": {
                    "total_files": len(files),
                    "total_size": total_size,
                    "file_types": file_types,
                    "files": files,
                },
            }

        except Exception as e:
            self.logger.error(f"分析项目结构失败: {e}")
            return {
                "success": False,
                "error": f"分析项目结构失败: {e}",
                "project_id": project_id,
            }

    def get_project_info(self, project_id: str) -> Dict[str, Any]:
        """获取项目信息"""
        try:
            project_path = os.path.join(self.temp_folder, project_id)
            config_file = os.path.join(project_path, "project.json")

            if not os.path.exists(config_file):
                return {
                    "success": False,
                    "error": f"项目ID {project_id} 不存在",
                    "project_id": project_id,
                }

            with open(config_file, "r", encoding="utf-8") as f:
                config_data = json.load(f)

            return {
                "success": True,
                "project_id": project_id,
                "info": config_data.get("project", {}),
            }

        except Exception as e:
            self.logger.error(f"获取项目信息失败: {e}")
            return {
                "success": False,
                "error": f"获取项目信息失败: {e}",
                "project_id": project_id,
            }

    def get_project_files(self, project_id: str) -> List[Dict[str, Any]]:
        """获取项目文件列表"""
        try:
            project_path = os.path.join(self.temp_folder, project_id)

            if not os.path.exists(project_path):
                return []

            files = []
            for root, dirs, filenames in os.walk(project_path):
                for filename in filenames:
                    file_path = os.path.join(root, filename)
                    rel_path = os.path.relpath(file_path, project_path)

                    file_info = self.get_file_info(file_path)
                    file_info["relative_path"] = rel_path
                    files.append(file_info)

            return files

        except Exception as e:
            self.logger.error(f"获取项目文件列表失败: {e}")
            return []

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

            return {"success": True, "cleaned_count": cleaned_count}

        except Exception as e:
            self.logger.error(f"清理临时文件失败: {e}")
            return {"success": False, "error": f"清理临时文件失败: {e}"}

    def delete_project_folder(self, project_id: str) -> Dict[str, Any]:
        """删除项目文件夹"""
        try:
            project_path = os.path.join(self.temp_folder, project_id)

            if not os.path.exists(project_path):
                return {
                    "success": False,
                    "error": f"项目ID {project_id} 不存在",
                    "project_id": project_id,
                }

            shutil.rmtree(project_path)

            return {
                "success": True,
                "project_id": project_id,
                "deleted_path": project_path,
            }

        except Exception as e:
            self.logger.error(f"删除项目文件夹失败: {e}")
            return {
                "success": False,
                "error": f"删除项目文件夹失败: {e}",
                "project_id": project_id,
            }
