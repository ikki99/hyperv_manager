using Microsoft.UI.Xaml.Controls;
using System.Collections.ObjectModel;
using System.Threading.Tasks;
using Microsoft.UI.Xaml;
using Windows.Storage.Pickers;
using System;
using WinRT.Interop;
using System.Linq;
using System.Diagnostics;

namespace HyperVManager.Views
{
    public sealed partial class ImagesPage : Page
    {
        public ObservableCollection<OnlineImage> OnlineImages { get; set; }
        public ObservableCollection<LocalImage> LocalImages { get; set; }
        private HyperVService _hyperVService;

        public ImagesPage()
        {
            this.InitializeComponent();
            _hyperVService = new HyperVService();
            OnlineImages = new ObservableCollection<OnlineImage>();
            LocalImages = new ObservableCollection<LocalImage>();
            _ = LoadOnlineImagesAsync();
        }

        private async Task LoadOnlineImagesAsync()
        {
            var images = await _hyperVService.GetOnlineImagesAsync();
            OnlineImages.Clear();
            foreach (var image in images)
            {
                OnlineImages.Add(image);
            }
        }

        private void OnOpenDownloadUrlClicked(object sender, RoutedEventArgs e)
        {
            if (sender is Button button && button.Tag is string url)
            {
                _ = Windows.System.Launcher.LaunchUriAsync(new Uri(url));
            }
        }

        private async void OnBrowseScanPathClicked(object sender, RoutedEventArgs e)
        {
            FolderPicker folderPicker = new FolderPicker();
            folderPicker.SuggestedStartLocation = PickerLocationId.DocumentsLibrary;
            folderPicker.FileTypeFilter.Add("*");

            IntPtr hwnd = WindowNative.GetWindowHandle(App.Current.Windows.FirstOrDefault());
            InitializeWithWindow.Initialize(folderPicker, hwnd);

            Windows.Storage.StorageFolder folder = await folderPicker.PickSingleFolderAsync();

            if (folder != null)
            {
                ScanPathTextBox.Text = folder.Path;
            }
        }

        private async void OnScanLocalClicked(object sender, RoutedEventArgs e)
        {
            string scanPath = ScanPathTextBox.Text;
            if (string.IsNullOrEmpty(scanPath))
            {
                var dialog = new MessageDialog("请选择一个文件夹进行扫描。", "提示");
                await dialog.ShowAsync();
                return;
            }

            var images = await _hyperVService.GetLocalImagesAsync(scanPath);
            LocalImages.Clear();
            foreach (var image in images)
            {
                LocalImages.Add(image);
            }
        }

        private void OnCreateVMFromLocalClicked(object sender, RoutedEventArgs e)
        {
            if (LocalImagesDataGrid.SelectedItem is LocalImage selectedImage)
            {
                // Navigate to CreateVMPage and pre-fill ISO path
                App.WizardData.IsoPath = selectedImage.Path;
                // This page needs to be able to trigger navigation in the main window
                // For now, just show a message
                var dialog = new MessageDialog($"已选择镜像: {selectedImage.Name}\n请切换到 '创建虚拟机' 页面继续。", "提示");
                _ = dialog.ShowAsync();
            }
            else
            {
                var dialog = new MessageDialog("请先选择一个本地镜像。", "提示");
                _ = dialog.ShowAsync();
            }
        }
    }
}