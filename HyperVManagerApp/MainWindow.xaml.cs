using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;
using Microsoft.UI.Xaml.Navigation;
using HyperVManager.Views;
using System;

namespace HyperVManager
{
    public sealed partial class MainWindow : Window
    {
        public MainWindow()
        {
            this.InitializeComponent();
            Title = "Hyper-V 统一管理器";
            // Set the initial page
            ContentFrame.Navigate(typeof(MainPage));
        }

        private void NavigationViewControl_SelectionChanged(NavigationView sender, NavigationViewSelectionChangedEventArgs args)
        {
            if (args.IsSettingsSelected)
            {
                // Handle settings navigation if needed
            }
            else if (args.SelectedItem is NavigationViewItem selectedItem)
            {
                string pageTag = selectedItem.Tag?.ToString();
                Type pageType = null;

                switch (pageTag)
                {
                    case "VMs":
                        pageType = typeof(MainPage);
                        break;
                    case "Network":
                        pageType = typeof(NetworkPage);
                        break;
                    case "CreateVM":
                        pageType = typeof(CreateVMPage);
                        break;
                    case "Images":
                        pageType = typeof(ImagesPage);
                        break;
                    case "SystemCheck":
                        pageType = typeof(SystemCheckPage);
                        break;
                }

                if (pageType != null && ContentFrame.CurrentSourcePageType != pageType)
                {
                    ContentFrame.Navigate(pageType);
                }
            }
        }
    }
}
