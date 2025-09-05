public partial class MainPage : Page
    {
        public ObservableCollection<VM> VMs { get; set; }
        private HyperVService _hyperVService;
        private VM _selectedVM;

        public MainPage()
        {
            this.InitializeComponent();
            _hyperVService = new HyperVService();
            VMs = new ObservableCollection<VM>();
            _ = LoadVMsAsync();
        }

        private async Task LoadVMsAsync()
        {
            var vms = await _hyperVService.GetVMsAsync();
            VMs.Clear();
            foreach (var vm in vms)
            {
                VMs.Add(vm);
            }
            UpdateVMActionButtons();
        }

        private void OnVmDataGridSelectionChanged(object sender, SelectionChangedEventArgs e)
        {
            _selectedVM = VmDataGrid.SelectedItem as VM;
            UpdateVMActionButtons();
        }

        private void UpdateVMActionButtons()
        {
            bool isVMSelected = _selectedVM != null;
            bool isRunning = isVMSelected && _selectedVM.State == 2; // Assuming 2 is Running state
            bool isOff = isVMSelected && _selectedVM.State == 3; // Assuming 3 is Off state

            // In a real app, you'd enable/disable buttons here based on isVMSelected, isRunning, isOff
            // For now, buttons are always enabled in XAML, and we handle null _selectedVM in handlers.
        }

        private async void OnRefreshVMsClicked(object sender, RoutedEventArgs e)
        {
            _selectedVM = null;
            VmDataGrid.SelectedItem = null;
            await LoadVMsAsync();
        }

        private async void OnStartVMClicked(object sender, RoutedEventArgs e)
        {
            if (_selectedVM != null)
            {
                await _hyperVService.StartVMAsync(_selectedVM.Name);
                await LoadVMsAsync();
            }
        }

        private async void OnShutdownVMClicked(object sender, RoutedEventArgs e)
        {
            if (_selectedVM != null)
            {
                await _hyperVService.ShutdownVMAsync(_selectedVM.Name);
                await LoadVMsAsync();
            }
        }

        private async void OnStopVMClicked(object sender, RoutedEventArgs e)
        {
            if (_selectedVM != null)
            {
                await _hyperVService.StopVMAsync(_selectedVM.Name);
                await LoadVMsAsync();
            }
        }

        private async void OnDeleteVMClicked(object sender, RoutedEventArgs e)
        {
            if (_selectedVM != null)
            {
                // Add confirmation dialog in a real app
                await _hyperVService.DeleteVMAsync(_selectedVM.Name);
                await LoadVMsAsync();
            }
        }

        private void OnConnectVMClicked(object sender, RoutedEventArgs e)
        {
            if (_selectedVM != null)
            {
                _hyperVService.ConnectVM(_selectedVM.Name);
            }
        }

        private async void OnInvokeCommandInVMClicked(object sender, RoutedEventArgs e)
        {
            if (_selectedVM == null)
            {
                var noVmDialog = new MessageDialog("请先选择一个虚拟机。", "提示");
                await noVmDialog.ShowAsync();
                return;
            }

            // For simplicity, we'll use a basic input dialog.
            // In a real app, this would be a custom ContentDialog with input fields.
            string username = ""; // Replace with actual input from dialog
            string password = ""; // Replace with actual input from dialog
            string command = "";  // Replace with actual input from dialog

            // Let's just prompt for the command for now, and hardcode user/pass for testing
            var commandInputDialog = new MessageDialog("请输入要执行的PowerShell命令:", "远程命令");
            commandInputDialog.Commands.Add(new UICommand("执行", (cmd) => { command = "Get-Service"; /* Placeholder */ })); // Replace with actual command input
            commandInputDialog.Commands.Add(new UICommand("取消"));
            commandInputDialog.DefaultCommandIndex = 0;
            commandInputDialog.CancelCommandIndex = 1;
            var result = await commandInputDialog.ShowAsync();

            if (result.Label == "执行")
            {
                // Hardcoded credentials for testing. DO NOT DO THIS IN PRODUCTION.
                username = "Administrator"; // Example
                password = "Password123"; // Example
                command = "Get-Service"; // Example, replace with actual input

                var output = await _hyperVService.InvokeCommandInVMAsync(_selectedVM.Name, username, password, command);

                var outputDialog = new MessageDialog(output, "命令输出");
                await outputDialog.ShowAsync();
            }
        }
    }
}
