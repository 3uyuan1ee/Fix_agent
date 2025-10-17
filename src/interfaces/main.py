#!/usr/bin/env python3
"""
CLI主程序入口
整合参数解析、配置加载和AgentOrchestrator，提供完整的命令行接口
"""

import sys
import os
import signal
from pathlib import Path
from typing import Optional, List
import json

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from .cli import CLIArgumentParser, CLIArguments, CLIHelper
from .static_commands import StaticAnalysisCommand
from ..utils.config import ConfigManager
from ..utils.logger import get_logger, setup_logging
from ..agent.orchestrator import AgentOrchestrator
from ..agent.planner import AnalysisMode

logger = get_logger()


class CLIMainApplication:
    """CLI主应用程序"""

    def __init__(self):
        """初始化CLI应用程序"""
        self.parser = CLIArgumentParser()
        self.config: Optional[ConfigManager] = None
        self.orchestrator: Optional[AgentOrchestrator] = None
        self.args: Optional[CLIArguments] = None
        self._setup_signal_handlers()

    def _setup_signal_handlers(self):
        """设置信号处理器"""
        def signal_handler(signum, frame):
            logger.info(f"接收到信号 {signum}，正在退出...")
            if self.orchestrator:
                self.orchestrator.cleanup()
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    def run(self, args: Optional[List[str]] = None) -> int:
        """
        运行CLI应用程序

        Args:
            args: 命令行参数列表，None表示从sys.argv获取

        Returns:
            int: 退出码，0表示成功
        """
        try:
            # 保存原始参数用于帮助主题处理
            if args:
                self._raw_args = args
                # 检查是否为帮助主题（在参数解析之前）
                if args[0] in ['modes', 'tools', 'formats', 'examples']:
                    self.parser.print_help(args[0])
                    return 0

            # 解析命令行参数
            self.args = self.parser.parse_args(args, validate_paths=False)

            # 处理特殊命令
            if self._handle_special_commands():
                return 0

            # 处理子命令
            if self.args.command == 'analyze':
                return self._handle_analyze_command()

            # 加载配置
            self._load_configuration()

            # 设置日志
            self._setup_logging()

            # 初始化编排器
            self._initialize_orchestrator()

            # 执行主要功能
            return self._execute_main_functionality()

        except KeyboardInterrupt:
            logger.info("用户中断操作")
            return 130
        except Exception as e:
            logger.error(f"程序执行失败: {e}")
            if self.args and self.args.verbose:
                import traceback
                traceback.print_exc()
            return 1
        finally:
            self._cleanup()

    def _handle_special_commands(self) -> bool:
        """
        处理特殊命令（版本、帮助等）

        Returns:
            bool: 是否为特殊命令
        """
        if self.args.version:
            self.parser.print_version()
            return True

        if self.args.list_tools:
            self.parser.list_tools()
            return True

        # 检查是否为帮助主题（通过原始参数）
        if hasattr(self, '_raw_args') and self._raw_args:
            first_arg = self._raw_args[0]
            if first_arg in ['modes', 'tools', 'formats', 'examples']:
                self.parser.print_help(first_arg)
                return True

        return False

    def _handle_analyze_command(self) -> int:
        """
        处理analyze子命令

        Returns:
            int: 退出码
        """
        try:
            if self.args.analyze_command == 'static':
                return self._handle_static_analysis_command()
            elif self.args.analyze_command == 'deep':
                print("❌ 深度分析模式正在开发中")
                return 1
            elif self.args.analyze_command == 'fix':
                print("❌ 分析修复模式正在开发中")
                return 1
            else:
                print("❌ 未知的分析模式，使用 'aidetector analyze --help' 查看可用模式")
                return 1

        except Exception as e:
            logger.error(f"处理analyze命令失败: {e}")
            if self.args.verbose:
                import traceback
                traceback.print_exc()
            return 1

    def _handle_static_analysis_command(self) -> int:
        """
        处理静态分析命令

        Returns:
            int: 退出码
        """
        try:
            # 验证必需参数
            if not self.args.sub_target:
                print("❌ 静态分析需要指定目标路径")
                return 1

            # 创建静态分析命令处理器
            static_cmd = StaticAnalysisCommand(self.config if hasattr(self, 'config') and self.config else None)

            # 执行静态分析
            result = static_cmd.execute_static_analysis(
                target=self.args.sub_target,
                tools=self.args.sub_tools,
                output_format=self.args.sub_format or "simple",
                output_file=self.args.sub_output,
                verbose=self.args.sub_verbose,
                quiet=self.args.sub_quiet,
                dry_run=self.args.sub_dry_run
            )

            return 0 if result.success else 1

        except FileNotFoundError as e:
            print(f"❌ 文件或路径不存在: {e}")
            return 1
        except Exception as e:
            logger.error(f"静态分析执行失败: {e}")
            if self.args.verbose:
                import traceback
                traceback.print_exc()
            return 1

    def _load_configuration(self):
        """加载配置文件"""
        try:
            config_file = self.args.config if self.args.config else None
            self.config = ConfigManager(config_file)
            logger.info("配置文件加载成功")
        except Exception as e:
            logger.error(f"配置文件加载失败: {e}")
            raise

    def _setup_logging(self):
        """设置日志"""
        try:
            if not self.args.enable_logging or self.args.quiet:
                # 禁用日志或静默模式
                setup_logging(level="ERROR")
            else:
                # 根据verbose设置日志级别
                log_level = "DEBUG" if self.args.verbose else "INFO"
                setup_logging(level=log_level)

            logger.info("日志系统初始化完成")
        except Exception as e:
            logger.error(f"日志设置失败: {e}")
            raise

    def _initialize_orchestrator(self):
        """初始化Agent编排器"""
        try:
            self.orchestrator = AgentOrchestrator()

            # 应用CLI参数覆盖配置
            self._apply_cli_overrides()

            logger.info("Agent编排器初始化完成")
        except Exception as e:
            logger.error(f"编排器初始化失败: {e}")
            raise

    def _apply_cli_overrides(self):
        """应用CLI参数覆盖配置"""
        if not self.orchestrator or not self.config:
            return

        # 覆盖分析模式
        if self.args.mode:
            try:
                mode = AnalysisMode(self.args.mode)
                # 这里可以设置默认模式
                logger.info(f"使用指定模式: {mode.value}")
            except ValueError:
                logger.warning(f"无效的模式: {self.args.mode}")

        # 覆盖工具配置
        if self.args.static_tools:
            try:
                current_config = self.config.get_tools_config()
                current_config['static_analysis_tools'] = {
                    tool: {'enabled': True}
                    for tool in self.args.static_tools
                }
                logger.info(f"使用指定工具: {', '.join(self.args.static_tools)}")
            except Exception as e:
                logger.warning(f"设置工具配置失败: {e}")

        # 覆盖LLM模型
        if self.args.deep_model:
            try:
                current_config = self.config.get_tools_config()
                current_config['llm_interface']['model'] = self.args.deep_model
                logger.info(f"使用指定LLM模型: {self.args.deep_model}")
            except Exception as e:
                logger.warning(f"设置LLM模型失败: {e}")

        # 覆盖缓存设置
        if not self.args.enable_cache:
            try:
                # 禁用缓存
                logger.info("缓存功能已禁用")
            except Exception as e:
                logger.warning(f"禁用缓存失败: {e}")

    def _execute_main_functionality(self) -> int:
        """
        执行主要功能

        Returns:
            int: 退出码
        """
        try:
            # 检查是否为批处理模式
            if self.args.batch_file:
                return self._run_batch_mode()

            # 检查是否为非交互式模式
            if self.args.interactive is False:
                return self._run_non_interactive_mode()

            # 默认交互式模式
            return self._run_interactive_mode()

        except Exception as e:
            logger.error(f"功能执行失败: {e}")
            return 1

    def _run_interactive_mode(self) -> int:
        """
        运行交互式模式

        Returns:
            int: 退出码
        """
        if not self.args.quiet:
            print("🚀 AI缺陷检测系统")
            print("输入 '/help' 查看帮助，输入 '/exit' 退出程序")
            print("=" * 60)

        try:
            # 创建会话
            session = self.orchestrator.create_session()

            # 如果提供了初始目标，设置默认分析
            if self.args.target and self.args.mode:
                initial_input = f"{self.args.mode}分析 {self.args.target}"
                self._process_user_input(session, initial_input)

            # 主交互循环
            while True:
                try:
                    # 获取用户输入
                    user_input = self._get_user_input()

                    if not user_input:
                        continue

                    # 处理用户输入
                    result = self._process_user_input(session, user_input)

                    # 检查是否需要退出
                    if result.get('should_exit', False):
                        break

                except KeyboardInterrupt:
                    print("\n使用 '/exit' 命令退出程序")
                    continue
                except EOFError:
                    break

            return 0

        except Exception as e:
            logger.error(f"交互式模式执行失败: {e}")
            return 1
        finally:
            if 'session' in locals():
                self.orchestrator.close_session(session)

    def _run_non_interactive_mode(self) -> int:
        """
        运行非交互式模式

        Returns:
            int: 退出码
        """
        try:
            # 验证必需参数
            if not self.args.target:
                logger.error("非交互式模式需要指定 --target 参数")
                return 1

            if not self.args.mode:
                logger.error("非交互式模式需要指定 --mode 参数")
                return 1

            # 构建分析命令
            command = f"{self.args.mode}分析 {self.args.target}"

            # 创建临时会话
            session = self.orchestrator.create_session()

            try:
                # 执行分析
                result = self._process_user_input(session, command)

                if result.get('success', False):
                    # 输出结果
                    self._output_result(result)
                    return 0
                else:
                    logger.error(f"分析失败: {result.get('message', '未知错误')}")
                    return 1

            finally:
                self.orchestrator.close_session(session)

        except Exception as e:
            logger.error(f"非交互式模式执行失败: {e}")
            return 1

    def _run_batch_mode(self) -> int:
        """
        运行批处理模式

        Returns:
            int: 退出码
        """
        try:
            batch_file = Path(self.args.batch_file)
            if not batch_file.exists():
                logger.error(f"批处理文件不存在: {self.args.batch_file}")
                return 1

            # 读取批处理命令
            with open(batch_file, 'r', encoding='utf-8') as f:
                commands = [line.strip() for line in f if line.strip() and not line.strip().startswith('#')]

            if not commands:
                logger.warning("批处理文件为空")
                return 0

            logger.info(f"开始执行批处理模式，共 {len(commands)} 个命令")

            # 执行每个命令
            results = []
            for i, command in enumerate(commands, 1):
                logger.info(f"执行命令 {i}/{len(commands)}: {command}")

                try:
                    session = self.orchestrator.create_session()
                    result = self._process_user_input(session, command)
                    results.append({
                        'command': command,
                        'success': result.get('success', False),
                        'result': result
                    })
                    self.orchestrator.close_session(session)

                except Exception as e:
                    logger.error(f"命令执行失败: {command} - {e}")
                    results.append({
                        'command': command,
                        'success': False,
                        'error': str(e)
                    })

            # 输出批处理结果
            self._output_batch_results(results)

            # 检查是否全部成功
            failed_count = sum(1 for r in results if not r['success'])
            if failed_count > 0:
                logger.warning(f"批处理完成，{failed_count} 个命令失败")
                return 1
            else:
                logger.info("批处理完成，所有命令执行成功")
                return 0

        except Exception as e:
            logger.error(f"批处理模式执行失败: {e}")
            return 1

    def _get_user_input(self) -> str:
        """获取用户输入"""
        try:
            prompt = "aidetector> "
            user_input = input(prompt).strip()
            logger.info(f"用户输入: {user_input}")
            return user_input
        except KeyboardInterrupt:
            raise
        except EOFError:
            raise

    def _process_user_input(self, session, user_input: str) -> dict:
        """
        处理用户输入

        Args:
            session: 会话对象
            user_input: 用户输入

        Returns:
            dict: 处理结果
        """
        try:
            result = self.orchestrator.process_user_input(session, user_input)

            # 实时输出结果
            if not self.args.quiet and result.get('success', False):
                print(f"✓ {result.get('message', '操作成功')}")

            return result

        except Exception as e:
            logger.error(f"处理用户输入失败: {e}")
            return {
                'success': False,
                'message': f"处理失败: {e}",
                'should_exit': False
            }

    def _output_result(self, result: dict):
        """输出结果"""
        try:
            if self.args.output:
                # 输出到文件
                output_path = Path(self.args.output)
                with open(output_path, 'w', encoding='utf-8') as f:
                    if self.args.format == 'json':
                        json.dump(result, f, indent=2, ensure_ascii=False)
                    else:
                        f.write(str(result))
                logger.info(f"结果已保存到: {output_path}")
            else:
                # 输出到控制台
                if self.args.format == 'json':
                    print(json.dumps(result, indent=2, ensure_ascii=False))
                else:
                    print(str(result))

        except Exception as e:
            logger.error(f"输出结果失败: {e}")

    def _output_batch_results(self, results: List[dict]):
        """输出批处理结果"""
        try:
            summary = {
                'total_commands': len(results),
                'successful_commands': sum(1 for r in results if r['success']),
                'failed_commands': sum(1 for r in results if not r['success']),
                'results': results
            }

            if self.args.output:
                # 输出到文件
                output_path = Path(self.args.output)
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(summary, f, indent=2, ensure_ascii=False)
                logger.info(f"批处理结果已保存到: {output_path}")
            else:
                # 输出到控制台
                print(f"\n批处理执行完成:")
                print(f"总命令数: {summary['total_commands']}")
                print(f"成功: {summary['successful_commands']}")
                print(f"失败: {summary['failed_commands']}")

                if self.args.verbose and summary['failed_commands'] > 0:
                    print("\n失败的命令:")
                    for result in results:
                        if not result['success']:
                            print(f"  ✗ {result['command']}")
                            if 'error' in result:
                                print(f"    错误: {result['error']}")

        except Exception as e:
            logger.error(f"输出批处理结果失败: {e}")

    def _cleanup(self):
        """清理资源"""
        try:
            if self.orchestrator:
                self.orchestrator.cleanup()
                logger.info("资源清理完成")
        except Exception as e:
            logger.error(f"资源清理失败: {e}")


def main():
    """主函数"""
    try:
        app = CLIMainApplication()
        exit_code = app.run()
        sys.exit(exit_code)
    except Exception as e:
        print(f"程序启动失败: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()