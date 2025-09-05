using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

namespace HyperVManager
{
    public class VM
    {
        public string Name { get; set; }
        public int State { get; set; } // Corresponds to VMState enum in PowerShell
        public TimeSpan Uptime { get; set; }
        public long MemoryAssigned { get; set; } // Bytes
        public int CPUUsage { get; set; } // Percentage
        public string GuestOS { get; set; }
        public List<string> IPAddresses { get; set; } = new List<string>();
        public string NetworkStatus { get; set; } // Custom status based on adapters
    }

    public class VMSimpleNetworkAdapter
    {
        public string Name { get; set; }
        public string SwitchName { get; set; }
        public string Status { get; set; } // e.g., "Ok"
    }

    public class VSwitch
    {
        public string Name { get; set; }
        public string SwitchType { get; set; } // e.g., "External", "Internal", "Private"
        public string Notes { get; set; }
        public string IPAddress { get; set; } // For Internal switches, host-side IP
        public string NatStatus { get; set; } // Custom status: "Enabled", "Disabled"
    }

    public class NatRule
    {
        public string Protocol { get; set; } // "TCP", "UDP"
        public int ExternalPort { get; set; }
        public string InternalIPAddress { get; set; }
        public int InternalPort { get; set; }
    }

    public class OnlineImage
    {
        public string Name { get; set; }
        public string Version { get; set; }
        public string Size { get; set; }
        public string Description { get; set; }
        public string DownloadUrl { get; set; }
    }

    public class LocalImage
    {
        public string Name { get; set; }
        public string Path { get; set; }
        public string Size { get; set; }
    }
}
