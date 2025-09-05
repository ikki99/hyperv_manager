using Microsoft.UI.Xaml.Controls;
using System.Threading.Tasks;
using Microsoft.UI.Xaml;
using Windows.Storage.Pickers;
using System;
using WinRT.Interop;
using System.Linq;

namespace HyperVManager.Views
{
    public sealed partial class WizardStep3Page : Page
    {
        public CreateVMWizardData ViewModel { get; set; }

        public WizardStep3Page()
        {
            this.InitializeComponent();
            ViewModel = App.WizardData;
            this.DataContext = ViewModel;
        }

        private async void OnBrowseExistingDiskClicked(object sender, RoutedEventArgs e)
        {
            FileOpenPicker openPicker = new FileOpenPicker();
            openPicker.ViewMode = PickerViewMode.Thumbnail;
            openPicker.SuggestedStartLocation = PickerLocationId.DocumentsLibrary;
            openPicker.FileTypeFilter.Add(".vhd");
            openPicker.FileTypeFilter.Add(".vhdx");

            IntPtr hwnd = WindowNative.GetWindowHandle(App.Current.Windows.FirstOrDefault());
            InitializeWithWindow.Initialize(openPicker, hwnd);

            Windows.Storage.StorageFile file = await openPicker.PickSingleFileAsync();

            if (file != null)
            {
                ViewModel.ExistingDiskPath = file.Path;
            }
        }
    }
}
