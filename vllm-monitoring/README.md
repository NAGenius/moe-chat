# vLLM监控系统

这个项目提供了一个完整的vLLM服务监控解决方案，使用Docker容器化部署，包含Prometheus和Grafana，可以监控远程vLLM服务的各项指标。

## 目录结构

```
vllm-monitoring/
├── prometheus/
│   ├── prometheus.yml     # Prometheus配置文件
│   └── rules.yml          # 告警规则配置
├── grafana/
│   ├── dashboards/
│   │   └── vllm-dashboard.json  # vLLM监控仪表盘
│   └── provisioning/
│       ├── dashboards/
│       │   └── dashboards.yml   # 仪表盘配置
│       └── datasources/
│           └── prometheus.yml   # 数据源配置
├── docker-compose.yml     # Docker Compose配置文件
├── start-monitoring.bat   # 启动脚本
└── README.md              # 使用说明
```

## 快速开始

1. **先决条件**
   - Windows 10/11操作系统
   - 安装Docker Desktop for Windows
   - 确保Docker已启动并正常运行

2. **配置监控目标**
   - 打开`prometheus/prometheus.yml`
   - 将`vllm-server-ip:8001`替换为您要监控的vLLM服务的实际IP和端口

3. **启动服务**
   - 双击`start-monitoring.bat`脚本
   - 或在命令提示符中运行以下命令:
   ```
   cd path\to\vllm-monitoring
   docker-compose up -d
   ```

4. **访问监控界面**
   - Grafana: [http://localhost:3010](http://localhost:3010) (默认用户名/密码: admin/admin)
   - Prometheus: [http://localhost:9090](http://localhost:9090)

## 监控指标说明

vLLM监控系统可以收集以下关键指标:

### 核心业务指标
- **请求队列状态**: 运行中和等待中的请求数量
- **GPU缓存使用率**: KV-cache使用百分比，监控内存效率
- **Token处理速率**: Prompt和Generation Token的实时处理速度
- **请求成功率**: 按结束原因分类（stop/length/abort）的请求统计
- **首Token响应时间**: P95响应时间分布，衡量用户体验

### 性能优化指标
- **GPU前缀缓存性能**: 缓存命中率和查询率，优化推理效率
- **内存使用情况**: 物理内存使用监控
- **请求抢占情况**: 请求抢占次数统计，了解资源竞争
- **迭代Token数**: 平均每次迭代处理的Token数量

### 系统健康指标
- **Python进程指标**: 垃圾回收、文件描述符、CPU使用率
- **进程内存**: 虚拟内存和物理内存使用情况
- **文件描述符**: 打开的文件描述符数量监控

## 仪表板面板说明

vLLM监控仪表板包含9个核心面板，提供全方位的性能监控：

1. **请求队列状态** - 实时显示运行中和等待中的请求数量，帮助识别系统负载
2. **GPU缓存使用率** - 监控KV-cache使用百分比，优化内存分配
3. **Token处理速率** - 显示Prompt、Generation和平均迭代Token的处理速度
4. **请求成功率** - 按结束原因（stop/length/abort）统计请求完成情况
5. **首Token响应时间分布** - P95响应时间，直接反映用户体验质量
6. **GPU前缀缓存性能** - 缓存命中率和查询率，评估缓存效率
7. **内存使用情况** - 物理内存使用监控，防止内存溢出
8. **请求抢占情况** - 请求抢占次数统计，了解资源竞争状况
9. **Python进程指标** - GC收集、文件描述符、CPU使用率等系统级指标

每个面板都支持模型名称过滤，可以针对特定模型进行监控分析。

## 自定义配置

### 添加更多监控目标

编辑`prometheus/prometheus.yml`文件，在`scrape_configs`部分添加新的监控目标:

```yaml
scrape_configs:
  # vLLM服务监控
  - job_name: 'vllm-server-2'
    metrics_path: '/metrics'
    static_configs:
      - targets: ['另一台服务器IP:8001']
        labels:
          instance: 'vllm-staging'
          environment: 'staging'
```

### 调整告警规则

编辑`prometheus/rules.yml`文件，修改告警条件:

```yaml
- alert: HighRequestQueue
  expr: vllm_request_queue_size > 100  # 将阈值从50改为100
  for: 2m
```

### 增加自定义仪表盘

1. 在Grafana界面创建并保存自定义仪表盘
2. 导出为JSON并保存到`grafana/dashboards/`目录
3. 重启服务: `docker-compose restart`

## 故障排除

1. **无法连接到vLLM服务**
   - 检查vLLM服务器是否开放了metrics端点
   - 验证网络连接: `ping vllm-server-ip`
   - 检查防火墙设置，确保允许从监控服务器访问vLLM服务的8001端口

2. **Grafana没有显示数据**
   - 检查Prometheus目标状态: [http://localhost:9090/targets](http://localhost:9090/targets)
   - 验证vLLM服务是否正确暴露了metrics
   - 检查Prometheus查询是否正确: [http://localhost:9090/graph](http://localhost:9090/graph)

3. **Docker服务无法启动**
   - 检查Docker日志: `docker-compose logs`
   - 确保端口未被占用: `netstat -ano | findstr "9090 3010"`

## 配置为开机自启动

1. 创建批处理脚本的快捷方式
2. 按`Win+R`，输入`shell:startup`打开启动文件夹
3. 将快捷方式复制到启动文件夹中