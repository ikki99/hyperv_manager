using Microsoft.UI.Xaml.Controls;
using System.Threading.Tasks;
using Microsoft.UI.Xaml;
using Windows.UI.Popups;
using System;

namespace HyperVManager.Views
{
    public sealed partial class SystemCheckPage : Page
    {
        private HyperVService _hyperVService;

        public SystemCheckPage()
        {
            this.InitializeComponent();
            _hyperVService = new HyperVService();
        }

        private async void OnCheckHyperVStatusClicked(object sender, RoutedEventArgs e)
        {
            StatusTextBlock.Text = "正在检查...";
            InstallButton.Visibility = Visibility.Collapsed;
            WarningTextBlock.Visibility = Visibility.Collapsed;

            string status = await _hyperVService.CheckHyperVStatusAsync();

            switch (status)
            {
                case "Enabled":
                    StatusTextBlock.Text = "Hyper-V 已安装并启用。";
                    StatusTextBlock.Foreground = new Microsoft.UI.Xaml.Media.SolidColorBrush(Microsoft.UI.Colors.Green);
                    break;
                case "Disabled":
                case "Absent":
                    StatusTextBlock.Text = "Hyper-V 未安装或未启用。";
                    StatusTextBlock.Foreground = new Microsoft.UI.Xaml.Media.SolidColorBrush(Microsoft.UI.Colors.Orange);
                    InstallButton.Visibility = Visibility.Visible;
                    WarningTextBlock.Visibility = Visibility.Visible;
                    break;
                case "Insufficient permissions":
                    StatusTextBlock.Text = "权限不足，无法检查 Hyper-V 状态。请以管理员身份运行。";
                    StatusTextBlock.Foreground = new Microsoft.UI.Xaml.Media.SolidColorBrush(Microsoft.UI.Colors.Red);
                    break;
                default:
                    StatusTextBlock.Text = $"检查失败: {status}";
                    StatusTextBlock.Foreground = new Microsoft.UI.Xaml.Media.SolidColorBrush(Microsoft.UI.Colors.Red);
                    break;
            }
        }

        private async void OnInstallHyperVClicked(object sender, RoutedEventArgs e)
        {
            var confirmDialog = new ContentDialog
            {
                Title = "确认安装 Hyper-V",
                Content = "此操作将安装 Hyper-V 功能并可能需要重启电脑，确定吗？",
                PrimaryButtonText = "安装",
                CloseButtonText = "取消",
                XamlRoot = this.XamlRoot
            };

            ContentDialogResult result = await confirmDialog.ShowAsync();

            if (result == ContentDialogResult.Primary)
            {
                bool success = await _hyperVService.InstallHyperVAsync();
                var statusDialog = new MessageDialog(success ? "Hyper-V 安装命令已成功执行！请手动重启电脑以完成安装。" : "Hyper-V 安装失败。", "结果");
                await statusDialog.ShowAsync();
                // Re-check status after attempt
                OnCheckHyperVStatusClicked(sender, e);
            }
        }
    }
}
