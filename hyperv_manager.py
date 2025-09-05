import PySimpleGUI as sg
import sys
import os
import webbrowser
import time
import json
from powershell_utils import (
    get_vms_data, start_vm, shutdown_vm, stop_vm, delete_vm, connect_vm,
    check_hyperv_status, install_hyperv, get_vswitches, 
    remove_vswitch, get_network_adapters, create_vswitch, 
    get_nat_networks, get_nat_rules, add_nat_rule, remove_nat_rule, 
    get_online_images, get_local_images, create_new_vm,
    set_vswitch_ip, create_nat_network, get_vswitch_ip_addresses,
    get_vm_network_adapters, connect_vm_to_switch, disconnect_vm_from_switch,
    get_vm_network_adapter_status, invoke_command_in_vm
)
from download_manager import DownloadManager

# --- UI Helper Functions ---

def refresh_vm_table(window):
    if not window or window.was_closed(): return
    state_map = {
        2: "正在运行", 3: "已关闭", 4: "正在运行", 5: "正在暂停", 6: "正在保存",
        8: "已暂停", 9: "已保存", 10: "正在停止", 11: "正在重置"
    }
    vms = get_vms_data()
    vm_data = []
    if vms:
        for vm in vms:
            net_status = "未知"
            adapters_status = get_vm_network_adapter_status(vm.get('Name'))
            if not adapters_status:
                net_status = "无网卡"
            else:
                is_connected = any(ad.get('SwitchName') for ad in adapters_status)
                has_error = any(ad.get('Status') != 'Ok' for ad in adapters_status)
                if has_error:
                    net_status = "状态异常"
                elif is_connected:
                    net_status = "已连接"
                else:
                    net_status = "未连接"
            state_code = vm.get('State', 0)
            state_text = state_map.get(state_code, f"未知({state_code})")
            os_text = vm.get('GuestOS') or "未知"
            vm_data.append([
                vm.get('Name', 'N/A'), state_text, net_status, os_text,
                ", ".join(vm.get('IPAddresses') if isinstance(vm.get('IPAddresses'), list) else [])
            ])
    window["-VM_TABLE-"].update(values=vm_data)
    for key in ["-START_VM-", "-SHUTDOWN_VM-", "-STOP_VM-", "-DELETE_VM-", "-CONNECT_VM-", "-CONFIG_VM_NET-", "-EXEC_COMMAND-"]:
        window[key].update(disabled=True)

def refresh_vswitch_table(window):
    if not window or window.was_closed(): return
    switches = get_vswitches()
    nats = get_nat_networks()
    nat_names = [n['Name'] for n in nats] if nats else []
    ip_addresses = get_vswitch_ip_addresses()
    vswitch_data = []
    if switches:
        for switch in switches:
            details = ""
            switch_name = switch.get('Name', 'N/A')
            if switch.get('SwitchType') == 'Internal':
                nat_status = "NAT: 已启用" if switch_name in nat_names else "NAT: 未启用"
                gateway = ip_addresses.get(switch_name, "未设置")
                details = f"{nat_status}, 网关: {gateway}"
            else:
                details = "不适用"
            vswitch_data.append([switch_name, switch.get('SwitchType', 'N/A'), details, switch.get('Notes', '')])
    window["-VSWITCH_TABLE-"].update(values=vswitch_data)
    window["-DELETE_VSWITCH-"].update(disabled=True)
    window['-NAT_CONTAINER-'].update(sg.Column([[]]))

# --- Modal Window Functions ---
def create_vswitch_window():
    adapter_list = get_network_adapters()
    type_mapping = {"外部": "External", "内部": "Internal", "专用": "Private"}
    reverse_type_mapping = {v: k for k, v in type_mapping.items()}
    descriptions = {
        "External": "将虚拟机连接到物理网络。需要绑定一个物理网卡。\n警告: 这会改变物理网卡的网络配置，可能导致现有网络连接(包括远程桌面)中断。",
        "Internal": "创建一个仅在当前主机上的虚拟机之间以及虚拟机与主机之间通信的交换机。\n虚拟机无法访问外部网络，但可以和主机互相访问。",
        "Private": "创建一个仅在当前主机上的虚拟机之间通信的交换机。\n虚拟机之间可以互相通信，但无法与主机或外部网络通信。"
    }
    layout = [
        [sg.Text("交换机名称:"), sg.Input(key="-NAME-")],
        [sg.Text("交换机类型:"), sg.Combo(list(type_mapping.keys()), default_value=reverse_type_mapping["Internal"], key="-TYPE-", readonly=True, enable_events=True)],
        [sg.Text("物理网卡:", visible=False, key="-ADAPTER_LABEL-"), sg.Combo(adapter_list, key="-ADAPTER-", visible=False, readonly=True)],
        [sg.Frame('说明', [[sg.Text(descriptions["Internal"], key="-DESC-", size=(50, 4))]])],
        [sg.Button("创建", key="-SUBMIT-"), sg.Button("取消")]
    ]
    window = sg.Window("创建虚拟交换机", layout, modal=True, finalize=True)
    while True:
        event, values = window.read()
        if event in (sg.WIN_CLOSED, "取消"):
            break
        if event == "-TYPE-":
            selected_type_chinese = values["-TYPE-"]
            switch_type_english = type_mapping[selected_type_chinese]
            is_external = switch_type_english == "External"
            window["-ADAPTER_LABEL-"].update(visible=is_external)
            window["-ADAPTER-"].update(visible=is_external)
            window["-DESC-"].update(descriptions[switch_type_english])
        if event == "-SUBMIT-":
            name = values["-NAME-"]
            selected_type_chinese = values["-TYPE-"]
            switch_type_english = type_mapping[selected_type_chinese]
            adapter = values["-ADAPTER-"] if switch_type_english == "External" else None
            if not name:
                sg.popup_error("交换机名称不能为空！")
                continue
            if switch_type_english == "External" and not adapter:
                sg.popup_error("外部交换机必须选择一个物理网卡！")
                continue
            success, output = create_vswitch(name, switch_type_english, adapter)
            if success:
                sg.popup("交换机创建成功！")
                break
            else:
                sg.popup_error(f"创建失败: {output}")
    window.close()

def create_add_nat_rule_window(nat_name):
    layout = [
        [sg.Text("协议:"), sg.Combo(["TCP", "UDP"], default_value="TCP", key="-PROTO-", readonly=True)],
        [sg.Text("外部端口:"), sg.Input(key="-EXT_PORT-")],
        [sg.Text("内部IP地址:"), sg.Input(key="-INT_IP-")],
        [sg.Text("内部端口:"), sg.Input(key="-INT_PORT-")],
        [sg.Button("添加"), sg.Button("取消")]
    ]
    window = sg.Window("添加端口转发规则", layout, modal=True, finalize=True)
    rule_added = False
    while True:
        event, values = window.read()
        if event in (sg.WIN_CLOSED, "取消"):
            break
        if event == "添加":
            if not all([values["-EXT_PORT-"], values["-INT_IP-"], values["-INT_PORT-"]]):
                sg.popup_error("所有字段都不能为空！")
                continue
            try:
                ext_port = int(values["-EXT_PORT-"])
                int_port = int(values["-INT_PORT-"])
            except ValueError:
                sg.popup_error("端口号必须是数字！")
                continue
            success, output = add_nat_rule(
                nat_name=nat_name,
                protocol=values["-PROTO-"],
                external_port=ext_port,
                internal_ip=values["-INT_IP-"],
                internal_port=int_port
            )
            if success:
                sg.popup("规则添加成功！")
                rule_added = True
                break
            else:
                sg.popup_error(f"添加失败: {output}")
    window.close()
    return rule_added

def create_vm_network_window(vm_name):
    adapters = get_vm_network_adapters(vm_name)
    switches = get_vswitches()
    switch_names = [s['Name'] for s in switches]
    if not adapters:
        sg.popup_error(f"虚拟机 '{vm_name}' 没有找到网络适配器。")
        return
    adapter_name = adapters[0].get('Name')
    current_switch = adapters[0].get('SwitchName') or "未连接"
    layout = [
        [sg.Text(f"正在为虚拟机 '{vm_name}' 配置网络")],
        [sg.Text(f"网卡: {adapter_name}")],
        [sg.Text(f"当前连接: {current_switch}")],
        [sg.HSep()],
        [sg.Text("选择要连接的交换机:"), sg.Combo(switch_names, key="-SWITCH_TO_CONNECT-", readonly=True)],
        [sg.Button("连接"), sg.Button("断开连接"), sg.Button("关闭")]
    ]
    window = sg.Window("设置虚拟机网络", layout, modal=True, finalize=True)
    while True:
        event, values = window.read()
        if event in (sg.WIN_CLOSED, "关闭"):
            break
        if event == "连接":
            selected_switch = values["-SWITCH_TO_CONNECT-"]
            if not selected_switch:
                sg.popup_error("请先选择一个交换机。")
                continue
            success, output = connect_vm_to_switch(vm_name, adapter_name, selected_switch)
            if success:
                sg.popup("连接成功！")
                break
            else:
                sg.popup_error(f"连接失败: {output}")
        if event == "断开连接":
            if current_switch == "未连接":
                sg.popup("该网卡尚未连接到任何交换机。")
            else:
                success, output = disconnect_vm_from_switch(vm_name, adapter_name)
                if success:
                    sg.popup("已断开连接。")
                    break
                else:
                    sg.popup_error(f"操作失败: {output}")
    window.close()

def create_remote_command_window(vm_name):
    layout = [
        [sg.Text(f"在虚拟机 '{vm_name}' 中执行命令", font=("Any 16"))],
        [sg.Text("此功能使用PowerShell Direct...", font=("Any 9"))],
        [sg.HSep()],
        [sg.Text("用户名", size=(10,1)), sg.Input(key="-USERNAME-")],
        [sg.Text("密码", size=(10,1)), sg.Input(key="-PASSWORD-", password_char='*')],
        [sg.HSep()],
        [sg.Text("输入要执行的PowerShell命令:")],
        [sg.Multiline(key="-COMMAND-", size=(80, 10), expand_x=True)],
        [sg.Button("执行", key="-SUBMIT-", expand_x=True)],
        [sg.HSep()],
        [sg.Text("输出结果:")],
        [sg.Multiline("", key="-OUTPUT-", size=(80, 15), disabled=True, expand_x=True, expand_y=True)]
    ]
    window = sg.Window("远程执行命令", layout, modal=True, resizable=True, finalize=True)
    while True:
        event, values = window.read()
        if event in (sg.WIN_CLOSED, "关闭"):
            break
        if event == "-SUBMIT-":
            username = values["-USERNAME-"]
            password = values["-PASSWORD-"]
            command = values["-COMMAND-"]
            if not all([username, password, command]):
                sg.popup_error("用户名、密码和命令均不能为空！")
                continue
            window["-OUTPUT-"].update("正在执行，请稍候...")
            window.refresh()
            success, result = invoke_command_in_vm(vm_name, username, password, command)
            if success:
                if result.get('success'):
                    window["-OUTPUT-"].update(result.get('output', '执行成功，但没有输出。'))
                else:
                    window["-OUTPUT-"].update(f"在虚拟机中执行命令失败:\n{result.get('error')}")
            else:
                window["-OUTPUT-"].update(f"执行PowerShell命令失败:\n{result.get('error')}")
    window.close()

# --- Layout Definitions ---
def build_online_images_layout():
    images = get_online_images()
    layout = []
    for i in range(0, len(images), 2):
        row = []
        img1 = images[i]
        url1 = img1.get("download_url")
        frame1_layout = [
            [sg.Text(img1.get("name"), font=("Any 14"))],
            [sg.Text(f"版本: {img1.get('version')} | 大小: {img1.get('size')}")],
            [sg.Text(img1.get("description"), size=(35, 2))],
            [sg.Button("在浏览器中打开", key=f"-OPEN_URL-{url1}", expand_x=True)]
        ]
        row.append(sg.Frame(title="", layout=frame1_layout, pad=(5,5), expand_x=True))
        if i + 1 < len(images):
            img2 = images[i+1]
            url2 = img2.get("download_url")
            frame2_layout = [
                [sg.Text(img2.get("name"), font=("Any 14"))],
                [sg.Text(f"版本: {img2.get('version')} | 大小: {img2.get('size')}")],
                [sg.Text(img2.get("description"), size=(35, 2))],
                [sg.Button("在浏览器中打开", key=f"-OPEN_URL-{url2}", expand_x=True)]
            ]
            row.append(sg.Frame(title="", layout=frame2_layout, pad=(5,5), expand_x=True))
        layout.append(row)
    return layout

def get_vm_list_layout():
    return [[sg.Text("虚拟机列表", font=("Any 20"))],
            [sg.Button("刷新", key="-REFRESH_VMS-"), sg.Button("连接", key="-CONNECT_VM-", disabled=True), sg.Button("启动", key="-START_VM-", disabled=True), sg.Button("设置网络", key="-CONFIG_VM_NET-", disabled=True), sg.Button("执行命令", key="-EXEC_COMMAND-", disabled=True), sg.Button("关机", key="-SHUTDOWN_VM-", disabled=True), sg.Button("强制停止", key="-STOP_VM-", disabled=True), sg.Button("删除", key="-DELETE_VM-", disabled=True, button_color=("white", "red"))],
            [sg.Table(values=[], headings=["名称", "状态", "网络状态", "操作系统", "IP地址"], key="-VM_TABLE-", auto_size_columns=False, col_widths=[25, 15, 15, 30, 30], justification='left', enable_events=True, num_rows=20, expand_x=True, expand_y=True)]]

def get_network_layout():
    return [[sg.Text("网络管理", font=("Any 20"))],
            [sg.Button("刷新", key="-REFRESH_VSWITCHES-"), sg.Button("创建交换机", key="-CREATE_VSWITCH-"), sg.Button("删除所选交换机", key="-DELETE_VSWITCH-", disabled=True, button_color=("white", "red"))],
            [sg.Column([[sg.Table(values=[], headings=["名称", "类型", "详情", "备注"], key="-VSWITCH_TABLE-", auto_size_columns=False, col_widths=[30, 15, 40, 25], justification='left', enable_events=True, num_rows=12, expand_x=True, expand_y=True)]]),
             sg.Column([], key='-NAT_CONTAINER-', vertical_alignment='top')]]

def get_create_vm_layout():
    # This layout is complex, so we define it fully here.
    step1 = [[sg.Text("步骤 1: 名称和位置",font=("Any 16"))],[sg.Text("虚拟机名称",size=(15,1)),sg.Input(key="-VM_NAME-")],[sg.Text("存储位置",size=(15,1)),sg.Input(os.path.join(os.path.expanduser("~"),"Hyper-V"),key="-VM_PATH-"),sg.FolderBrowse("浏览")] ,[sg.Checkbox("启用安全启动",key="-SECURE_BOOT-",default=True),sg.Text("?",tooltip="推荐用于 Windows 11 和其他现代操作系统。\n如果安装旧版系统（如 Windows 7），请取消勾选。")]]
    step2 = [[sg.Text("步骤 2: 内存和处理器",font=("Any 16"))],[sg.Text("内存 (MB)",size=(15,1)),sg.Slider(range=(1024,16384),default_value=2048,resolution=1024,orientation='h',size=(30,20),key="-VM_MEM-"),sg.Text("?",tooltip="为虚拟机分配的内存大小。\n此向导目前不支持动态内存。")], [sg.Text("CPU核心数",size=(15,1)),sg.Slider(range=(1,8),default_value=2,orientation='h',size=(30,20),key="-VM_CPU-"),sg.Text("?",tooltip="为虚拟机分配的CPU逻辑核心数量。\n建议不要超过主机物理核心数的一半。")]]
    step3 = [[sg.Text("步骤 3: 硬盘",font=("Any 16"))],[sg.Radio("创建新的虚拟硬盘","DISK",key="-DISK_NEW-",default=True,enable_events=True),sg.Text("?",tooltip="将为虚拟机创建一个全新的、空白的虚拟硬盘文件 (.vhdx)。\n您需要在虚拟机启动后手动安装操作系统。")], [sg.Text("大小 (GB)",size=(15,1)),sg.Input("50",key="-DISK_SIZE-",size=(10,1))],[sg.Radio("使用现有虚拟硬盘","DISK",key="-DISK_EXIST-",enable_events=True),sg.Text("?",tooltip="使用一个已经存在的虚拟硬盘文件 (.vhd 或 .vhdx)。\n这通常用于恢复虚拟机，或使用已预装好系统的硬盘文件。")], [sg.Text("路径",size=(15,1)),sg.Input(key="-DISK_PATH-",disabled=True),sg.FileBrowse("浏览",file_types=(("Virtual Hard Disks","*.vhdx *.vhd"),))]]
    step4 = [[sg.Text("步骤 4: 网络",font=("Any 16"))],[sg.Text("虚拟交换机",size=(15,1)),sg.Combo([],key="-VM_VSWITCH-",readonly=True,size=(30,1)),sg.Text("?",tooltip="为虚拟机选择一个网络连接。\nDefault Switch: 可访问外网的默认交换机。\nInternal/Private: 仅用于内部网络的交换机。")]]
    install_from_file_layout=[[sg.Text("选择一个本地的 .iso 镜像文件用于安装系统。")],[sg.Text("镜像路径",size=(15,1)),sg.Input(key="-ISO_PATH-"),sg.FileBrowse("浏览",file_types=(("ISO Files","*.iso"),))]]
    install_from_download_layout=[[sg.Text("从通过本软件下载的镜像列表中选择一个进行安装。")],[sg.Table(values=[],headings=["文件名","大小"],key="-DOWNLOADED_IMG_TABLE-",auto_size_columns=False,col_widths=[40,15],justification='left',enable_events=True,num_rows=8,expand_x=True)]]
    step5 = [[sg.Text("步骤 5: 安装选项",font=("Any 16"))],[sg.Text("说明: 如果您在步骤3中选择了'使用现有虚拟硬盘'，则无需在此选择安装介质。",font=("Any 9"),text_color="grey")],[sg.TabGroup([[sg.Tab("从本地文件",install_from_file_layout,key="-TAB_ISO_LOCAL-")],[sg.Tab("从已下载镜像",install_from_download_layout,key="-TAB_ISO_DOWNLOADED-")]],key="-ISO_TAB_GROUP-")]]
    step6 = [[sg.Text("步骤 6: 摘要",font=("Any 16"))],[sg.Text("请在创建前最后检查一遍您的配置：")],[sg.Multiline(size=(60,15),key="-VM_SUMMARY-",disabled=True)]]
    wizard_steps = {1: step1, 2: step2, 3: step3, 4: step4, 5: step5, 6: step6}
    wizard_layout = [[sg.Text("创建虚拟机向导",font=("Any 20"))],[sg.HorizontalSeparator()]]
    for i in range(1, 7):
        wizard_layout.append([sg.Column(wizard_steps[i], key=f"-WIZARD_STEP_{i}-", visible=(i==1))])
    wizard_layout.extend([[sg.HorizontalSeparator()],[sg.Button("上一步",key="-WIZARD_BACK-",disabled=True),sg.Button("下一步",key="-WIZARD_NEXT-")]])
    return wizard_layout

def get_images_layout():
    online_images_layout_content = build_online_images_layout()
    online_images_tab_content = [[sg.Text("提示: 点击按钮后将在外部浏览器打开下载页面。", font=("Any 9"), text_color="grey")],
                                 [sg.Column(online_images_layout_content, scrollable=True, vertical_scroll_only=True, expand_x=True, expand_y=True,  key='-IMAGE_LIST_COL-')]]
    local_images_layout = [[sg.Text("选择包含镜像文件的文件夹:")],
                           [sg.Input(key="-SCAN_PATH-", expand_x=True), sg.FolderBrowse("选择文件夹", target="-SCAN_PATH-")],
                           [sg.Button("开始扫描", key="-SCAN_LOCAL-", expand_x=True)],
                           [sg.HorizontalSeparator()],
                           [sg.Table(values=[], headings=["文件名", "路径", "大小"], key="-LOCAL_IMG_TABLE-", auto_size_columns=False, col_widths=[20, 50, 15], justification='left', enable_events=True, num_rows=11, expand_x=True)],
                           [sg.Button("使用选中镜像创建虚拟机", key="-CREATE_FROM_LOCAL-", disabled=True, expand_x=True)]]
    return [[sg.TabGroup([[sg.Tab("在线镜像市场", online_images_tab_content, expand_x=True, expand_y=True)],[sg.Tab("本地镜像", local_images_layout, expand_x=True, expand_y=True)]], key="-IMAGE_TABS-", expand_x=True, expand_y=True)]]

def get_system_check_layout():
    return [[sg.Text("系统状态检查", font=("Any 20"))],[sg.Button("检查Hyper-V状态", key="-CHECK_HYPERV-")],[sg.Text("点击上方按钮检查Hyper-V状态...", key="-STATUS_TEXT-", size=(60, 3))],[sg.Button("一键安装 Hyper-V", key="-INSTALL_HYPERV-", visible=False, button_color=("white", "green"))],[sg.Text("警告：安装过程需要管理员权限...", key="-INSTALL_WARN-", visible=False, text_color="orange")]]

# --- Main Window --- 
def main():
    sg.theme("SystemDefaultForReal")

    nav_column = sg.Column([
        [sg.Button("虚拟机", key="-NAV_VMS", size=(12, 2))],
        [sg.Button("网络设置", key="-NAV_NETWORK", size=(12, 2))],
        [sg.Button("创建虚拟机", key="-NAV_CREATE", size=(12, 2))],
        [sg.Button("系统镜像", key="-NAV_IMAGES", size=(12, 2))],
        [sg.Button("系统检查", key="-NAV_SYSTEM", size=(12, 2))],
    ], vertical_alignment='top')

    content_container = sg.Column([[]], key='-CONTENT_CONTAINER-', expand_x=True, expand_y=True)

    layout = [[nav_column, sg.VerticalSeparator(), content_container]]
    window = sg.Window("Hyper-V 统一管理器", layout, resizable=True, finalize=True, size=(950, 700))

    layout_generators = {
        "VMS": get_vm_list_layout,
        "NETWORK": get_network_layout,
        "CREATE": get_create_vm_layout,
        "IMAGES": get_images_layout,
        "SYSTEM": get_system_check_layout
    }

    active_view_key = "-VIEW_VMS-"
    window['-CONTENT_CONTAINER-'].update(sg.Column(layout_generators["VMS"](), key=active_view_key, expand_x=True, expand_y=True))
    window.refresh()
    refresh_vm_table(window)

    selected_vm_name = None
    selected_vswitch_name = None
    wizard_step = 1

    while True:
        event, values = window.read()
        if event == sg.WIN_CLOSED:
            break

        if event.startswith("-NAV_"):
            view_name = event.replace("-NAV_", "")
            new_view_key = f"-VIEW_{view_name}"
            
            window['-CONTENT_CONTAINER-'].update(sg.Column(layout_generators[view_name](), key=new_view_key, expand_x=True, expand_y=True))
            window.refresh()
            active_view_key = new_view_key
            
            if view_name == "VMS": refresh_vm_table(window)
            if view_name == "NETWORK": refresh_vswitch_table(window)

        if event == "-REFRESH_VMS-": refresh_vm_table(window)
        if event == "-REFRESH_VSWITCHES-": refresh_vswitch_table(window)

        if event == "-VSWITCH_TABLE-":
            if values["-VSWITCH_TABLE-"]:
                selected_vswitch_name, switch_type, nat_status_text, _ = window["-VSWITCH_TABLE-"].Values[values["-VSWITCH_TABLE-"][0]]
                window["-DELETE_VSWITCH-"].update(disabled=False)
                if switch_type == 'Internal':
                    is_nat_enabled = "NAT: 已启用" in nat_status_text
                    nat_rules_data = []
                    if is_nat_enabled:
                        nat_rules = get_nat_rules(selected_vswitch_name)
                        nat_rules_data = [[r.get('Protocol', 'N/A'), r.get('ExternalPort', 'N/A'), r.get('InternalIPAddress', 'N/A'), r.get('InternalPort', 'N/A')] for r in nat_rules]
                    nat_panel_layout = [[sg.Frame("NAT 网络详情", [
                        [sg.Text(f"交换机 '{selected_vswitch_name}' 的NAT状态: {'已启用' if is_nat_enabled else '未启用'}")],
                        [sg.Button("创建NAT网络", key="-CREATE_NAT-", disabled=is_nat_enabled), sg.Button("添加端口转发", key="-ADD_NAT_RULE-", disabled=not is_nat_enabled)],
                        [sg.Table(values=nat_rules_data, headings=["协议", "外部端口", "内部IP", "内部端口"], key="-NAT_RULES_TABLE-", auto_size_columns=False, justification='left', expand_x=True)],
                        [sg.Button("删除所选规则", key="-DELETE_NAT_RULE-", disabled=not is_nat_enabled)]
                    ], expand_x=True, vertical_alignment='top')]]
                    window['-NAT_CONTAINER-'].update(sg.Column(nat_panel_layout))
                else:
                    window['-NAT_CONTAINER-'].update(sg.Column([[]]))
            else:
                selected_vswitch_name = None
                window['-NAT_CONTAINER-'].update(sg.Column([[]]))

    window.close()

if __name__ == "__main__":
    import ctypes
    if ctypes.windll.shell32.IsUserAnAdmin():
        main()
    else:
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
