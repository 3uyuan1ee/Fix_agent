"""
评估结果可视化工具

提供丰富的图表生成功能，用于可视化评估结果和分析数据。
"""

import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional
from pathlib import Path
import json
import warnings

# 忽略matplotlib的警告
warnings.filterwarnings('ignore')

class EvaluationVisualizer:
    """评估结果可视化器"""

    def __init__(self, results: List[Any] = None):
        """
        初始化可视化器

        Args:
            results: 评估结果列表
        """
        self.results = results or []
        self.df = None

        # 设置matplotlib中文字体支持
        plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'SimHei', 'Arial Unicode MS']
        plt.rcParams['axes.unicode_minus'] = False

        # 设置样式
        sns.set_style("whitegrid")
        sns.set_palette("husl")

    def generate_comprehensive_report(self, output_dir: str):
        """
        生成综合可视化报告

        Args:
            output_dir: 输出目录
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        print(f"[可视化] 生成报告到: {output_path}")

        # 生成各种图表
        self.plot_success_rate_analysis(output_path / "success_rate_analysis.png")
        self.plot_execution_time_distribution(output_path / "execution_time_analysis.png")
        self.plot_error_analysis(output_path / "error_analysis.png")
        self.plot_dataset_comparison(output_path / "dataset_comparison.png")

        # 生成HTML报告
        self.generate_html_report(output_path / "report.html")

    def plot_success_rate_analysis(self, save_path: str):
        """
        绘制成功率分析图

        Args:
            save_path: 保存路径
        """
        if not self.results:
            print("[可视化] 没有数据可绘制")
            return

        # 转换为DataFrame
        self.df = pd.DataFrame([{
            'task_id': r.task_id,
            'dataset_name': r.dataset_name,
            'success': r.success,
            'execution_time': r.execution_time,
            'error': r.error
        } for r in self.results])

        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        fig.suptitle('Success Rate Analysis', fontsize=16, fontweight='bold')

        # 1. 总体成功率饼图
        success_count = self.df['success'].sum()
        fail_count = len(self.df) - success_count

        axes[0, 0].pie([success_count, fail_count],
                       labels=['Success', 'Failure'],
                       autopct='%1.1f%%',
                       colors=['#2ecc71', '#e74c3c'])
        axes[0, 0].set_title('Overall Success Rate')

        # 2. 按数据集的成功率
        if 'dataset_name' in self.df.columns:
            dataset_success = self.df.groupby('dataset_name')['success'].mean().sort_values(ascending=False)
            bars = axes[0, 1].bar(range(len(dataset_success)), dataset_success.values)
            axes[0, 1].set_title('Success Rate by Dataset')
            axes[0, 1].set_ylabel('Success Rate')
            axes[0, 1].set_xticks(range(len(dataset_success)))
            axes[0, 1].set_xticklabels(dataset_success.index, rotation=45, ha='right')

            # 添加数值标签
            for bar, value in zip(bars, dataset_success.values):
                height = bar.get_height()
                axes[0, 1].text(bar.get_x() + bar.get_width()/2., height,
                               f'{value:.2%}', ha='center', va='bottom')

        # 3. 成功率与执行时间的关系
        axes[1, 0].scatter(self.df[self.df['success']]['execution_time'],
                          [1] * self.df[self.df['success']].shape[0],
                          color='green', alpha=0.6, label='Success')
        axes[1, 0].scatter(self.df[~self.df['success']]['execution_time'],
                          [1] * self.df[~self.df['success']].shape[0],
                          color='red', alpha=0.6, label='Failure')
        axes[1, 0].set_xlabel('Execution Time (seconds)')
        axes[1, 0].set_ylabel('Success/Failure')
        axes[1, 0].set_title('Success vs Execution Time')
        axes[1, 0].legend()

        # 4. 执行时间分布直方图
        axes[1, 1].hist(self.df['execution_time'], bins=30, alpha=0.7, color='skyblue')
        axes[1, 1].set_xlabel('Execution Time (seconds)')
        axes[1, 1].set_ylabel('Frequency')
        axes[1, 1].set_title('Execution Time Distribution')

        plt.tight_layout()
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()

    def plot_execution_time_analysis(self, save_path: str):
        """
        绘制执行时间分析图

        Args:
            save_path: 保存路径
        """
        if self.df is None or self.df.empty:
            return

        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        fig.suptitle('Execution Time Analysis', fontsize=16, fontweight='bold')

        # 1. 执行时间箱线图
        if 'dataset_name' in self.df.columns:
            self.df.boxplot(column='execution_time', by='dataset_name', ax=axes[0, 0])
            axes[0, 0].set_title('Execution Time by Dataset')
            axes[0, 0].set_ylabel('Execution Time (seconds)')
        else:
            axes[0, 0].boxplot(self.df['execution_time'])
            axes[0, 0].set_title('Execution Time Distribution')
            axes[0, 0].set_ylabel('Execution Time (seconds)')

        # 2. 成功vs失败执行时间对比
        success_times = self.df[self.df['success']]['execution_time']
        fail_times = self.df[~self.df['success']]['execution_time']

        axes[0, 1].boxplot([success_times, fail_times], labels=['Success', 'Failure'])
        axes[0, 1].set_title('Execution Time: Success vs Failure')
        axes[0, 1].set_ylabel('Execution Time (seconds)')

        # 3. 执行时间累积分布
        sorted_times = np.sort(self.df['execution_time'])
        cumulative = np.arange(1, len(sorted_times) + 1) / len(sorted_times)
        axes[1, 0].plot(sorted_times, cumulative, linewidth=2)
        axes[1, 0].set_xlabel('Execution Time (seconds)')
        axes[1, 0].set_ylabel('Cumulative Probability')
        axes[1, 0].set_title('Execution Time CDF')
        axes[1, 0].grid(True)

        # 4. 时间区间统计
        time_bins = [0, 30, 60, 120, 300, float('inf')]
        time_labels = ['<30s', '30-60s', '60-120s', '120-300s', '>300s']
        time_groups = pd.cut(self.df['execution_time'], bins=time_bins, labels=time_labels, right=False)
        time_counts = time_groups.value_counts().sort_index()

        bars = axes[1, 1].bar(time_labels, time_counts.values, color='steelblue')
        axes[1, 1].set_title('Execution Time Distribution')
        axes[1, 1].set_xlabel('Time Range')
        axes[1, 1].set_ylabel('Count')

        # 添加数值标签
        for bar, count in zip(bars, time_counts.values):
            height = bar.get_height()
            axes[1, 1].text(bar.get_x() + bar.get_width()/2., height,
                           str(count), ha='center', va='bottom')

        plt.tight_layout()
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()

    def plot_error_analysis(self, save_path: str):
        """
        绘制错误分析图

        Args:
            save_path: 保存路径
        """
        if self.df is None or self.df.empty:
            return

        # 过滤出失败的记录
        failed_df = self.df[~self.df['success']].copy()

        if failed_df.empty:
            # 如果没有失败，创建一个空图
            plt.figure(figsize=(12, 8))
            plt.text(0.5, 0.5, 'No failures to analyze',
                    ha='center', va='center', transform=plt.gca().transAxes,
                    fontsize=20)
            plt.title('Error Analysis')
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            plt.close()
            return

        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        fig.suptitle('Error Analysis', fontsize=16, fontweight='bold')

        # 1. 错误类型统计（如果有错误信息）
        if 'error' in failed_df.columns:
            error_counts = failed_df['error'].value_counts().head(10)

            if not error_counts.empty:
                y_pos = range(len(error_counts))
                bars = axes[0, 0].barh(y_pos, error_counts.values, color='coral')
                axes[0, 0].set_yticks(y_pos)
                axes[0, 0].set_yticklabels([e[:30] + '...' if len(e) > 30 else e
                                           for e in error_counts.index])
                axes[0, 0].set_xlabel('Count')
                axes[0, 0].set_title('Top 10 Error Types')

                # 添加数值标签
                for bar, count in zip(bars, error_counts.values):
                    width = bar.get_width()
                    axes[0, 0].text(width, bar.get_y() + bar.get_height()/2.,
                                   str(count), ha='left', va='center')

        # 2. 按数据集的错误分布
        if 'dataset_name' in failed_df.columns:
            dataset_errors = failed_df['dataset_name'].value_counts()
            axes[0, 1].pie(dataset_errors.values, labels=dataset_errors.index, autopct='%1.1f%%')
            axes[0, 1].set_title('Error Distribution by Dataset')

        # 3. 失败任务的执行时间分布
        axes[1, 0].hist(failed_df['execution_time'], bins=20, alpha=0.7, color='orange')
        axes[1, 0].set_xlabel('Execution Time (seconds)')
        axes[1, 0].set_ylabel('Count')
        axes[1, 0].set_title('Failed Tasks Execution Time')

        # 4. 成功率和错误率对比
        if 'dataset_name' in failed_df.columns:
            total_by_dataset = self.df['dataset_name'].value_counts()
            failed_by_dataset = failed_df['dataset_name'].value_counts()

            datasets = total_by_dataset.index
            success_rates = []
            error_rates = []

            for dataset in datasets:
                total = total_by_dataset[dataset]
                failed = failed_by_dataset.get(dataset, 0)
                success_rates.append((total - failed) / total * 100)
                error_rates.append(failed / total * 100)

            x = np.arange(len(datasets))
            width = 0.35

            axes[1, 1].bar(x - width/2, success_rates, width, label='Success Rate', color='green')
            axes[1, 1].bar(x + width/2, error_rates, width, label='Error Rate', color='red')

            axes[1, 1].set_xlabel('Dataset')
            axes[1, 1].set_ylabel('Percentage')
            axes[1, 1].set_title('Success vs Error Rate by Dataset')
            axes[1, 1].set_xticks(x)
            axes[1, 1].set_xticklabels(datasets, rotation=45, ha='right')
            axes[1, 1].legend()

        plt.tight_layout()
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()

    def plot_dataset_comparison(self, save_path: str):
        """
        绘制数据集对比图

        Args:
            save_path: 保存路径
        """
        if self.df is None or self.df.empty:
            return

        if 'dataset_name' not in self.df.columns:
            # 如果没有多个数据集，跳过
            return

        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        fig.suptitle('Dataset Comparison', fontsize=16, fontweight='bold')

        # 1. 任务数量对比
        task_counts = self.df['dataset_name'].value_counts()
        bars = axes[0, 0].bar(task_counts.index, task_counts.values, color='skyblue')
        axes[0, 0].set_title('Task Count by Dataset')
        axes[0, 0].set_ylabel('Number of Tasks')
        axes[0, 0].tick_params(axis='x', rotation=45)

        # 添加数值标签
        for bar, count in zip(bars, task_counts.values):
            height = bar.get_height()
            axes[0, 0].text(bar.get_x() + bar.get_width()/2., height,
                           str(count), ha='center', va='bottom')

        # 2. 成功率对比
        success_rates = self.df.groupby('dataset_name')['success'].mean()
        bars = axes[0, 1].bar(success_rates.index, success_rates.values, color='lightgreen')
        axes[0, 1].set_title('Success Rate by Dataset')
        axes[0, 1].set_ylabel('Success Rate')
        axes[0, 1].tick_params(axis='x', rotation=45)
        axes[0, 1].set_ylim(0, 1)

        # 添加数值标签
        for bar, rate in zip(bars, success_rates.values):
            height = bar.get_height()
            axes[0, 1].text(bar.get_x() + bar.get_width()/2., height,
                           f'{rate:.2%}', ha='center', va='bottom')

        # 3. 平均执行时间对比
        avg_times = self.df.groupby('dataset_name')['execution_time'].mean()
        bars = axes[1, 0].bar(avg_times.index, avg_times.values, color='orange')
        axes[1, 0].set_title('Average Execution Time by Dataset')
        axes[1, 0].set_ylabel('Execution Time (seconds)')
        axes[1, 0].tick_params(axis='x', rotation=45)

        # 添加数值标签
        for bar, time_val in zip(bars, avg_times.values):
            height = bar.get_height()
            axes[1, 0].text(bar.get_x() + bar.get_width()/2., height,
                           f'{time_val:.1f}s', ha='center', va='bottom')

        # 4. 综合指标雷达图
        if len(task_counts) <= 5:  # 只在数据集数量较少时绘制雷达图
            categories = ['Task Count', 'Success Rate', 'Speed', 'Consistency']

            # 标准化指标（0-1范围）
            max_tasks = task_counts.max()
            max_time = avg_times.max()

            dataset_metrics = {}
            for dataset in task_counts.index:
                dataset_data = self.df[self.df['dataset_name'] == dataset]

                metrics = [
                    task_counts[dataset] / max_tasks,  # 任务数量（标准化）
                    dataset_data['success'].mean(),   # 成功率
                    1 - (avg_times[dataset] / max_time),  # 速度（时间越短越好）
                    1 - dataset_data['execution_time'].std() / dataset_data['execution_time'].mean()  # 一致性
                ]
                dataset_metrics[dataset] = metrics

            # 绘制雷达图
            angles = np.linspace(0, 2 * np.pi, len(categories), endpoint=False).tolist()
            angles += angles[:1]  # 闭合图形

            axes[1, 1].remove()
            axes[1, 1] = fig.add_subplot(2, 2, 4, projection='polar')

            colors = plt.cm.Set3(np.linspace(0, 1, len(dataset_metrics)))

            for i, (dataset, metrics) in enumerate(dataset_metrics.items()):
                values = metrics + metrics[:1]  # 闭合图形
                axes[1, 1].plot(angles, values, 'o-', linewidth=2, label=dataset, color=colors[i])
                axes[1, 1].fill(angles, values, alpha=0.25, color=colors[i])

            axes[1, 1].set_xticks(angles[:-1])
            axes[1, 1].set_xticklabels(categories)
            axes[1, 1].set_ylim(0, 1)
            axes[1, 1].set_title('Dataset Performance Radar')
            axes[1, 1].legend(loc='upper right', bbox_to_anchor=(1.3, 1.0))

        plt.tight_layout()
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()

    def generate_html_report(self, save_path: str):
        """
        生成HTML报告

        Args:
            save_path: HTML文件保存路径
        """
        if self.df is None or self.df.empty:
            return

        # 基础统计
        total_tasks = len(self.df)
        success_count = self.df['success'].sum()
        success_rate = success_count / total_tasks
        avg_time = self.df['execution_time'].mean()

        # 生成HTML内容
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Evaluation Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ text-align: center; color: #333; }}
                .summary {{ background: #f5f5f5; padding: 15px; border-radius: 5px; margin: 20px 0; }}
                .image {{ text-align: center; margin: 20px 0; }}
                .image img {{ max-width: 100%; height: auto; border: 1px solid #ddd; }}
                table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Fix Agent Evaluation Report</h1>
                <p>Generated on {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>

            <div class="summary">
                <h2>Summary</h2>
                <ul>
                    <li><strong>Total Tasks:</strong> {total_tasks}</li>
                    <li><strong>Successful Tasks:</strong> {success_count}</li>
                    <li><strong>Success Rate:</strong> {success_rate:.2%}</li>
                    <li><strong>Average Execution Time:</strong> {avg_time:.2f} seconds</li>
                </ul>
            </div>

            <div class="image">
                <h2>Success Rate Analysis</h2>
                <img src="success_rate_analysis.png" alt="Success Rate Analysis">
            </div>

            <div class="image">
                <h2>Execution Time Analysis</h2>
                <img src="execution_time_analysis.png" alt="Execution Time Analysis">
            </div>

            <div class="image">
                <h2>Error Analysis</h2>
                <img src="error_analysis.png" alt="Error Analysis">
            </div>

            <div class="image">
                <h2>Dataset Comparison</h2>
                <img src="dataset_comparison.png" alt="Dataset Comparison">
            </div>
        </body>
        </html>
        """

        with open(save_path, 'w', encoding='utf-8') as f:
            f.write(html_content)

        print(f"[可视化] HTML报告已生成: {save_path}")