using Microsoft.UI.Xaml.Controls;
using System.Threading.Tasks;
using Microsoft.UI.Xaml;
using Windows.Storage.Pickers;
using System;
using WinRT.Interop;

namespace HyperVManager.Views
{
    public sealed partial class WizardStep1Page : Page
    {
        public CreateVMWizardData ViewModel { get; set; }

        public WizardStep1Page()
        {
            this.InitializeComponent();
            ViewModel = App.WizardData; // Access the shared data model
            this.DataContext = ViewModel; // Set DataContext for binding

            // Set default VM path
            if (string.IsNullOrEmpty(ViewModel.VmPath))
            {
                ViewModel.VmPath = System.IO.Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.UserProfile), "Hyper-V");
            }
        }

        private async void OnBrowsePathClicked(object sender, RoutedEventArgs e)
        {
            FolderPicker folderPicker = new FolderPicker();
            folderPicker.SuggestedStartLocation = PickerLocationId.DocumentsLibrary;
            folderPicker.FileTypeFilter.Add("*");

            // Get the current window's handle
            IntPtr hwnd = WindowNative.GetWindowHandle(App.Current.Windows.FirstOrDefault());
            InitializeWithWindow.Initialize(folderPicker, hwnd);

            Windows.Storage.StorageFolder folder = await folderPicker.PickSingleFolderAsync();

            if (folder != null)
            {
                ViewModel.VmPath = folder.Path;
            }
        }
    }
}
