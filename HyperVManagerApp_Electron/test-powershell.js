const PowerShellService = require('./powershell-service');

async function testGetVMs() {
    const psService = new PowerShellService();
    try {
        console.log('Fetching VMs...');
        const vms = await psService.getVMs();
        console.log('VMs fetched:', vms);
    } catch (error) {
        console.error('Error during test:', error);
    }
}

testGetVMs();
