#!/usr/bin/env python3
"""
Dataset评估框架 - 主入口脚本

实现完全隔离的自动化评估，支持SWE-bench标准流程。
"""

import argparse
import asyncio
import json
import logging
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

# 添加Dataset目录到Python路径
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from core.evaluation import DatasetEvaluationFramework
from loaders.swe_bench import SWEBenchLiteLoader
from utils.config import Config
from utils.file_utils import setup_logging, create_secure_temp_filename


def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="Dataset评估框架 - 完全自动化的SWE-bench评估",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 生成预测文件
  python main.py --mode generate --dataset ./datasets/swe-bench-lite.jsonl --samples 10

  # 运行SWE-bench标准评估
  python main.py --mode evaluate --predictions ./datasets/predictions/test_predictions.jsonl

  # 完整流程（生成+评估）
  python main.py --mode complete --dataset ./datasets/swe-bench-lite.jsonl --samples 50
        """
    )

    parser.add_argument(
        "--mode",
        choices=["generate", "evaluate", "complete"],
        default="complete",
        help="运行模式：generate(生成预测)、evaluate(运行评估)、complete(完整流程)"
    )

    parser.add_argument(
        "--dataset",
        default="./datasets/swe-bench-lite.jsonl",
        help="SWE-bench数据集路径"
    )

    parser.add_argument(
        "--predictions",
        default="./datasets/predictions/test_predictions.jsonl",
        help="预测文件路径"
    )

    parser.add_argument(
        "--samples",
        type=int,
        default=10,
        help="处理的样本数量（用于测试）"
    )

    parser.add_argument(
        "--swe-bench-path",
        default="./datasets/SWE-bench",
        help="SWE-bench仓库路径"
    )

    parser.add_argument(
        "--testbed",
        default="./testbed",
        help="测试床目录"
    )

    parser.add_argument(
        "--log-dir",
        default="./logs",
        help="日志目录"
    )

    parser.add_argument(
        "--temp-dir",
        default="./temp",
        help="临时文件目录"
    )

    parser.add_argument(
        "--results-dir",
        default="./results",
        help="结果输出目录"
    )

    parser.add_argument(
        "--config",
        default="./config.json",
        help="配置文件路径"
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="启用调试模式"
    )

    return parser.parse_args()


async def generate_predictions(args: argparse.Namespace) -> bool:
    """生成预测文件"""
    try:
        # 设置日志
        logger = setup_logging(
            log_level=logging.DEBUG if args.debug else logging.INFO,
            log_dir=args.log_dir,
            mode="generate"
        )
        logger.info(f"开始生成预测文件，数据集: {args.dataset}")

        # 创建必要的目录
        Path(args.temp_dir).mkdir(parents=True, exist_ok=True)
        Path(args.predictions).parent.mkdir(parents=True, exist_ok=True)

        # 加载数据集
        loader = SWEBenchLiteLoader(args.dataset)
        tasks = loader.load_tasks(sample_size=args.samples)

        if not tasks:
            logger.error("未加载到任何任务")
            return False

        logger.info(f"加载了 {len(tasks)} 个任务")

        # 创建评估框架
        framework = DatasetEvaluationFramework(
            config_path=args.config,
            temp_dir=args.temp_dir,
            debug=args.debug
        )

        # 初始化框架
        if not await framework.initialize():
            logger.error("评估框架初始化失败")
            return False

        # 生成预测
        predictions = await framework.generate_predictions(tasks)

        # 保存预测文件
        loader.save_predictions(predictions, args.predictions)

        logger.info(f"预测文件已保存到: {args.predictions}")
        logger.info(f"成功生成 {len(predictions)} 个预测")

        return True

    except Exception as e:
        logger.error(f"生成预测文件时发生错误: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
        return False


async def run_evaluation(args: argparse.Namespace) -> bool:
    """运行SWE-bench标准评估"""
    try:
        # 设置日志
        logger = setup_logging(
            log_level=logging.DEBUG if args.debug else logging.INFO,
            log_dir=args.log_dir,
            mode="evaluate"
        )
        logger.info(f"开始运行SWE-bench评估，预测文件: {args.predictions}")

        # 验证预测文件存在
        if not Path(args.predictions).exists():
            logger.error(f"预测文件不存在: {args.predictions}")
            return False

        # 创建评估框架
        framework = DatasetEvaluationFramework(
            config_path=args.config,
            swe_bench_path=args.swe_bench_path,
            testbed_path=args.testbed,
            temp_dir=args.temp_dir,
            debug=args.debug
        )

        # 运行SWE-bench评估
        results = await framework.run_swe_bench_evaluation(
            predictions_path=args.predictions,
            log_dir=args.log_dir
        )

        # 保存结果
        results_file = Path(args.results_dir) / "evaluation_results.json"
        results_file.parent.mkdir(parents=True, exist_ok=True)

        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        logger.info(f"评估结果已保存到: {results_file}")

        # 生成报告
        await framework.generate_evaluation_report(results, args.results_dir)

        return True

    except Exception as e:
        logger.error(f"运行评估时发生错误: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
        return False


async def run_complete_workflow(args: argparse.Namespace) -> bool:
    """运行完整工作流程"""
    logger = setup_logging(
        log_level=logging.DEBUG if args.debug else logging.INFO,
        log_dir=args.log_dir,
        mode="complete"
    )

    logger.info("开始运行完整评估流程")

    # 第一步：生成预测
    logger.info("=== 第一步：生成预测文件 ===")
    success = await generate_predictions(args)

    if not success:
        logger.error("预测文件生成失败，终止流程")
        return False

    # 第二步：运行评估
    logger.info("=== 第二步：运行SWE-bench评估 ===")
    success = await run_evaluation(args)

    if success:
        logger.info("=== 完整流程执行成功 ===")
    else:
        logger.error("=== 评估阶段失败 ===")

    return success


async def main():
    """主函数"""
    args = parse_arguments()

    # 显示配置信息
    print("=" * 60)
    print("🚀 Dataset评估框架 - 完全自动化的SWE-bench评估")
    print("=" * 60)
    print(f"运行模式: {args.mode}")
    print(f"数据集: {args.dataset}")
    print(f"样本数量: {args.samples}")
    print(f"调试模式: {args.debug}")
    print("=" * 60)

    # 根据模式执行相应操作
    if args.mode == "generate":
        success = await generate_predictions(args)
    elif args.mode == "evaluate":
        success = await run_evaluation(args)
    elif args.mode == "complete":
        success = await run_complete_workflow(args)
    else:
        print(f"❌ 不支持的模式: {args.mode}")
        return 1

    if success:
        print("\n✅ 任务执行成功")
        return 0
    else:
        print("\n❌ 任务执行失败")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))