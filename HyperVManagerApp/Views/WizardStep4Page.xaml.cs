using Microsoft.UI.Xaml.Controls;
using System.Collections.ObjectModel;
using System.Threading.Tasks;
using System.Linq;

namespace HyperVManager.Views
{
    public sealed partial class WizardStep4Page : Page
    {
        public CreateVMWizardData ViewModel { get; set; }
        public ObservableCollection<VSwitch> VSwitches { get; set; }
        private HyperVService _hyperVService;

        public WizardStep4Page()
        {
            this.InitializeComponent();
            ViewModel = App.WizardData;
            this.DataContext = ViewModel;
            _hyperVService = new HyperVService();
            VSwitches = new ObservableCollection<VSwitch>();
            _ = LoadVSwitchesAsync();
        }

        private async Task LoadVSwitchesAsync()
        {
            var allSwitches = await _hyperVService.GetVSwitchesAsync();
            // Filter out Private switches as they are not typically used for general VM networking
            var filteredSwitches = allSwitches.Where(s => s.SwitchType != "Private").ToList();
            
            VSwitches.Clear();
            foreach (var s in filteredSwitches)
            {
                VSwitches.Add(s);
            }

            // Set default selection if not already set
            if (string.IsNullOrEmpty(ViewModel.SelectedVSwitchName) && VSwitches.Any())
            {
                ViewModel.SelectedVSwitchName = VSwitches.First().Name;
            }
        }
    }
}
