import queue
import threading
import time
import logging
from typing import Dict

import matplotlib.animation as animation
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MoEExpertVisualizer:
    """MoE专家激活可视化器"""

    def __init__(self, num_experts: int = 64, grid_size: tuple = (8, 8)):
        """
        初始化可视化器

        Args:
            num_experts: 专家数量
            grid_size: 网格大小 (rows, cols)
        """
        self.num_experts = num_experts
        self.grid_size = grid_size
        self.data_queue = queue.Queue()
        self.current_data = {}
        self.is_running = False

        # 初始化图形 - 创建左侧统计面板和右侧热力图
        self.fig = plt.figure(figsize=(16, 10))
        self.fig.suptitle(
            "MoE Model Expert Activation Real-time Monitor",
            fontsize=18,
            fontweight="bold",
        )

        # 创建网格布局：左侧统计信息，右侧热力图
        gs = self.fig.add_gridspec(1, 2, width_ratios=[1, 2], wspace=0.15)

        # 左侧统计信息面板
        self.stats_ax = self.fig.add_subplot(gs[0, 0])
        self.stats_ax.set_xlim(0, 1)
        self.stats_ax.set_ylim(0, 1)
        self.stats_ax.axis("off")  # 隐藏坐标轴

        # 右侧热力图
        self.ax = self.fig.add_subplot(gs[0, 1])

        # 创建颜色映射 - 专业红色系渐变
        colors = [
            "#1a0000",
            "#330000",
            "#4d0000",
            "#660000",
            "#800000",
            "#990000",
            "#b30000",
            "#cc0000",
            "#e60000",
            "#ff0000",
            "#ff1a1a",
            "#ff3333",
            "#ff4d4d",
            "#ff6666",
            "#ff8080",
            "#ff9999",
            "#ffb3b3",
            "#ffcccc",
        ]
        self.cmap = LinearSegmentedColormap.from_list("expert_activation_red", colors)

        # 初始化数据网格
        self.expert_grid = np.zeros(grid_size)
        self.expert_ids = np.arange(num_experts).reshape(grid_size)

        # 创建热力图
        self.im = self.ax.imshow(
            self.expert_grid,
            cmap=self.cmap,
            vmin=0,
            vmax=1000,
            animated=True,
            aspect="equal",
        )

        # 添加颜色条到右侧
        self.cbar = plt.colorbar(self.im, ax=self.ax, fraction=0.046, pad=0.08)
        self.cbar.set_label("Activation Count", rotation=270, labelpad=20, fontsize=12)

        # 设置热力图坐标轴
        self.ax.set_title("Expert Activation Heatmap", fontsize=14, pad=20)
        self.ax.set_xlabel("Expert Grid (Column)", fontsize=12)
        self.ax.set_ylabel("Expert Grid (Row)", fontsize=12)

        # 添加专家ID标签（左上角）和激活次数标签（中间）
        self.expert_id_texts = []
        self.activation_count_texts = []

        for i in range(grid_size[0]):
            id_row = []
            count_row = []
            for j in range(grid_size[1]):
                expert_id = self.expert_ids[i, j]
                if expert_id < num_experts:
                    # 专家ID显示在左上角
                    id_text = self.ax.text(
                        j - 0.35,
                        i - 0.35,
                        str(expert_id),
                        ha="center",
                        va="center",
                        fontsize=8,
                        color="white",
                        fontweight="bold",
                        bbox=dict(
                            boxstyle="round,pad=0.15", facecolor="black", alpha=0.8
                        ),
                    )
                    id_row.append(id_text)

                    # 激活次数显示在中间
                    count_text = self.ax.text(
                        j,
                        i,
                        "0",
                        ha="center",
                        va="center",
                        fontsize=10,
                        color="white",
                        fontweight="bold",
                        bbox=dict(
                            boxstyle="round,pad=0.2", facecolor="#cc0000", alpha=0.9
                        ),
                    )
                    count_row.append(count_text)
                else:
                    id_row.append(None)
                    count_row.append(None)

            self.expert_id_texts.append(id_row)
            self.activation_count_texts.append(count_row)

        # 统计信息文本 - 显示在左侧面板
        self.stats_text = self.stats_ax.text(
            0.05,
            0.95,
            "",
            transform=self.stats_ax.transAxes,
            fontsize=11,
            verticalalignment="top",
            horizontalalignment="left",
            bbox=dict(
                boxstyle="round,pad=0.5",
                facecolor="#f8f8f8",
                edgecolor="#cc0000",
                linewidth=2,
                alpha=0.95,
            ),
            family="monospace",
        )

        plt.tight_layout()

    def update_expert_data(self, expert_stats: Dict[str, int]) -> None:
        """
        更新专家激活数据的接口方法

        Args:
            expert_stats: 专家统计数据，格式: {'专家ID': 激活次数}
        """
        try:
            # 将数据放入队列
            self.data_queue.put(expert_stats.copy())
            logger.info(
                f"Data updated: Received activation data for {len(expert_stats)} experts"
            )
        except Exception as e:
            logger.error(f"Error updating data: {e}")

    def _process_data_queue(self):
        """处理数据队列中的数据"""
        try:
            while not self.data_queue.empty():
                new_data = self.data_queue.get_nowait()
                self.current_data = new_data
        except queue.Empty:
            pass

    def _update_grid(self):
        """更新显示网格"""
        if not self.current_data:
            return

        # 重置网格
        self.expert_grid.fill(0)

        # 更新专家激活数据
        max_activation = max(self.current_data.values()) if self.current_data else 1
        min_activation = min(self.current_data.values()) if self.current_data else 0

        for i in range(self.grid_size[0]):
            for j in range(self.grid_size[1]):
                expert_id = self.expert_ids[i, j]
                if expert_id < self.num_experts:
                    expert_key = str(expert_id)
                    if expert_key in self.current_data:
                        activation_count = self.current_data[expert_key]
                        self.expert_grid[i, j] = activation_count

                        # 更新中间的激活次数显示
                        if self.activation_count_texts[i][j] is not None:
                            self.activation_count_texts[i][j].set_text(
                                str(activation_count)
                            )
                    else:
                        # 如果没有数据，显示0
                        if self.activation_count_texts[i][j] is not None:
                            self.activation_count_texts[i][j].set_text("0")

        # 更新颜色映射范围
        if max_activation > 0:
            self.im.set_clim(vmin=min_activation, vmax=max_activation)

        # 更新图像数据
        self.im.set_array(self.expert_grid)

        # 更新统计信息
        if self.current_data:
            total_activations = sum(self.current_data.values())
            active_experts = len([v for v in self.current_data.values() if v > 0])
            avg_activation = (
                total_activations / len(self.current_data) if self.current_data else 0
            )

            # 按激活次数排序获取前10多和前10少
            sorted_experts = sorted(
                self.current_data.items(), key=lambda x: x[1], reverse=True
            )
            top_10 = sorted_experts[:10]
            bottom_10 = sorted_experts[-10:]

            # 生成统计文本
            stats_text = f"""REAL-TIME STATISTICS
━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total Activations: {total_activations:,}
Active Experts: {active_experts}/{self.num_experts}
Average Activation: {avg_activation:.1f}

TOP 10 MOST ACTIVE EXPERTS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━"""

            for i, (expert_id, count) in enumerate(top_10, 1):
                stats_text += f"\n{i:2d}. Expert {expert_id:2s}: {count:,}"

            stats_text += f"""

TOP 10 LEAST ACTIVE EXPERTS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━"""

            for i, (expert_id, count) in enumerate(bottom_10, 1):
                stats_text += f"\n{i:2d}. Expert {expert_id:2s}: {count:,}"

            self.stats_text.set_text(stats_text)

    def animate(self, frame):
        """动画更新函数"""
        self._process_data_queue()
        self._update_grid()

        # 返回所有需要更新的对象
        update_objects = [self.im, self.stats_text]

        # 添加所有激活次数文本对象到更新列表
        for row in self.activation_count_texts:
            for text_obj in row:
                if text_obj is not None:
                    update_objects.append(text_obj)

        return update_objects

    def start_animation(self, interval: int = 1000):
        """
        开始动画显示

        Args:
            interval: 动画更新间隔(毫秒)
        """
        self.is_running = True
        self.ani = animation.FuncAnimation(
            self.fig,
            self.animate,
            interval=interval,
            blit=False,
            repeat=True,
            cache_frame_data=False,
        )
        plt.show()

    def stop_animation(self):
        """停止动画"""
        self.is_running = False
        if hasattr(self, "ani"):
            self.ani.event_source.stop()

    def save_animation(self, filename: str, duration: int = 10, fps: int = 2):
        """
        保存动画为GIF文件

        Args:
            filename: 文件名
            duration: 动画时长(秒)
            fps: 帧率
        """
        logger.info(f"Saving animation to {filename}...")
        frames = duration * fps
        self.ani = animation.FuncAnimation(
            self.fig,
            self.animate,
            frames=frames,
            interval=1000 // fps,
            blit=False,
            repeat=False,
        )
        self.ani.save(filename, writer="pillow", fps=fps)
        logger.info(f"Animation saved to {filename}")


def simulate_moe_conversation(visualizer: MoEExpertVisualizer):
    """模拟MoE对话数据生成"""

    # 示例数据1
    expert_data_1 = {
        "60": 659,
        "49": 651,
        "39": 649,
        "28": 645,
        "14": 644,
        "55": 635,
        "57": 597,
        "46": 594,
        "20": 594,
        "47": 592,
        "34": 591,
        "23": 586,
        "29": 579,
        "15": 578,
        "42": 564,
        "61": 564,
        "59": 558,
        "40": 556,
        "32": 553,
        "10": 552,
        "1": 551,
        "50": 550,
        "19": 548,
        "35": 541,
        "22": 540,
        "48": 539,
        "58": 533,
        "36": 525,
        "26": 524,
        "3": 523,
        "12": 519,
        "63": 518,
        "0": 516,
        "6": 514,
        "8": 509,
        "21": 505,
        "13": 505,
        "18": 504,
        "24": 502,
        "17": 501,
        "25": 498,
        "45": 490,
        "4": 484,
        "38": 482,
        "27": 480,
        "31": 477,
        "52": 476,
        "33": 474,
        "53": 469,
        "54": 469,
        "9": 468,
        "16": 465,
        "51": 461,
        "7": 461,
        "43": 454,
        "41": 448,
        "5": 447,
        "2": 440,
        "30": 439,
        "44": 428,
        "62": 428,
        "11": 427,
        "56": 426,
        "37": 373,
    }

    # 示例数据2
    expert_data_2 = {
        "45": 687,
        "12": 673,
        "51": 668,
        "33": 662,
        "7": 658,
        "58": 654,
        "23": 651,
        "41": 647,
        "16": 643,
        "29": 639,
        "54": 635,
        "8": 631,
        "37": 628,
        "62": 624,
        "19": 620,
        "46": 617,
        "31": 613,
        "9": 609,
        "56": 605,
        "24": 601,
        "13": 598,
        "50": 594,
        "38": 590,
        "61": 587,
        "5": 583,
        "27": 579,
        "42": 576,
        "18": 572,
        "60": 568,
        "34": 565,
        "11": 561,
        "49": 558,
        "25": 554,
        "53": 551,
        "40": 547,
        "6": 544,
        "35": 540,
        "59": 537,
        "22": 533,
        "48": 530,
        "14": 526,
        "57": 523,
        "32": 519,
        "43": 516,
        "28": 512,
        "39": 509,
        "1": 505,
        "55": 502,
        "17": 498,
        "63": 495,
        "36": 491,
        "47": 488,
        "21": 484,
        "52": 481,
        "10": 477,
        "44": 474,
        "30": 470,
        "26": 467,
        "15": 463,
        "2": 460,
        "20": 456,
        "4": 453,
        "0": 449,
        "3": 446,
    }

    data_sets = [expert_data_1, expert_data_2]

    def data_feeder():
        """数据输入线程"""
        time.sleep(2)  # 等待界面初始化

        for i, data in enumerate(data_sets):
            logger.info(f"\n=== Round {i+1} Conversation Data ===")
            visualizer.update_expert_data(data)
            time.sleep(5)  # 每5秒更新一次数据

        # 继续生成随机变化的数据来模拟持续对话
        logger.info("\n=== Starting Continuous Conversation Simulation ===")
        base_data = expert_data_2.copy()

        for round_num in range(3, 20):
            # 随机调整专家激活数据
            new_data = {}
            for expert_id in range(64):
                expert_key = str(expert_id)
                if expert_key in base_data:
                    # 在原值基础上随机变化 ±50
                    base_value = base_data[expert_key]
                    change = np.random.randint(-50, 51)
                    new_value = max(100, base_value + change)  # 最小值100
                    new_data[expert_key] = new_value
                else:
                    new_data[expert_key] = np.random.randint(100, 300)

            logger.info(f"Round {round_num} conversation data generated")
            visualizer.update_expert_data(new_data)
            base_data = new_data.copy()
            time.sleep(3)  # 每3秒更新一次

    # 启动数据输入线程
    data_thread = threading.Thread(target=data_feeder, daemon=True)
    data_thread.start()


def main():
    """主函数"""
    logger.info("MoE Expert Activation Visualization System Starting...")

    # 创建可视化器
    visualizer = MoEExpertVisualizer(num_experts=64, grid_size=(8, 8))

    # 启动模拟数据生成
    simulate_moe_conversation(visualizer)

    # 开始动画显示
    logger.info("Starting animation display...")
    logger.info("Close window to stop the program")

    try:
        visualizer.start_animation(interval=1000)  # 每秒更新一次
    except KeyboardInterrupt:
        logger.info("\nProgram interrupted by user")
    finally:
        visualizer.stop_animation()
        logger.info("Visualization system closed")


# 外部调用接口示例
class MoEInterface:
    """提供给外部程序的接口类"""

    def __init__(self):
        self.visualizer = None

    def initialize_visualizer(self, num_experts: int = 64):
        """初始化可视化器"""
        self.visualizer = MoEExpertVisualizer(num_experts=num_experts)
        return self.visualizer

    def update_expert_activation(self, expert_stats: Dict[str, int]):
        """
        外部程序调用此方法更新专家激活数据

        Args:
            expert_stats: 专家激活统计，格式: {'专家ID': 激活次数}

        Example:
            interface = MoEInterface()
            visualizer = interface.initialize_visualizer()

            # 外部程序每次对话后调用
            expert_data = {'0': 520, '1': 510, '2': 480, ...}
            interface.update_expert_activation(expert_data)
        """
        if self.visualizer:
            self.visualizer.update_expert_data(expert_stats)
        else:
            logger.error(
                "Error: Visualizer not initialized, please call initialize_visualizer() first"
            )

    def start_display(self, interval: int = 1000):
        """启动显示"""
        if self.visualizer:
            self.visualizer.start_animation(interval=interval)
        else:
            logger.error("Error: Visualizer not initialized")


if __name__ == "__main__":
    main()
