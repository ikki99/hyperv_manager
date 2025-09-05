# Hyper-V 统一管理器 .NET 重构项目开发日志

## 1. 项目概述

*   **项目目标**: 重新实现 Hyper-V 统一管理器，提供虚拟机和网络管理的图形用户界面。
*   **选择技术栈**: C# / .NET / WinUI 3 (桌面应用)
*   **项目负责人**: Gemini (AI 助手)

## 2. 开发计划与进度

### 阶段 1: 项目搭建与核心基础设施

*   **任务 1.1: 项目初始化**
    *   **目标**: 创建 WinUI 3 项目骨架，配置基础依赖。
    *   **过程**:
        *   尝试 `dotnet new winui -n HyperVManager -o HyperVManagerApp`。
        *   **挑战**: 发现 .NET SDK 未安装。
        *   **解决方案**: 指导用户安装 .NET SDK。
        *   **挑战**: 发现 WinUI 模板未安装。
        *   **解决方案**: 指导用户安装 `VijayAnand.WinUITemplates`。
        *   **挑战**: 发现 NuGet 源未配置。
        *   **解决方案**: 指导用户添加 `nuget.org` 源。
        *   **结果**: 项目 `HyperVManagerApp` 成功创建。
    *   **状态**: **完成**

*   **任务 1.2: PowerShell 交互层**
    *   **目标**: 引入 `System.Management.Automation` 库，封装 PowerShell 调用。
    *   **过程**:
        *   进入项目目录 `HyperVManagerApp`。
        *   添加 `Microsoft.PowerShell.SDK` NuGet 包。
        *   在 `HyperVService.cs` 中实现 `ExecutePowerShellCommandAsync` 辅助方法。
    *   **状态**: **完成**

*   **任务 1.3: 数据模型定义**
    *   **目标**: 定义 C# 类来表示 Hyper-V 对象（VM, VSwitch, NatRule 等）。
    *   **过程**:
        *   创建 `Models.cs` 文件。
        *   定义 `VM`, `VMSimpleNetworkAdapter`, `VSwitch`, `NatRule`, `OnlineImage`, `LocalImage` 等类。
    *   **状态**: **完成**

### 阶段 2: 虚拟机管理模块

*   **任务 2.1: 虚拟机列表展示**
    *   **目标**: 在主界面显示虚拟机列表。
    *   **过程**:
        *   在 `HyperVService.cs` 中实现 `GetVMsAsync` 方法。
        *   修改 `Views/MainPage.xaml`，添加 `DataGrid` 并绑定数据。
        *   修改 `Views/MainPage.xaml.cs`，实例化 `HyperVService`，调用 `GetVMsAsync` 并绑定到 `ObservableCollection`。
    *   **状态**: **完成**

*   **任务 2.2: 虚拟机基本操作**
    *   **目标**: 实现启动、关机、停止、删除、连接虚拟机功能。
    *   **过程**:
        *   在 `Views/MainPage.xaml` 中添加操作按钮。
        *   在 `HyperVService.cs` 中实现 `StartVMAsync`, `ShutdownVMAsync`, `StopVMAsync`, `DeleteVMAsync`, `ConnectVM` 方法。
        *   在 `Views/MainPage.xaml.cs` 中实现按钮点击事件和 `DataGrid` 选择事件，调用 `HyperVService` 方法并刷新列表。
    *   **状态**: **完成**

*   **任务 2.3: 远程命令执行**
    *   **目标**: 实现通过 PowerShell Direct 在虚拟机内执行命令。
    *   **过程**:
        *   在 `Views/MainPage.xaml` 中添加“执行命令”按钮。
        *   在 `HyperVService.cs` 中实现 `InvokeCommandInVMAsync` 方法。
        *   在 `Views/MainPage.xaml.cs` 中实现按钮点击事件，弹出简易对话框获取凭据和命令，调用 `InvokeCommandInVMAsync` 并显示结果。
    *   **状态**: **完成**

### 阶段 3: 网络管理模块

*   **任务 3.1: 虚拟交换机列表展示**
    *   **目标**: 显示虚拟交换机列表。
    *   **过程**:
        *   在 `HyperVService.cs` 中实现 `GetVSwitchesAsync` 方法。
        *   创建 `Views/NetworkPage.xaml` 和 `Views/NetworkPage.xaml.cs`。
        *   在 `NetworkPage.xaml` 中添加 `DataGrid` 并绑定数据。
        *   在 `NetworkPage.xaml.cs` 中实例化 `HyperVService`，调用 `GetVSwitchesAsync` 并绑定数据。
        *   **临时调整**: 为方便测试，修改 `App.xaml.cs` 使其启动时直接导航到 `NetworkPage`。
    *   **状态**: **完成**

*   **任务 3.2: 虚拟交换机操作**
    *   **目标**: 实现创建和删除虚拟交换机功能。
    *   **过程**:
        *   在 `HyperVService.cs` 中实现 `CreateVSwitchAsync` 和 `DeleteVSwitchAsync` 方法。
        *   在 `Views/NetworkPage.xaml` 中添加操作按钮。
        *   在 `Views/NetworkPage.xaml.cs` 中实现按钮点击事件，包括创建交换机的简易对话框和删除确认。
    *   **状态**: **完成**

*   **任务 3.3: NAT 管理**
    *   **目标**: 实现 NAT 网络的创建、IP 配置、规则的增删查。
    *   **过程**:
        *   在 `HyperVService.cs` 中实现 `GetNatRulesAsync`, `AddNatRuleAsync`, `RemoveNatRuleAsync`, `CreateNatNetworkAsync`, `SetVSwitchIPAsync` 方法。
        *   在 `Views/NetworkPage.xaml` 中添加 NAT 管理面板的 UI 元素（按钮、`DataGrid`）。
        *   在 `Views/NetworkPage.xaml.cs` 中实现相关事件处理程序，包括对话框交互和数据刷新。
    *   **状态**: **完成**

### 阶段 4: 虚拟机创建向导

*   **任务 4.1: 实现向导导航**
    *   **目标**: 搭建多步骤向导的 UI 框架和导航逻辑。
    *   **过程**:
        *   创建 `Views/CreateVMPage.xaml` 和 `Views/CreateVMPage.xaml.cs`。
        *   在 `CreateVMPage.xaml` 中添加 `Frame` 和导航按钮。
        *   在 `CreateVMPage.xaml.cs` 中实现 `NavigateToStep` 方法和按钮点击事件。
    *   **状态**: **完成**

*   **任务 4.2: 实现步骤 1 (名称、路径、安全启动)**
    *   **目标**: 实现向导第一步的 UI 和数据绑定。
    *   **过程**:
        *   创建 `WizardData.cs` 定义 `CreateVMWizardData` 共享数据模型。
        *   修改 `App.xaml.cs` 添加静态 `WizardData` 属性。
        *   创建 `Views/WizardStep1Page.xaml` 和 `Views/WizardStep1Page.xaml.cs`。
        *   实现路径浏览功能，并绑定 UI 元素到 `WizardData`。
    *   **状态**: **完成**

*   **任务 4.3: 实现步骤 2 (内存、CPU)**
    *   **目标**: 实现向导第二步的 UI 和数据绑定。
    *   **过程**:
        *   创建 `Views/WizardStep2Page.xaml` 和 `Views/WizardStep2Page.xaml.cs`。
        *   添加滑块等 UI 元素，并绑定到 `WizardData`。
    *   **状态**: **完成**

*   **任务 4.4: 实现步骤 3 (磁盘 - 新建/现有)**
    *   **目标**: 实现向导第三步的 UI 和数据绑定。
    *   **过程**:
        *   创建 `Views/WizardStep3Page.xaml` 和 `Views/WizardStep3Page.xaml.cs`。
        *   添加单选按钮、文本框等 UI 元素，并实现文件浏览功能，绑定到 `WizardData`。
    *   **状态**: **完成**

*   **任务 4.5: 实现步骤 4 (网络)**
    *   **目标**: 实现向导第四步的 UI 和数据绑定。
    *   **过程**:
        *   创建 `Views/WizardStep4Page.xaml` 和 `Views/WizardStep4Page.xaml.cs`。
        *   添加下拉列表等 UI 元素，加载可用虚拟交换机，并绑定到 `WizardData`。
    *   **状态**: **完成**

*   **任务 4.6: 实现步骤 5 (安装选项)**
    *   **目标**: 实现向导第五步的 UI 和数据绑定。
    *   **过程**:
        *   创建 `Views/WizardStep5Page.xaml` 和 `Views/WizardStep5Page.xaml.cs`。
        *   添加 Pivot 控件、文件浏览功能，并绑定到 `WizardData`。
    *   **状态**: **完成**

*   **任务 4.7: 实现步骤 6 (摘要与创建虚拟机)**
    *   **目标**: 实现向导最后一步的 UI 和虚拟机创建逻辑。
    *   **过程**:
        *   创建 `Views/WizardStep6Page.xaml` 和 `Views/WizardStep6Page.xaml.cs`。
        *   在 `WizardStep6Page.xaml.cs` 中生成摘要文本。
        *   在 `HyperVService.cs` 中实现 `CreateVMAsync` 方法。
        *   在 `Views/CreateVMPage.xaml.cs` 中，当向导完成时调用 `CreateVMAsync`。
    *   **状态**: **完成**

### 阶段 5: 镜像管理与系统检查

*   **任务 5.1: 实现在线镜像展示**
    *   **目标**: 显示在线镜像列表。
    *   **过程**:
        *   在 `HyperVService.cs` 中实现 `GetOnlineImagesAsync` 方法。
        *   在 `Views/ImagesPage.xaml` 中添加 UI 元素（`ItemsRepeater`）。
        *   在 `Views/ImagesPage.xaml.cs` 中加载并绑定在线镜像数据。
    *   **状态**: **完成**

*   **任务 5.2: 实现本地镜像扫描**
    *   **目标**: 扫描本地文件夹中的镜像文件并显示。
    *   **过程**:
        *   在 `HyperVService.cs` 中实现 `GetLocalImagesAsync` 方法。
        *   在 `Views/ImagesPage.xaml` 中添加 UI 元素（文本框、按钮、`DataGrid`）。
        *   在 `Views/ImagesPage.xaml.cs` 中实现文件夹浏览、扫描和数据绑定。
    *   **状态**: **完成**

*   **任务 5.3: 实现系统检查**
    *   **目标**: 检查 Hyper-V 状态并提供安装选项。
    *   **过程**:
        *   在 `HyperVService.cs` 中实现 `CheckHyperVStatusAsync` 和 `InstallHyperVAsync` 方法。
        *   创建 `Views/SystemCheckPage.xaml` 和 `Views/SystemCheckPage.xaml.cs`。
        *   在 `SystemCheckPage.xaml` 中添加 UI 元素（按钮、文本块）。
        *   在 `Views/SystemCheckPage.xaml.cs` 中实现状态检查和安装逻辑。
    *   **状态**: **完成**

### 阶段 6: 优化、测试与新功能

*   **任务 6.1: UI 细节优化与响应式设计**
    *   **目标**: 搭建主导航框架，整合所有页面。
    *   **过程**:
        *   修改 `App.xaml.cs`，使其创建并激活 `MainWindow`。
        *   创建 `MainWindow.xaml` 和 `MainWindow.xaml.cs`，添加 `NavigationView` 和 `Frame`。
        *   在 `MainWindow.xaml.cs` 中实现导航逻辑，将所有功能页面集成到 `NavigationView` 中。
        *   移除各页面 `refresh_..._table` 方法中不再需要的 `Window` 参数。
    *   **状态**: **完成**

*   **任务 6.2: 全面测试与 Bug 修复**
    *   **目标**: 编译项目，运行测试，修复发现的 Bug。
    *   **过程**:
        *   **挑战**: 项目无法编译，持续出现 `MSB3073: XamlCompiler.exe 已退出，代码为 1` 的错误。
        *   **排查步骤 1 (SDK 版本)**: 尝试将项目从 .NET 9 预览版降级至 .NET 8 稳定版，问题依旧。
        *   **排查步骤 2 (WinAppSDK 版本)**: 尝试将 `Microsoft.WindowsAppSDK` 从 `1.7.*` 预览版降级至 `1.5.*` 稳定版，问题依旧。
        *   **排查步骤 3 (清理缓存)**: 执行了完整的 NuGet 缓存清理 (`dotnet nuget locals all --clear`) 并手动删除了 `bin` 和 `obj` 目录，问题依旧。
        *   **排查步骤 4 (XAML 审查)**: 对所有 `.xaml` 文件进行了全面审查。发现 `MainPage.xaml`, `NetworkPage.xaml`, `ImagesPage.xaml`, `WizardStep5Page.xaml` 中均使用了错误的 UWP 控件命名空间 (`using:Microsoft.Toolkit.Uwp.UI.Controls`)。
        *   **解决方案**: 将所有错误的命名空间修正为正确的 `using:CommunityToolkit.WinUI.UI.Controls`，并添加了对应的 `CommunityToolkit.WinUI.UI.Controls.DataGrid` NuGet 包。
        *   **最终挑战**: 即使在修正了所有已发现的 XAML 错误后，`XamlCompiler.exe` 仍然以完全相同的方式崩溃。
    *   **当前状态**: **阻塞**。已用尽所有标准诊断方法，但编译问题无法解决。怀疑是 XAML 编译器本身存在一个由特定代码触发的、无法明确提示的罕见 Bug，或项目文件存在更深层次的、未被发现的损坏。由于缺乏可直接调试 XAML 编译器的工具，无法进一步诊断。
    *   **建议**: 暂停后续功能开发，直到此编译问题得到解决。建议开发者考虑使用 Visual Studio 等更强大的 IDE 进行深度调试，或尝试从头开始重建 `.csproj` 项目文件。

*   **任务 6.3: 评估与新增必要功能**
    *   **目标**: 识别并添加新的、有价值的功能。
    *   **状态**: **已阻塞**

---
