"""
文件备份管理器
负责在代码修复前创建文件备份并管理备份历史
"""

import os
import shutil
import json
import time
import hashlib
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from pathlib import Path

from ..utils.logger import get_logger
from ..utils.config import get_config_manager


@dataclass
class BackupMetadata:
    """备份元数据"""
    backup_id: str
    original_file_path: str
    backup_file_path: str
    timestamp: str
    file_hash: str
    file_size: int
    reason: str  # 备份原因
    fix_request_id: Optional[str] = None
    issues_fixed: List[str] = field(default_factory=list)
    created_by: str = "fix_system"
    additional_info: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BackupResult:
    """备份结果"""
    success: bool
    backup_id: str
    backup_path: str
    original_path: str
    file_size: int
    execution_time: float = 0.0
    error: Optional[str] = None
    metadata: Optional[BackupMetadata] = None


class BackupManager:
    """文件备份管理器"""

    def __init__(self, config_manager=None):
        """
        初始化备份管理器

        Args:
            config_manager: 配置管理器实例
        """
        self.config_manager = config_manager or get_config_manager()
        self.logger = get_logger()

        # 获取配置
        try:
            self.config = self.config_manager.get_section('backup')
        except:
            self.config = {}

        self.backup_dir = Path(self.config.get('backup_directory', '.fix_backups'))
        self.max_backups_per_file = self.config.get('max_backups_per_file', 10)
        self.backup_retention_days = self.config.get('backup_retention_days', 30)
        self.compress_backups = self.config.get('compress_backups', True)

        # 创建备份目录
        self.backup_dir.mkdir(exist_ok=True)
        self.metadata_file = self.backup_dir / 'backup_metadata.json'

        # 初始化元数据
        self._load_metadata()

        self.logger.info(f"BackupManager initialized with backup directory: {self.backup_dir}")

    def create_backup(self, file_path: str, reason: str = "pre_fix",
                     fix_request_id: Optional[str] = None,
                     issues_fixed: Optional[List[str]] = None) -> BackupResult:
        """
        创建文件备份

        Args:
            file_path: 要备份的文件路径
            reason: 备份原因
            fix_request_id: 关联的修复请求ID
            issues_fixed: 修复的问题列表

        Returns:
            备份结果
        """
        start_time = time.time()
        file_path = Path(file_path)

        self.logger.info(f"Creating backup for {file_path} (reason: {reason})")

        result = BackupResult(
            success=False,
            backup_id="",
            backup_path="",
            original_path=str(file_path),
            file_size=0
        )

        try:
            # 验证文件存在
            if not file_path.exists():
                result.error = f"Source file does not exist: {file_path}"
                return result

            # 生成备份ID和路径
            backup_id = self._generate_backup_id(file_path)
            backup_path = self._get_backup_path(file_path, backup_id)

            # 创建备份目录
            backup_path.parent.mkdir(parents=True, exist_ok=True)

            # 计算文件哈希
            file_hash = self._calculate_file_hash(file_path)
            file_size = file_path.stat().st_size

            # 检查是否已存在相同内容的备份
            existing_backup = self._find_existing_backup(file_path, file_hash)
            if existing_backup:
                self.logger.info(f"File already backed up with same content: {existing_backup.backup_id}")
                result.backup_id = existing_backup.backup_id
                result.backup_path = existing_backup.backup_file_path
                result.file_size = existing_backup.file_size
                result.success = True
                result.metadata = existing_backup
                result.execution_time = time.time() - start_time
                return result

            # 复制文件
            if self.compress_backups and file_size > 1024:  # 压缩大于1KB的文件
                backup_path = backup_path.with_suffix(backup_path.suffix + '.gz')
                self._create_compressed_backup(file_path, backup_path)
            else:
                shutil.copy2(file_path, backup_path)

            # 创建备份元数据
            metadata = BackupMetadata(
                backup_id=backup_id,
                original_file_path=str(file_path),
                backup_file_path=str(backup_path),
                timestamp=datetime.now().isoformat(),
                file_hash=file_hash,
                file_size=file_size,
                reason=reason,
                fix_request_id=fix_request_id,
                issues_fixed=issues_fixed or [],
                created_by="fix_system",
                additional_info={
                    "original_mtime": file_path.stat().st_mtime,
                    "compression": backup_path.suffix == '.gz'
                }
            )

            # 保存元数据
            self._save_backup_metadata(metadata)

            # 清理旧备份
            self._cleanup_old_backups(file_path)

            # 构建结果
            result.success = True
            result.backup_id = backup_id
            result.backup_path = str(backup_path)
            result.file_size = file_size
            result.metadata = metadata

            self.logger.info(f"Backup created successfully: {backup_path}")

        except Exception as e:
            result.error = str(e)
            self.logger.error(f"Failed to create backup for {file_path}: {e}")

        result.execution_time = time.time() - start_time
        return result

    def restore_backup(self, backup_id: str, target_path: Optional[str] = None) -> bool:
        """
        从备份恢复文件

        Args:
            backup_id: 备份ID
            target_path: 目标路径（可选，默认恢复到原位置）

        Returns:
            是否恢复成功
        """
        try:
            # 查找备份元数据
            metadata = self._get_backup_metadata(backup_id)
            if not metadata:
                self.logger.error(f"Backup not found: {backup_id}")
                return False

            backup_path = Path(metadata.backup_file_path)
            if not backup_path.exists():
                self.logger.error(f"Backup file not found: {backup_path}")
                return False

            # 确定目标路径
            target = Path(target_path) if target_path else Path(metadata.original_file_path)
            target.parent.mkdir(parents=True, exist_ok=True)

            # 恢复文件
            if backup_path.suffix == '.gz':
                self._restore_compressed_backup(backup_path, target)
            else:
                shutil.copy2(backup_path, target)

            # 恢复原始时间戳
            if 'original_mtime' in metadata.additional_info:
                os.utime(target, (target.stat().st_atime, metadata.additional_info['original_mtime']))

            self.logger.info(f"File restored from backup: {backup_id} -> {target}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to restore backup {backup_id}: {e}")
            return False

    def list_backups(self, file_path: Optional[str] = None, limit: int = 50) -> List[BackupMetadata]:
        """
        列出备份

        Args:
            file_path: 文件路径过滤（可选）
            limit: 返回数量限制

        Returns:
            备份元数据列表
        """
        try:
            backups = self.metadata.get('backups', [])

            # 按文件路径过滤
            if file_path:
                file_path = str(Path(file_path).resolve())
                backups = [b for b in backups if b['original_file_path'] == file_path]

            # 按时间戳排序（最新的在前）
            backups.sort(key=lambda x: x['timestamp'], reverse=True)

            # 限制数量
            backups = backups[:limit]

            # 转换为BackupMetadata对象
            return [self._dict_to_metadata(b) for b in backups]

        except Exception as e:
            self.logger.error(f"Failed to list backups: {e}")
            return []

    def delete_backup(self, backup_id: str) -> bool:
        """
        删除备份

        Args:
            backup_id: 备份ID

        Returns:
            是否删除成功
        """
        try:
            metadata = self._get_backup_metadata(backup_id)
            if not metadata:
                self.logger.error(f"Backup not found: {backup_id}")
                return False

            # 删除备份文件
            backup_path = Path(metadata.backup_file_path)
            if backup_path.exists():
                backup_path.unlink()

            # 从元数据中删除
            self.metadata['backups'] = [
                b for b in self.metadata['backups']
                if b['backup_id'] != backup_id
            ]
            self._save_metadata_file()

            self.logger.info(f"Backup deleted: {backup_id}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to delete backup {backup_id}: {e}")
            return False

    def cleanup_expired_backups(self) -> int:
        """
        清理过期备份

        Returns:
            删除的备份数量
        """
        deleted_count = 0
        cutoff_time = datetime.now().timestamp() - (self.backup_retention_days * 24 * 3600)

        try:
            backups_to_keep = []
            for backup_data in self.metadata.get('backups', []):
                backup_time = datetime.fromisoformat(backup_data['timestamp']).timestamp()

                if backup_time < cutoff_time:
                    # 删除过期备份文件
                    backup_path = Path(backup_data['backup_file_path'])
                    if backup_path.exists():
                        backup_path.unlink()
                        deleted_count += 1
                    self.logger.info(f"Deleted expired backup: {backup_data['backup_id']}")
                else:
                    backups_to_keep.append(backup_data)

            # 更新元数据
            self.metadata['backups'] = backups_to_keep
            self._save_metadata_file()

            self.logger.info(f"Cleanup completed, deleted {deleted_count} expired backups")

        except Exception as e:
            self.logger.error(f"Failed to cleanup expired backups: {e}")

        return deleted_count

    def get_backup_statistics(self) -> Dict[str, Any]:
        """
        获取备份统计信息

        Returns:
            备份统计信息
        """
        try:
            backups = self.metadata.get('backups', [])

            total_backups = len(backups)
            total_size = sum(b['file_size'] for b in backups)
            unique_files = len(set(b['original_file_path'] for b in backups))

            # 按原因统计
            reason_counts = {}
            for backup in backups:
                reason = backup['reason']
                reason_counts[reason] = reason_counts.get(reason, 0) + 1

            # 按日期统计
            date_counts = {}
            for backup in backups:
                date = backup['timestamp'][:10]  # YYYY-MM-DD
                date_counts[date] = date_counts.get(date, 0) + 1

            return {
                "total_backups": total_backups,
                "total_size_bytes": total_size,
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "unique_files": unique_files,
                "backup_directory": str(self.backup_dir),
                "reason_distribution": reason_counts,
                "daily_distribution": date_counts,
                "oldest_backup": min(b['timestamp'] for b in backups) if backups else None,
                "newest_backup": max(b['timestamp'] for b in backups) if backups else None
            }

        except Exception as e:
            self.logger.error(f"Failed to get backup statistics: {e}")
            return {}

    def _generate_backup_id(self, file_path: Path) -> str:
        """生成备份ID"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_hash = hashlib.md5(str(file_path).encode()).hexdigest()[:8]
        return f"backup_{timestamp}_{file_hash}"

    def _get_backup_path(self, file_path: Path, backup_id: str) -> Path:
        """获取备份文件路径"""
        # 保持相对路径结构
        relative_path = file_path.relative_to(Path.cwd())
        backup_dir = self.backup_dir / relative_path.parent
        return backup_dir / f"{relative_path.stem}_{backup_id}{relative_path.suffix}"

    def _calculate_file_hash(self, file_path: Path) -> str:
        """计算文件哈希"""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    def _find_existing_backup(self, file_path: Path, file_hash: str) -> Optional[BackupMetadata]:
        """查找已存在的相同内容备份"""
        file_path_str = str(file_path.resolve())

        for backup_data in self.metadata.get('backups', []):
            if (backup_data['original_file_path'] == file_path_str and
                backup_data['file_hash'] == file_hash):
                return self._dict_to_metadata(backup_data)

        return None

    def _create_compressed_backup(self, source: Path, target: Path):
        """创建压缩备份"""
        import gzip
        with open(source, 'rb') as f_in:
            with gzip.open(target, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)

    def _restore_compressed_backup(self, backup_path: Path, target: Path):
        """恢复压缩备份"""
        import gzip
        with gzip.open(backup_path, 'rb') as f_in:
            with open(target, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)

    def _cleanup_old_backups(self, file_path: Path):
        """清理文件的旧备份"""
        file_path_str = str(file_path.resolve())

        # 获取该文件的所有备份
        file_backups = [
            b for b in self.metadata.get('backups', [])
            if b['original_file_path'] == file_path_str
        ]

        # 按时间戳排序，保留最新的N个
        file_backups.sort(key=lambda x: x['timestamp'], reverse=True)

        backups_to_keep = file_backups[:self.max_backups_per_file]
        backups_to_delete = file_backups[self.max_backups_per_file:]

        # 删除多余备份
        for backup_data in backups_to_delete:
            try:
                backup_path = Path(backup_data['backup_file_path'])
                if backup_path.exists():
                    backup_path.unlink()

                # 从元数据中删除
                self.metadata['backups'].remove(backup_data)
                self.logger.info(f"Deleted old backup: {backup_data['backup_id']}")

            except Exception as e:
                self.logger.error(f"Failed to delete old backup {backup_data['backup_id']}: {e}")

        # 保存更新的元数据
        if backups_to_delete:
            self._save_metadata_file()

    def _load_metadata(self):
        """加载元数据"""
        try:
            if self.metadata_file.exists():
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    self.metadata = json.load(f)
            else:
                self.metadata = {
                    "version": "1.0",
                    "created_at": datetime.now().isoformat(),
                    "backups": []
                }
                self._save_metadata_file()
        except Exception as e:
            self.logger.error(f"Failed to load backup metadata: {e}")
            self.metadata = {"backups": []}

    def _save_metadata_file(self):
        """保存元数据文件"""
        try:
            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(self.metadata, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"Failed to save backup metadata: {e}")

    def _save_backup_metadata(self, metadata: BackupMetadata):
        """保存备份元数据"""
        try:
            backup_dict = {
                "backup_id": metadata.backup_id,
                "original_file_path": metadata.original_file_path,
                "backup_file_path": metadata.backup_file_path,
                "timestamp": metadata.timestamp,
                "file_hash": metadata.file_hash,
                "file_size": metadata.file_size,
                "reason": metadata.reason,
                "fix_request_id": metadata.fix_request_id,
                "issues_fixed": metadata.issues_fixed,
                "created_by": metadata.created_by,
                "additional_info": metadata.additional_info
            }

            self.metadata['backups'].append(backup_dict)
            self._save_metadata_file()

        except Exception as e:
            self.logger.error(f"Failed to save backup metadata: {e}")

    def _get_backup_metadata(self, backup_id: str) -> Optional[BackupMetadata]:
        """获取备份元数据"""
        for backup_data in self.metadata.get('backups', []):
            if backup_data['backup_id'] == backup_id:
                return self._dict_to_metadata(backup_data)
        return None

    def _dict_to_metadata(self, data: Dict[str, Any]) -> BackupMetadata:
        """将字典转换为BackupMetadata对象"""
        return BackupMetadata(
            backup_id=data['backup_id'],
            original_file_path=data['original_file_path'],
            backup_file_path=data['backup_file_path'],
            timestamp=data['timestamp'],
            file_hash=data['file_hash'],
            file_size=data['file_size'],
            reason=data['reason'],
            fix_request_id=data.get('fix_request_id'),
            issues_fixed=data.get('issues_fixed', []),
            created_by=data.get('created_by', 'fix_system'),
            additional_info=data.get('additional_info', {})
        )