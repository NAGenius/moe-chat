import json
import sys
import threading
import logging

import redis

from show_moe import MoEInterface

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class MoEVisualizerService:
    """MoE可视化服务 - 独立进程运行"""

    def __init__(self, redis_host="localhost", redis_port=6379, redis_db=0):
        self.redis_client = redis.Redis(host=redis_host, port=redis_port, db=redis_db)
        self.moe_interface = MoEInterface()
        self.visualizer = None
        self.is_running = False

    def initialize(self, num_experts: int = 64):
        """初始化可视化器"""
        self.visualizer = self.moe_interface.initialize_visualizer(num_experts)
        logger.info(f"MoE可视化器已初始化，专家数量: {num_experts}")

    def start_redis_listener(self):
        """启动Redis监听器"""

        def redis_listener():
            try:
                pubsub = self.redis_client.pubsub()
                pubsub.subscribe("moe:expert:activation")

                logger.info("Redis监听器已启动，等待专家激活数据...")

                for message in pubsub.listen():
                    if message["type"] == "message":
                        try:
                            # 解析专家激活数据
                            expert_data = json.loads(message["data"].decode("utf-8"))
                            logger.info(f"收到专家激活数据: {len(expert_data)} 个专家")

                            # 更新可视化
                            if self.visualizer:
                                self.moe_interface.update_expert_activation(expert_data)

                        except Exception as e:
                            logger.error(f"处理专家激活数据时出错: {e}")
            except Exception as e:
                logger.error(f"Redis监听器启动失败: {e}")

        logger.error("请确保Redis服务正在运行")

        # 在独立线程中运行Redis监听器
        listener_thread = threading.Thread(target=redis_listener, daemon=True)
        listener_thread.start()

    def start_visualization(self, interval: int = 1000):
        """启动可视化显示"""
        if not self.visualizer:
            logger.error("错误: 可视化器未初始化，请先调用initialize()")
            return

        self.is_running = True
        logger.info("启动MoE专家激活可视化...")

        # 启动Redis监听
        self.start_redis_listener()

        # 启动可视化动画
        try:
            self.visualizer.start_animation(interval=interval)
        except KeyboardInterrupt:
            logger.info("\n用户中断程序")
        finally:
            self.stop()

    def stop(self):
        """停止服务"""
        self.is_running = False
        if self.visualizer:
            self.visualizer.stop_animation()
        logger.info("MoE可视化服务已停止")


def main():
    """主函数"""
    logger.info("=== MoE专家激活可视化服务 ===")
    logger.info("正在启动...")

    try:
        # 创建可视化服务
        service = MoEVisualizerService()

        # 初始化可视化器（64个专家，适用于大多数MoE模型）
        service.initialize(num_experts=64)

        # 启动可视化
        service.start_visualization(interval=1000)  # 每秒更新一次

    except KeyboardInterrupt:
        logger.info("\n用户中断程序")
    except Exception as e:
        logger.error(f"启动失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
