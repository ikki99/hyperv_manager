using System;
using System.ComponentModel;
using System.Runtime.CompilerServices;

namespace HyperVManager
{
    public class CreateVMWizardData : INotifyPropertyChanged
    {
        private string _vmName;
        public string VmName
        {
            get => _vmName;
            set => SetProperty(ref _vmName, value);
        }

        private string _vmPath;
        public string VmPath
        {
            get => _vmPath;
            set => SetProperty(ref _vmPath, value);
        }

        private bool _secureBootEnabled = true;
        public bool SecureBootEnabled
        {
            get => _secureBootEnabled;
            set => SetProperty(ref _secureBootEnabled, value);
        }

        // Step 2: Memory and CPU
        private int _memoryMB = 2048;
        public int MemoryMB
        {
            get => _memoryMB;
            set => SetProperty(ref _memoryMB, value);
        }

        private int _cpuCores = 2;
        public int CpuCores
        {
            get => _cpuCores;
            set => SetProperty(ref _cpuCores, value);
        }

        // Step 3: Disk
        private bool _createNewDisk = true;
        public bool CreateNewDisk
        {
            get => _createNewDisk;
            set => SetProperty(ref _createNewDisk, value);
        }

        private int _diskSizeGB = 50;
        public int DiskSizeGB
        {
            get => _diskSizeGB;
            set => SetProperty(ref _diskSizeGB, value);
        }

        private string _existingDiskPath;
        public string ExistingDiskPath
        {
            get => _existingDiskPath;
            set => SetProperty(ref _existingDiskPath, value);
        }

        // Step 4: Network
        private string _selectedVSwitchName;
        public string SelectedVSwitchName
        {
            get => _selectedVSwitchName;
            set => SetProperty(ref _selectedVSwitchName, value);
        }

        // Step 5: Install Options
        private string _isoPath;
        public string IsoPath
        {
            get => _isoPath;
            set => SetProperty(ref _isoPath, value);
        }

        public event PropertyChangedEventHandler PropertyChanged;

        protected bool SetProperty<T>(ref T storage, T value, [CallerMemberName] string propertyName = null)
        {
            if (Equals(storage, value)) return false;
            storage = value;
            OnPropertyChanged(propertyName);
            return true;
        }

        protected void OnPropertyChanged([CallerMemberName] string propertyName = null)
        {
            PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(propertyName));
        }
    }
}
