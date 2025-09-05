using Microsoft.UI.Xaml.Controls;
using System.Collections.ObjectModel;
using HyperVManager;
using System.Threading.Tasks;
using Microsoft.UI.Xaml;
using Windows.UI.Popups;
using System;
using System.Linq;

namespace HyperVManager.Views
{
    public sealed partial class NetworkPage : Page
    {
        public ObservableCollection<VSwitch> VSwitches { get; set; }
        public ObservableCollection<NatRule> NatRules { get; set; }
        private HyperVService _hyperVService;
        private VSwitch _selectedVSwitch;

        public NetworkPage()
        {
            this.InitializeComponent();
            _hyperVService = new HyperVService();
            VSwitches = new ObservableCollection<VSwitch>();
            NatRules = new ObservableCollection<NatRule>();
            _ = LoadVSwitchesAsync();
        }

        private async Task LoadVSwitchesAsync()
        {
            var vswitches = await _hyperVService.GetVSwitchesAsync();
            VSwitches.Clear();
            foreach (var vswitch in vswitches)
            {
                VSwitches.Add(vswitch);
            }
            UpdateVSwitchActionButtons();
        }

        private async void OnVSwitchDataGridSelectionChanged(object sender, SelectionChangedEventArgs e)
        {
            _selectedVSwitch = VSwitchDataGrid.SelectedItem as VSwitch;
            UpdateVSwitchActionButtons();

            // Load NAT rules if an Internal switch is selected
            if (_selectedVSwitch != null && _selectedVSwitch.SwitchType == "Internal")
            {
                NatPanel.Visibility = Visibility.Visible;
                await LoadNatRulesAsync(_selectedVSwitch.Name);
            }
            else
            {
                NatPanel.Visibility = Visibility.Collapsed;
                NatRules.Clear();
            }
        }

        private async Task LoadNatRulesAsync(string natName)
        {
            var rules = await _hyperVService.GetNatRulesAsync(natName);
            NatRules.Clear();
            foreach (var rule in rules)
            {
                NatRules.Add(rule);
            }
        }

        private void UpdateVSwitchActionButtons()
        {
            bool isVSwitchSelected = _selectedVSwitch != null;
            // Enable/disable buttons based on selection and vSwitch type
            // For now, buttons are always enabled in XAML, and we handle null _selectedVSwitch in handlers.
        }

        private async void OnRefreshVSwitchesClicked(object sender, RoutedEventArgs e)
        {
            _selectedVSwitch = null;
            VSwitchDataGrid.SelectedItem = null;
            await LoadVSwitchesAsync();
        }

        private async void OnCreateVSwitchClicked(object sender, RoutedEventArgs e)
        {
            // Simple dialog for vSwitch creation
            TextBox nameTextBox = new TextBox() { PlaceholderText = "交换机名称" };
            ComboBox typeComboBox = new ComboBox();
            typeComboBox.Items.Add("External");
            typeComboBox.Items.Add("Internal");
            typeComboBox.Items.Add("Private");
            typeComboBox.SelectedIndex = 0; // Default to External

            StackPanel content = new StackPanel();
            content.Children.Add(new TextBlock() { Text = "名称:" });
            content.Children.Add(nameTextBox);
            content.Children.Add(new TextBlock() { Text = "类型:" });
            content.Children.Add(typeComboBox);

            ContentDialog createDialog = new ContentDialog
            {
                Title = "创建虚拟交换机",
                Content = content,
                PrimaryButtonText = "创建",
                CloseButtonText = "取消",
                XamlRoot = this.XamlRoot
            };

            ContentDialogResult result = await createDialog.ShowAsync();

            if (result == ContentDialogResult.Primary)
            {
                string name = nameTextBox.Text;
                string type = typeComboBox.SelectedItem?.ToString();

                if (string.IsNullOrEmpty(name) || string.IsNullOrEmpty(type))
                {
                    var errorDialog = new MessageDialog("名称和类型不能为空。", "错误");
                    await errorDialog.ShowAsync();
                    return;
                }

                // For External, we'd need to get network adapter name. Skipping for simplicity now.
                bool success = await _hyperVService.CreateVSwitchAsync(name, type);

                var statusDialog = new MessageDialog(success ? "交换机创建成功！" : "交换机创建失败。", "结果");
                await statusDialog.ShowAsync();
                await LoadVSwitchesAsync(); // Refresh list
            }
        }

        private async void OnDeleteVSwitchClicked(object sender, RoutedEventArgs e)
        {
            if (_selectedVSwitch == null)
            {
                var noSwitchDialog = new MessageDialog("请先选择一个要删除的交换机。", "提示");
                await noSwitchDialog.ShowAsync();
                return;
            }

            var confirmDialog = new ContentDialog
            {
                Title = "确认删除",
                Content = $"您确定要删除交换机 '{_selectedVSwitch.Name}' 吗？",
                PrimaryButtonText = "删除",
                CloseButtonText = "取消",
                XamlRoot = this.XamlRoot
            };

            ContentDialogResult result = await confirmDialog.ShowAsync();

            if (result == ContentDialogResult.Primary)
            {
                bool success = await _hyperVService.DeleteVSwitchAsync(_selectedVSwitch.Name);
                var statusDialog = new MessageDialog(success ? "交换机删除成功！" : "交换机删除失败。", "结果");
                await statusDialog.ShowAsync();
                await LoadVSwitchesAsync(); // Refresh list
            }
        }

        private async void OnCreateNatNetworkClicked(object sender, RoutedEventArgs e)
        {
            if (_selectedVSwitch == null || _selectedVSwitch.SwitchType != "Internal")
            {
                var dialog = new MessageDialog("请先选择一个内部类型的虚拟交换机。", "提示");
                await dialog.ShowAsync();
                return;
            }

            TextBox subnetTextBox = new TextBox() { PlaceholderText = "子网地址 (例如: 192.168.100.0/24)" };
            ContentDialog createNatDialog = new ContentDialog
            {
                Title = $"为 '{_selectedVSwitch.Name}' 创建 NAT 网络",
                Content = subnetTextBox,
                PrimaryButtonText = "创建",
                CloseButtonText = "取消",
                XamlRoot = this.XamlRoot
            };

            ContentDialogResult result = await createNatDialog.ShowAsync();
            if (result == ContentDialogResult.Primary)
            {
                string subnet = subnetTextBox.Text;
                if (string.IsNullOrEmpty(subnet))
                {
                    var errorDialog = new MessageDialog("子网地址不能为空。", "错误");
                    await errorDialog.ShowAsync();
                    return;
                }
                bool success = await _hyperVService.CreateNatNetworkAsync(_selectedVSwitch.Name, subnet);
                var statusDialog = new MessageDialog(success ? "NAT 网络创建成功！" : "NAT 网络创建失败。", "结果");
                await statusDialog.ShowAsync();
                await LoadVSwitchesAsync(); // Refresh vSwitch list to update NAT status
            }
        }

        private async void OnSetGatewayIPClicked(object sender, RoutedEventArgs e)
        {
            if (_selectedVSwitch == null || _selectedVSwitch.SwitchType != "Internal")
            {
                var dialog = new MessageDialog("请先选择一个内部类型的虚拟交换机。", "提示");
                await dialog.ShowAsync();
                return;
            }

            TextBox ipTextBox = new TextBox() { PlaceholderText = "网关 IP (例如: 192.168.100.1/24)" };
            ContentDialog setIpDialog = new ContentDialog
            {
                Title = $"为 '{_selectedVSwitch.Name}' 设置网关 IP",
                Content = ipTextBox,
                PrimaryButtonText = "设置",
                CloseButtonText = "取消",
                XamlRoot = this.XamlRoot
            };

            ContentDialogResult result = await setIpDialog.ShowAsync();
            if (result == ContentDialogResult.Primary)
            {
                string ipAddressPrefix = ipTextBox.Text;
                if (string.IsNullOrEmpty(ipAddressPrefix) || !ipAddressPrefix.Contains("/"))
                {
                    var errorDialog = new MessageDialog("IP 地址格式不正确，请包含前缀长度 (例如: 192.168.100.1/24)。", "错误");
                    await errorDialog.ShowAsync();
                    return;
                }
                string[] parts = ipAddressPrefix.Split('/');
                string ipAddress = parts[0];
                string prefixLength = parts[1];

                bool success = await _hyperVService.SetVSwitchIPAsync(_selectedVSwitch.Name, ipAddress, prefixLength);
                var statusDialog = new MessageDialog(success ? "网关 IP 设置成功！" : "网关 IP 设置失败。", "结果");
                await statusDialog.ShowAsync();
                await LoadVSwitchesAsync(); // Refresh vSwitch list to update IP
            }
        }

        private async void OnAddNatRuleClicked(object sender, RoutedEventArgs e)
        {
            if (_selectedVSwitch == null || _selectedVSwitch.SwitchType != "Internal")
            {
                var dialog = new MessageDialog("请先选择一个内部类型的虚拟交换机。", "提示");
                await dialog.ShowAsync();
                return;
            }
            if (_selectedVSwitch.NatStatus != "已启用")
            {
                var dialog = new MessageDialog("请先为选定的交换机创建 NAT 网络。", "提示");
                await dialog.ShowAsync();
                return;
            }

            StackPanel content = new StackPanel() { Spacing = 10 };
            ComboBox protocolComboBox = new ComboBox();
            protocolComboBox.Items.Add("TCP");
            protocolComboBox.Items.Add("UDP");
            protocolComboBox.SelectedIndex = 0;
            TextBox extPortTextBox = new TextBox() { PlaceholderText = "外部端口" };
            TextBox intIpTextBox = new TextBox() { PlaceholderText = "内部 IP 地址" };
            TextBox intPortTextBox = new TextBox() { PlaceholderText = "内部端口" };

            content.Children.Add(new TextBlock() { Text = "协议:" });
            content.Children.Add(protocolComboBox);
            content.Children.Add(new TextBlock() { Text = "外部端口:" });
            content.Children.Add(extPortTextBox);
            content.Children.Add(new TextBlock() { Text = "内部 IP 地址:" });
            content.Children.Add(intIpTextBox);
            content.Children.Add(new TextBlock() { Text = "内部端口:" });
            content.Children.Add(intPortTextBox);

            ContentDialog addRuleDialog = new ContentDialog
            {
                Title = "添加端口转发规则",
                Content = content,
                PrimaryButtonText = "添加",
                CloseButtonText = "取消",
                XamlRoot = this.XamlRoot
            };

            ContentDialogResult result = await addRuleDialog.ShowAsync();
            if (result == ContentDialogResult.Primary)
            {
                string protocol = protocolComboBox.SelectedItem?.ToString();
                int extPort, intPort;
                string intIp = intIpTextBox.Text;

                if (!int.TryParse(extPortTextBox.Text, out extPort) || !int.TryParse(intPortTextBox.Text, out intPort) || string.IsNullOrEmpty(intIp))
                {
                    var errorDialog = new MessageDialog("请确保所有字段都已填写且端口号为有效数字。", "错误");
                    await errorDialog.ShowAsync();
                    return;
                }

                bool success = await _hyperVService.AddNatRuleAsync(_selectedVSwitch.Name, protocol, extPort, intIp, intPort);
                var statusDialog = new MessageDialog(success ? "规则添加成功！" : "规则添加失败。", "结果");
                await statusDialog.ShowAsync();
                await LoadNatRulesAsync(_selectedVSwitch.Name); // Refresh NAT rules
            }
        }

        private async void OnRemoveNatRuleClicked(object sender, RoutedEventArgs e)
        {
            if (_selectedVSwitch == null || _selectedVSwitch.SwitchType != "Internal" || _selectedVSwitch.NatStatus != "已启用")
            {
                var dialog = new MessageDialog("请先选择一个已启用 NAT 的内部虚拟交换机。", "提示");
                await dialog.ShowAsync();
                return;
            }
            if (NatRulesDataGrid.SelectedItem == null)
            {
                var dialog = new MessageDialog("请先选择一个要删除的端口转发规则。", "提示");
                await dialog.ShowAsync();
                return;
            }

            NatRule selectedRule = NatRulesDataGrid.SelectedItem as NatRule;

            var confirmDialog = new ContentDialog
            {
                Title = "确认删除规则",
                Content = $"您确定要删除协议 {selectedRule.Protocol}，外部端口 {selectedRule.ExternalPort} 的转发规则吗？",
                PrimaryButtonText = "删除",
                CloseButtonText = "取消",
                XamlRoot = this.XamlRoot
            };

            ContentDialogResult result = await confirmDialog.ShowAsync();
            if (result == ContentDialogResult.Primary)
            {
                bool success = await _hyperVService.RemoveNatRuleAsync(_selectedVSwitch.Name, selectedRule.Protocol, selectedRule.ExternalPort);
                var statusDialog = new MessageDialog(success ? "规则删除成功！" : "规则删除失败。", "结果");
                await statusDialog.ShowAsync();
                await LoadNatRulesAsync(_selectedVSwitch.Name); // Refresh NAT rules
            }
        }
    }
}
