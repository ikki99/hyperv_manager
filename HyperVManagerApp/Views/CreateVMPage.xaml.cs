using Microsoft.UI.Xaml.Controls;
using System.Collections.Generic;
using System.Threading.Tasks;
using Microsoft.UI.Xaml;
using Windows.UI.Popups;
using HyperVManager;

namespace HyperVManager.Views
{
    public sealed partial class CreateVMPage : Page
    {
        private int _currentStep = 1;
        private const int TotalSteps = 6;
        private HyperVService _hyperVService;

        public CreateVMPage()
        {
            this.InitializeComponent();
            _hyperVService = new HyperVService();
            NavigateToStep(_currentStep);
        }

        private void NavigateToStep(int step)
        {
            switch (step)
            {
                case 1: WizardFrame.Navigate(typeof(WizardStep1Page)); break;
                case 2: WizardFrame.Navigate(typeof(WizardStep2Page)); break;
                case 3: WizardFrame.Navigate(typeof(WizardStep3Page)); break;
                case 4: WizardFrame.Navigate(typeof(WizardStep4Page)); break;
                case 5: WizardFrame.Navigate(typeof(WizardStep5Page)); break;
                case 6: WizardFrame.Navigate(typeof(WizardStep6Page)); break;
                default: break;
            }
            UpdateNavigationButtons();
        }

        private void UpdateNavigationButtons()
        {
            BackButton.IsEnabled = _currentStep > 1;
            NextButton.Content = _currentStep == TotalSteps ? "创建虚拟机" : "下一步";
        }

        private void OnBackClicked(object sender, RoutedEventArgs e)
        {
            if (_currentStep > 1)
            {
                _currentStep--;
                NavigateToStep(_currentStep);
            }
        }

        private async void OnNextClicked(object sender, RoutedEventArgs e)
        {
            if (_currentStep < TotalSteps)
            {
                _currentStep++;
                NavigateToStep(_currentStep);
            }
            else
            {
                var wizardData = App.WizardData;

                if (string.IsNullOrEmpty(wizardData.VmName) || string.IsNullOrEmpty(wizardData.VmPath) ||
                    (wizardData.CreateNewDisk && wizardData.DiskSizeGB <= 0) ||
                    (!wizardData.CreateNewDisk && string.IsNullOrEmpty(wizardData.ExistingDiskPath)) ||
                    string.IsNullOrEmpty(wizardData.SelectedVSwitchName))
                {
                    var errorDialog = new MessageDialog("请填写所有必填字段。", "错误");
                    await errorDialog.ShowAsync();
                    return;
                }

                bool success = await _hyperVService.CreateVMAsync(
                    wizardData.VmName,
                    wizardData.MemoryMB,
                    wizardData.CpuCores,
                    wizardData.VmPath,
                    wizardData.DiskSizeGB,
                    wizardData.SelectedVSwitchName,
                    wizardData.IsoPath,
                    wizardData.ExistingDiskPath,
                    wizardData.SecureBootEnabled
                );

                var statusDialog = new ContentDialog
                {
                    Title = "虚拟机创建结果",
                    Content = success ? "虚拟机创建成功！" : "虚拟机创建失败。",
                    CloseButtonText = "确定",
                    XamlRoot = this.XamlRoot
                };
                await statusDialog.ShowAsync();

                if (success)
                {
                    App.WizardData = new CreateVMWizardData();
                }
            }
        }
    }
}
