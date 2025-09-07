# Hyper-V Manager

## 简介

Hyper-V Manager 是一个基于 Electron 构建的桌面应用程序，旨在为用户提供一个直观、便捷的图形界面，用于管理 Windows 系统上的 Hyper-V 虚拟机。它简化了虚拟机的创建、配置、生命周期管理以及网络和镜像的管理，特别适合需要快速部署和管理虚拟环境的用户。

## 主要功能

-   **虚拟机生命周期管理**：
    -   列出所有 Hyper-V 虚拟机及其状态。
    -   启动、关机、强制停止和删除虚拟机。
    -   连接到虚拟机控制台。
-   **网络管理**：
    -   管理虚拟交换机（创建、删除）。
    -   查看和管理 NAT 网络及端口映射规则。
    -   虚拟机网络适配器设置，支持预选当前连接的虚拟交换机。
-   **镜像管理**：
    -   扫描本地 ISO 镜像文件。
    -   集成在线镜像仓库，提供常用操作系统镜像的下载链接。
-   **向导式虚拟机创建**：
    -   提供多步骤向导，简化虚拟机创建流程。
    -   支持自定义虚拟机名称、存储路径、内存、CPU、硬盘大小、网络和安装介质。
    -   修正了安全启动的默认设置。
-   **远程执行**：
    -   在虚拟机内部远程执行 PowerShell 或 Shell 命令。
    -   内置常用一键脚本，如安装 Chocolatey、Nginx、设置静态 IP 等。
-   **用户体验优化**：
    -   支持虚拟机列表右键菜单操作。
    -   关键操作提供确认提示。
    -   设置页面显示应用版本和作者信息。
-   **持久化设置**：保存用户配置，如本地 ISO 路径。

## 技术栈

-   **前端**：HTML, CSS (Bootstrap 5), JavaScript
-   **框架**：Electron
-   **后端交互**：Node.js (通过 `child_process` 调用 PowerShell)
-   **权限管理**：`sudo-prompt`
-   **数据存储**：`electron-store`

## 快速开始

### 开发环境设置

1.  **克隆仓库**：
    ```bash
    git clone https://github.com/ikki99/hyperv_manager.git
    cd hyperv_manager
    ```
2.  **进入 Electron 应用目录**：
    ```bash
    cd HyperVManagerApp_Electron
    ```
3.  **安装依赖**：
    ```bash
    npm install
    ```
4.  **启动应用**：
    ```bash
    npm start
    ```

### 构建应用程序

在 `HyperVManagerApp_Electron` 目录下运行以下命令来构建可分发的应用程序：

```bash
npm run build
```

构建完成后，打包好的安装程序（例如 `.exe` 文件）将位于 `HyperVManagerApp_Electron/dist` 目录下。

## 使用说明

-   启动应用后，您可以在左侧导航栏切换不同的管理模块。
-   在虚拟机列表中，选中虚拟机后，可以使用顶部的操作按钮或右键菜单进行管理。
-   在“设置”页面，您可以配置本地 ISO 路径等。

## 贡献

欢迎任何形式的贡献！如果您有任何建议、bug 报告或功能请求，请通过 GitHub Issues 提交。

## 许可证

本项目采用 MIT 许可证。详情请参阅 `LICENSE` 文件。

## 联系作者

-   **作者**：wngx99
-   **Email**：wngx99@gmail.com
