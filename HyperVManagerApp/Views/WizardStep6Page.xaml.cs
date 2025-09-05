using Microsoft.UI.Xaml.Controls;
using System.Text;

namespace HyperVManager.Views
{
    public sealed partial class WizardStep6Page : Page
    {
        public CreateVMWizardData ViewModel { get; set; }

        public WizardStep6Page()
        {
            this.InitializeComponent();
            ViewModel = App.WizardData;
            this.DataContext = ViewModel;
            UpdateSummary();
        }

        private void UpdateSummary()
        {
            StringBuilder summary = new StringBuilder();
            summary.AppendLine($"虚拟机名称: {ViewModel.VmName}");
            summary.AppendLine($"存储位置: {ViewModel.VmPath}");
            summary.AppendLine($"内存: {ViewModel.MemoryMB} MB");
            summary.AppendLine($"CPU 核心数: {ViewModel.CpuCores}");
            
            if (ViewModel.CreateNewDisk)
            {
                summary.AppendLine($"硬盘: 创建新硬盘 ({ViewModel.DiskSizeGB} GB)");
            }
            else
            {
                summary.AppendLine($"硬盘: 使用现有硬盘 ({ViewModel.ExistingDiskPath})");
            }
            summary.AppendLine($"网络: {ViewModel.SelectedVSwitchName}");
            summary.AppendLine($"安装介质: {(string.IsNullOrEmpty(ViewModel.IsoPath) ? "无" : ViewModel.IsoPath)}");
            summary.AppendLine($"启用安全启动: {ViewModel.SecureBootEnabled}");

            SummaryTextBlock.Text = summary.ToString();
        }
    }
}
