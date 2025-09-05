using Microsoft.UI.Xaml.Controls;

namespace HyperVManager.Views
{
    public sealed partial class WizardStep2Page : Page
    {
        public CreateVMWizardData ViewModel { get; set; }

        public WizardStep2Page()
        {
            this.InitializeComponent();
            ViewModel = App.WizardData; // Access the shared data model
            this.DataContext = ViewModel; // Set DataContext for binding
        }
    }
}
