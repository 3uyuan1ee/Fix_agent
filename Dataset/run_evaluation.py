#!/usr/bin/env python3
"""
Fix Agent 数据集评估主脚本

这个脚本提供了完整的评估流程，支持SWE-bench和BugsInPy数据集。
使用方法：
    python run_evaluation.py --dataset swe-bench --samples 50
    python run_evaluation.py --dataset bugsinpy --samples 30 --difficulty medium
"""

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

# 添加Dataset模块到Python路径
dataset_root = Path(__file__).parent
sys.path.insert(0, str(dataset_root))

# 添加项目根目录到Python路径（用于导入src模块）
project_root = dataset_root.parent
sys.path.insert(0, str(project_root / "src"))

# 使用统一的导入处理
try:
    from core.evaluation import EvaluationFramework
    from loaders.bugs_in_py import BugsInPyLoader
    from loaders.swe_bench import SWEBenchLoader

    from utils.metrics import MetricsCalculator
    from utils.visualization import EvaluationVisualizer

    print("[主程序] 使用完整版工具")
except ImportError as e:
    print(f"[主程序] 导入警告: {e}")
    # 尝试使用简化版本
    try:
        from core.evaluation import EvaluationFramework
        from loaders.bugs_in_py import BugsInPyLoader
        from loaders.swe_bench import SWEBenchLoader

        from utils.metrics_simple import MetricsCalculator
        from utils.visualization_simple import EvaluationVisualizer

        print("[主程序] 使用简化版工具")
    except ImportError as e2:
        print(f"[主程序] 导入错误: {e2}")
        raise


def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="Fix Agent 数据集评估工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  # 评估SWE-bench数据集（50个样本）
  python run_evaluation.py --dataset swe-bench --samples 50

  # 评估BugsInPy数据集（中等难度，30个样本）
  python run_evaluation.py --dataset bugsinpy --samples 30 --difficulty medium

  # 并行评估（8个工作线程）
  python run_evaluation.py --dataset swe-bench --samples 100 --workers 8

  # 生成详细报告和可视化
  python run_evaluation.py --dataset swe-bench --samples 50 --generate-report --visualize
        """,
    )

    parser.add_argument(
        "--dataset",
        choices=["swe-bench", "bugsinpy", "all"],
        default="swe-bench",
        help="选择要评估的数据集",
    )

    parser.add_argument(
        "--samples", type=int, default=10, help="评估样本数量（默认：10）"
    )

    parser.add_argument(
        "--workers", type=int, default=4, help="并行工作线程数（默认：4）"
    )

    parser.add_argument(
        "--difficulty",
        choices=["easy", "medium", "hard"],
        help="难度过滤器（仅适用于SWE-bench）",
    )

    parser.add_argument("--bug-type", help="Bug类型过滤器（仅适用于BugsInPy）")

    parser.add_argument(
        "--dataset-path",
        default="./datasets",
        help="数据集存储路径（默认：./datasets）",
    )

    parser.add_argument(
        "--output-dir",
        default="./evaluation_results",
        help="结果输出目录（默认：./evaluation_results）",
    )

    parser.add_argument(
        "--generate-report", action="store_true", help="生成详细的评估报告"
    )

    parser.add_argument("--visualize", action="store_true", help="生成可视化图表")

    parser.add_argument("--config", help="评估配置文件路径（JSON格式）")

    parser.add_argument("--model", help="使用的模型名称（如：gpt-4, claude-3-sonnet）")

    parser.add_argument(
        "--timeout", type=int, default=300, help="单个任务超时时间（秒，默认：300）"
    )

    parser.add_argument(
        "--debug", action="store_true", help="启用调试模式，输出详细信息"
    )

    return parser.parse_args()


async def load_dataset(args) -> List[Any]:
    """加载数据集任务"""
    tasks = []

    if args.dataset == "all" or args.dataset == "swe-bench":
        print("\n[主程序] 加载SWE-bench数据集...")
        swe_loader = SWEBenchLoader(str(Path(args.dataset_path) / "swe-bench"))

        # 下载数据集（如果需要）
        if not swe_loader.validate_dataset():
            print("[主程序] SWE-bench数据集不存在，开始下载...")
            if not swe_loader.download_dataset():
                print("[主程序] SWE-bench数据集下载失败")
                return None
        else:
            print("[主程序] SWE-bench数据集已存在")

        # 加载任务
        swe_tasks = swe_loader.load_tasks(
            sample_size=args.samples, difficulty_filter=args.difficulty
        )
        tasks.extend(swe_tasks)
        print(f"[主程序] SWE-bench：加载了 {len(swe_tasks)} 个任务")

    if args.dataset == "all" or args.dataset == "bugsinpy":
        print("\n[主程序] 加载BugsInPy数据集...")
        bugs_loader = BugsInPyLoader(str(Path(args.dataset_path) / "BugsInPy"))

        # 下载数据集（如果需要）
        if not bugs_loader.validate_dataset():
            print("[主程序] BugsInPy数据集不存在，开始下载...")
            if not bugs_loader.download_dataset():
                print("[主程序] BugsInPy数据集下载失败")
                return None
        else:
            print("[主程序] BugsInPy数据集已存在")

        # 加载任务
        bug_tasks = bugs_loader.load_tasks(
            sample_size=args.samples if args.dataset != "all" else args.samples // 2,
            bug_type_filter=args.bug_type,
        )
        tasks.extend(bug_tasks)
        print(f"[主程序] BugsInPy：加载了 {len(bug_tasks)} 个任务")

    return tasks


def load_config(config_path: str) -> Dict[str, Any]:
    """加载配置文件"""
    if not config_path or not Path(config_path).exists():
        return {}

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[主程序] 配置文件加载失败: {e}")
        return {}


def progress_callback(current: int, total: int, task, result):
    """进度回调函数"""
    progress = (current / total) * 100
    status = "成功" if result.success else "失败"
    print(f"[进度] {current}/{total} ({progress:.1f}%) - 任务 {task.task_id}: {status}")


def print_evaluation_summary(summary):
    """打印评估摘要"""
    print("\n" + "=" * 80)
    print("评估结果摘要")
    print("=" * 80)
    print(f"数据集: {summary.dataset_name}")
    print(f"总任务数: {summary.total_tasks}")
    print(f"成功任务数: {summary.successful_tasks}")
    print(f"失败任务数: {summary.failed_tasks}")
    print(f"成功率: {summary.success_rate:.2%}")
    print(f"平均执行时间: {summary.average_execution_time:.2f}秒")
    print(f"每小时处理任务数: {summary.tasks_per_hour:.1f}")
    print(f"总评估时间: {summary.total_execution_time:.2f}秒")

    if summary.error_analysis.get("total_errors", 0) > 0:
        print(f"\n错误分析:")
        print(f"  总错误数: {summary.error_analysis['total_errors']}")
        most_common = summary.error_analysis.get("most_common_errors", [])[:3]
        for error, count in most_common:
            print(f"  - {error}: {count}次")

    print("=" * 80)


async def main():
    """主函数"""
    print("Fix Agent 数据集评估工具")
    print("=" * 50)

    # 解析命令行参数
    args = parse_arguments()

    if args.debug:
        print(f"[调试] 命令行参数: {args}")

    # 加载配置
    config = load_config(args.config)
    if args.model:
        config.setdefault("agent", {})["model"] = args.model

    print(
        f"[主程序] 配置: 模型={config.get('agent', {}).get('model', 'default')}, "
        f"超时={args.timeout}秒, 工作线程={args.workers}"
    )

    # 创建输出目录
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        # 加载数据集
        tasks = await load_dataset(args)
        if not tasks:
            print("[主程序] 没有可用的评估任务")
            return 1

        print(f"\n[主程序] 总共加载了 {len(tasks)} 个评估任务")

        # 显示数据集信息
        datasets = set(task.dataset_name for task in tasks)
        print(f"[主程序] 涉及数据集: {', '.join(datasets)}")

        # 初始化评估框架
        print(f"\n[主程序] 初始化评估框架...")
        framework = EvaluationFramework(config)
        if not await framework.initialize():
            print("[主程序] 评估框架初始化失败")
            return 1

        # 运行评估
        print(f"\n[主程序] 开始评估...")
        start_time = time.time()

        try:
            summary = await framework.evaluate_dataset(
                tasks=tasks,
                max_workers=args.workers,
                progress_callback=progress_callback if not args.debug else None,
            )

            execution_time = time.time() - start_time
            print(f"\n[主程序] 评估完成，耗时: {execution_time:.2f}秒")

            # 打印摘要
            print_evaluation_summary(summary)

            # 生成详细报告
            if args.generate_report:
                print(f"\n[主程序] 生成详细报告...")
                metrics_calc = MetricsCalculator()

                # 获取详细结果（这里需要从framework获取）
                # 简化处理，实际应该从framework.results获取
                detailed_results = []  # 这里需要获取实际结果

                if detailed_results:
                    report = metrics_calc.generate_comprehensive_report(
                        detailed_results
                    )

                    # 保存报告
                    report_file = (
                        output_dir / f"detailed_report_{int(time.time())}.json"
                    )
                    with open(report_file, "w", encoding="utf-8") as f:
                        json.dump(report, f, indent=2, ensure_ascii=False, default=str)
                    print(f"[主程序] 详细报告已保存: {report_file}")

                    # 生成可视化
                    if args.visualize:
                        print(f"[主程序] 生成可视化图表...")
                        visualizer = EvaluationVisualizer(detailed_results)

                        viz_dir = output_dir / "visualizations"
                        visualizer.generate_comprehensive_report(str(viz_dir))

            # 保存评估摘要
            summary_file = output_dir / f"summary_{int(time.time())}.json"
            with open(summary_file, "w", encoding="utf-8") as f:
                json.dump(
                    summary.__dict__, f, indent=2, ensure_ascii=False, default=str
                )
            print(f"[主程序] 评估摘要已保存: {summary_file}")

            return 0 if summary.success_rate > 0 else 1

        finally:
            # 清理资源
            await framework.cleanup()

    except KeyboardInterrupt:
        print(f"\n[主程序] 评估被用户中断")
        return 1
    except Exception as e:
        print(f"\n[主程序] 评估过程中发生错误: {e}")
        if args.debug:
            import traceback

            traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
