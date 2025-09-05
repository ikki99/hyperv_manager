using Microsoft.UI.Xaml.Controls;
using System.Collections.ObjectModel;
using System.Threading.Tasks;
using Microsoft.UI.Xaml;
using Windows.Storage.Pickers;
using System;
using WinRT.Interop;
using System.Linq;

namespace HyperVManager.Views
{
    public sealed partial class WizardStep5Page : Page
    {
        public CreateVMWizardData ViewModel { get; set; }
        public ObservableCollection<DownloadedImage> DownloadedImages { get; set; }

        public WizardStep5Page()
        {
            this.InitializeComponent();
            ViewModel = App.WizardData;
            this.DataContext = ViewModel;
            DownloadedImages = new ObservableCollection<DownloadedImage>();
            
            // Placeholder for downloaded images
            DownloadedImages.Add(new DownloadedImage { FileName = "Ubuntu-22.04.iso", Size = "2.5 GB" });
            DownloadedImages.Add(new DownloadedImage { FileName = "Windows-11.iso", Size = "5.0 GB" });
        }

        private async void OnBrowseIsoClicked(object sender, RoutedEventArgs e)
        {
            FileOpenPicker openPicker = new FileOpenPicker();
            openPicker.ViewMode = PickerViewMode.Thumbnail;
            openPicker.SuggestedStartLocation = PickerLocationId.DocumentsLibrary;
            openPicker.FileTypeFilter.Add(".iso");

            IntPtr hwnd = WindowNative.GetWindowHandle(App.Current.Windows.FirstOrDefault());
            InitializeWithWindow.Initialize(openPicker, hwnd);

            Windows.Storage.StorageFile file = await openPicker.PickSingleFileAsync();

            if (file != null)
            {
                ViewModel.IsoPath = file.Path;
            }
        }
    }

    // Placeholder class for downloaded images
    public class DownloadedImage
    {
        public string FileName { get; set; }
        public string Size { get; set; }
    }
}
