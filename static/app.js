const i18n = {
  zh: {
    productName: "FoxDesk",
    title: "指纹浏览器控制台",
    refresh: "刷新",
    profiles: "配置档案",
    profilesDesc: "管理 Camoufox 启动参数",
    import: "导入",
    export: "导出",
    new: "新建",
    editor: "档案编辑器",
    openDir: "目录",
    clone: "复制",
    launch: "启动",
    save: "保存",
    name: "名称",
    startupUrl: "启动网址",
    mode: "模式",
    targetOs: "目标系统",
    userDataDir: "用户数据目录",
    locale: "语言区域",
    proxyServer: "代理地址",
    proxyUsername: "代理用户名",
    proxyPassword: "代理密码",
    addons: "扩展路径",
    extraArgs: "额外启动参数",
    notes: "备注",
    sessions: "运行会话",
    sessionsDesc: "由管理器启动和跟踪的 Camoufox 进程",
    system: "系统与安装",
    systemDesc: "检查 Python 环境、Camoufox 包和浏览器文件",
    checking: "检查中",
    installed: "Camoufox 已安装",
    missing: "Camoufox 未安装",
    editing: "正在编辑",
    unsaved: "新档案尚未保存",
    choose: "选择一个档案后编辑",
    noProfiles: "暂无档案。点击新建开始。",
    noProcesses: "暂无进程。",
    profileSaved: "档案已保存",
    profileDeleted: "档案已删除",
    profileCloned: "档案已复制",
    profileImported: "档案已导入",
    exportDone: "导出已生成",
    launched: "已启动",
    stopped: "进程已停止",
    taskStarted: "任务已启动",
    openDirDone: "目录已打开",
    running: "运行中",
    stoppedTag: "已停止",
    stop: "停止",
    terminate: "终止",
    noLogs: "暂无日志",
    noActivity: "暂无操作记录",
    python: "Python",
    executable: "解释器",
    installedField: "已安装",
    version: "版本",
    path: "路径",
    unavailable: "不可用",
    yes: "是",
    no: "否",
    next: "下一步",
    done: "已完成",
    pending: "待执行",
    installStep: "安装 Python 包",
    fetchStep: "下载浏览器文件",
    testStep: "运行自检",
    tabBasic: "基础",
    tabProxy: "代理",
    tabFingerprint: "指纹环境",
    tabAdvanced: "高级",
    testProxy: "测试代理",
    testing: "测试中…",
    proxyOk: "连通",
    proxyFailed: "失败",
    exitIp: "出口 IP",
    latency: "延迟",
    downloadSource: "下载源",
    channelGithub: "GitHub 官方",
    channelGhproxy: "GitHub 镜像",
    channelCustom: "自定义镜像",
    customMirrorUrl: "自定义镜像地址",
    sessionDetail: "会话详情",
    startTime: "启动时间",
    uptime: "运行时长",
    profileSnapshot: "配置快照",
    downloadLogs: "下载日志",
    tags: "标签",
    tagsPlaceholder: "标签 (逗号分隔)",
    filterByTag: "按标签筛选",
    allTags: "全部",
    batchStart: "批量启动",
    selectedCount: "已选择 {n} 个",
    darkMode: "深色模式",
    tabProfiles: "配置档案",
    tabSessions: "运行会话",
    tabProxies: "代理池",
    tabSystem: "系统",
    searchProfiles: "搜索档案...",
    stopAll: "全部停止",
    viewLogs: "查看日志",
    taskHistory: "任务历史",
    fingerprintParams: "指纹参数",
    randomFingerprint: "随机生成",
    exportCookies: "导出 Cookie",
    importCookies: "导入 Cookie",
    activityLog: "操作日志",
    delete: "删除",
    proxyPool: "代理池",
    proxyPoolDesc: "统一管理代理，档案可引用代理 ID",
    proxyPoolSelect: "代理池引用",
    proxyManual: "手动填写 / 不使用池",
    healthCheck: "健康检查",
    cleanupRuntime: "清理运行时",
    checkUpdate: "检查更新",
    firstRunTitle: "首次使用",
    firstRunDesc: "检测到环境未就绪，正在自动安装…",
    goSetup: "打开引导",
    setupTitle: "欢迎使用 FoxDesk",
    setupSubtitle: "正在为你准备运行环境，无需手动操作",
    setupPreparing: "准备中…",
    setupInstalling: "正在安装环境…",
    setupDownloading: "正在下载浏览器…",
    setupVerifying: "正在验证…",
    setupDone: "环境已就绪",
    setupFailed: "自动安装失败",
    setupRetry: "重试",
    setupContinue: "开始使用",
    setupHint: "首次下载浏览器文件可能需要几分钟，请保持网络畅通。",
    setupStepCheck: "环境检测",
    setupStepPackage: "安装组件",
    setupStepFetch: "下载浏览器",
    setupStepVerify: "安装校验",
    stepPending: "等待中",
    stepRunning: "进行中",
    stepDone: "已完成",
    stepSkipped: "已跳过",
    stepFailed: "失败",
    updateAvailable: "发现新版本",
    openRelease: "打开发布页",
    oneClickUpdate: "一键更新",
    updateLater: "稍后",
    updateModalDesc: "检测到新版本，可一键下载并安装",
    currentVersion: "当前版本",
    latestVersion: "最新版本",
    updateIdle: "等待操作",
    updateChecking: "正在检查更新…",
    updateDownloading: "正在下载安装包…",
    updateReady: "下载完成，可安装",
    updateInstalling: "正在启动安装程序…",
    updateUpToDate: "已是最新版本",
    updateFailed: "更新失败",
    updateHint: "下载完成后将自动打开安装程序；安装时建议先关闭当前会话。",
    updateStarted: "已开始更新",
    templates: "模板",
    createFromTemplate: "从模板创建",
    unsavedChanges: "有未保存的修改，确定离开？",
    discardChanges: "放弃修改",
    keepEditing: "继续编辑",
    sessionError: "启动错误",
    wsEndpoint: "WebSocket 端点",
    copyEndpoint: "复制端点",
    copied: "已复制",
    ready: "就绪",
    failed: "失败",
    lastTest: "上次测试",
    neverTested: "未测试",
    assignProxy: "分配到所选档案",
    noProxies: "暂无代理。在上方添加或导入。",
    proxyCreated: "代理已创建",
    proxyDeleted: "代理已删除",
    proxyImported: "代理已导入",
    healthOk: "健康检查通过",
    healthFail: "健康检查未通过",
    runtimeCleaned: "运行时已清理",
    upToDate: "已是最新版本",
    templateCreated: "已从模板创建档案",
    runningBadge: "运行中",
    navigatorPlatform: "平台",
    navigatorVendor: "厂商",
    screenWidth: "屏幕宽度",
    screenHeight: "屏幕高度",
    colorDepth: "色深",
    pixelRatio: "像素比",
    webglVendor: "WebGL 厂商",
    webglRenderer: "WebGL 渲染器",
    webrtcMode: "WebRTC 模式",
    mediaDevices: "媒体设备",
    fonts: "字体",
    canvasNoise: "Canvas 噪声",
    audioNoise: "音频噪声",
    default: "默认",
    disable: "禁用",
    publicOnly: "仅公网",
    forceProxy: "强制代理",
    random: "随机",
    empty: "空",
    systemInfo: "系统信息",
    fetchBtn: "下载",
    checkFingerprint: "检测",
    bulkProxyImport: "批量导入代理（每行一个）",
    bulkProxyImportBtn: "批量导入",
    logs: "日志",
    allChecksPassed: "所有检测通过",
    issues: "个问题",
    openInBrowser: "在浏览器中打开",
    fingerprintGenerated: "指纹已生成",
    exported: "已导出",
    imported: "已导入",
    cookies: "个 Cookie",
    modeBrowser: "浏览器",
    modeServer: "远程服务",
    osAuto: "自动",
    osWindows: "Windows",
    osMacos: "macOS",
    osLinux: "Linux",
    toggleHeadless: "无界面模式",
    togglePersistent: "持久化上下文",
    toggleHumanize: "人性化",
    toggleGeoip: "地理位置",
    toggleBlockImages: "拦截图片",
    toggleBlockWebrtc: "拦截 WebRTC",
    toggleBlockWebgl: "拦截 WebGL",
    toggleDisableCoop: "禁用 COOP",
    toggleEnableCache: "启用缓存",
    appVersion: "应用版本",
    dataDir: "数据目录",
    timezone: "时区",
    taskInstall: "安装",
    taskVersion: "版本",
    taskPath: "路径",
    taskTest: "自检",
    taskFetch: "下载",
  },
  en: {
    productName: "FoxDesk",
    title: "Fingerprint Browser Console",
    refresh: "Refresh",
    profiles: "Profiles",
    profilesDesc: "Manage Camoufox launch options",
    import: "Import",
    export: "Export",
    new: "New",
    editor: "Profile Editor",
    openDir: "Folder",
    clone: "Clone",
    launch: "Launch",
    save: "Save",
    name: "Name",
    startupUrl: "Startup URL",
    mode: "Mode",
    targetOs: "Target OS",
    userDataDir: "User Data Dir",
    locale: "Locale",
    proxyServer: "Proxy Server",
    proxyUsername: "Proxy Username",
    proxyPassword: "Proxy Password",
    addons: "Addons",
    extraArgs: "Extra Args",
    notes: "Notes",
    sessions: "Sessions",
    sessionsDesc: "Camoufox processes launched and tracked by the manager",
    system: "System & Install",
    systemDesc: "Check Python, Camoufox package, and browser files",
    checking: "Checking",
    installed: "Camoufox installed",
    missing: "Camoufox missing",
    editing: "Editing",
    unsaved: "Unsaved new profile",
    choose: "Select a profile to edit",
    noProfiles: "No profiles yet. Create one to start.",
    noProcesses: "No processes.",
    profileSaved: "Profile saved",
    profileDeleted: "Profile deleted",
    profileCloned: "Profile cloned",
    profileImported: "Profiles imported",
    exportDone: "Export generated",
    launched: "Launched",
    toggleHeadless: "Headless",
    togglePersistent: "Persistent Context",
    toggleHumanize: "Humanize",
    toggleGeoip: "GeoIP",
    toggleBlockImages: "Block Images",
    toggleBlockWebrtc: "Block WebRTC",
    toggleBlockWebgl: "Block WebGL",
    toggleDisableCoop: "Disable COOP",
    toggleEnableCache: "Enable Cache",
    stopped: "Process stopped",
    taskStarted: "Task started",
    openDirDone: "Folder opened",
    running: "running",
    stoppedTag: "stopped",
    stop: "Stop",
    terminate: "Terminate",
    noLogs: "No logs yet",
    noActivity: "No activity yet",
    python: "Python",
    executable: "Executable",
    installedField: "Installed",
    version: "Version",
    path: "Path",
    unavailable: "not available",
    yes: "yes",
    no: "no",
    next: "Next",
    done: "Done",
    pending: "Pending",
    installStep: "Install Python package",
    fetchStep: "Fetch browser binary",
    testStep: "Run self test",
    tabBasic: "Basic",
    tabProxy: "Proxy",
    tabFingerprint: "Fingerprint",
    tabAdvanced: "Advanced",
    testProxy: "Test Proxy",
    testing: "Testing...",
    proxyOk: "Connected",
    proxyFailed: "Failed",
    exitIp: "Exit IP",
    latency: "Latency",
    downloadSource: "Download Source",
    channelGithub: "GitHub Official",
    channelGhproxy: "GitHub Mirror",
    channelCustom: "Custom Mirror",
    customMirrorUrl: "Custom Mirror URL",
    sessionDetail: "Session Detail",
    startTime: "Start Time",
    uptime: "Uptime",
    profileSnapshot: "Profile Snapshot",
    downloadLogs: "Download Logs",
    tags: "Tags",
    tagsPlaceholder: "Tags (comma-separated)",
    filterByTag: "Filter by tag",
    allTags: "All",
    batchStart: "Batch Start",
    selectedCount: "{n} selected",
    darkMode: "Dark Mode",
    tabProfiles: "Profiles",
    tabSessions: "Sessions",
    tabProxies: "Proxies",
    tabSystem: "System",
    searchProfiles: "Search profiles...",
    stopAll: "Stop All",
    viewLogs: "View Logs",
    taskHistory: "Task History",
    fingerprintParams: "Fingerprint",
    randomFingerprint: "Random",
    exportCookies: "Export Cookies",
    importCookies: "Import Cookies",
    activityLog: "Activity Log",
    delete: "Delete",
    proxyPool: "Proxy Pool",
    proxyPoolDesc: "Manage proxies and reference them from profiles",
    proxyPoolSelect: "Proxy pool ref",
    proxyManual: "Manual / none",
    healthCheck: "Health Check",
    cleanupRuntime: "Cleanup Runtime",
    checkUpdate: "Check Updates",
    firstRunTitle: "First Run",
    firstRunDesc: "Environment is not ready. Setting up automatically…",
    goSetup: "Open Setup",
    setupTitle: "Welcome to FoxDesk",
    setupSubtitle: "Preparing your environment — no manual steps needed",
    setupPreparing: "Preparing…",
    setupInstalling: "Installing components…",
    setupDownloading: "Downloading browser…",
    setupVerifying: "Verifying…",
    setupDone: "Environment ready",
    setupFailed: "Automatic setup failed",
    setupRetry: "Retry",
    setupContinue: "Get Started",
    setupHint: "First browser download may take a few minutes. Keep your network available.",
    setupStepCheck: "Environment check",
    setupStepPackage: "Install package",
    setupStepFetch: "Download browser",
    setupStepVerify: "Verify install",
    stepPending: "Pending",
    stepRunning: "Running",
    stepDone: "Done",
    stepSkipped: "Skipped",
    stepFailed: "Failed",
    updateAvailable: "Update available",
    openRelease: "Open Release",
    oneClickUpdate: "Update Now",
    updateLater: "Later",
    updateModalDesc: "A new version is available. Download and install in one click.",
    currentVersion: "Current",
    latestVersion: "Latest",
    updateIdle: "Waiting",
    updateChecking: "Checking for updates…",
    updateDownloading: "Downloading installer…",
    updateReady: "Ready to install",
    updateInstalling: "Launching installer…",
    updateUpToDate: "You're up to date",
    updateFailed: "Update failed",
    updateHint: "The installer will open automatically after download. Close running sessions first.",
    updateStarted: "Update started",
    templates: "Templates",
    createFromTemplate: "Create from template",
    unsavedChanges: "You have unsaved changes. Leave anyway?",
    discardChanges: "Discard",
    keepEditing: "Keep editing",
    sessionError: "Launch error",
    wsEndpoint: "WebSocket endpoint",
    copyEndpoint: "Copy endpoint",
    copied: "Copied",
    ready: "Ready",
    failed: "Failed",
    lastTest: "Last test",
    neverTested: "Never tested",
    assignProxy: "Assign to selected",
    noProxies: "No proxies yet. Add or import above.",
    proxyCreated: "Proxy created",
    proxyDeleted: "Proxy deleted",
    proxyImported: "Proxies imported",
    healthOk: "Health check passed",
    healthFail: "Health check failed",
    runtimeCleaned: "Runtime cleaned",
    upToDate: "Already up to date",
    templateCreated: "Profile created from template",
    runningBadge: "Running",
    navigatorPlatform: "Platform",
    navigatorVendor: "Vendor",
    screenWidth: "Screen Width",
    screenHeight: "Screen Height",
    colorDepth: "Color Depth",
    pixelRatio: "Pixel Ratio",
    webglVendor: "WebGL Vendor",
    webglRenderer: "WebGL Renderer",
    webrtcMode: "WebRTC Mode",
    mediaDevices: "Media Devices",
    fonts: "Fonts",
    canvasNoise: "Canvas Noise",
    audioNoise: "Audio Noise",
    default: "Default",
    disable: "Disable",
    publicOnly: "Public Only",
    forceProxy: "Force Proxy",
    random: "Random",
    empty: "Empty",
    systemInfo: "System Info",
    fetchBtn: "Fetch",
    checkFingerprint: "Check",
    bulkProxyImport: "Bulk Import Proxies (one per line)",
    bulkProxyImportBtn: "Import",
    logs: "Logs",
    allChecksPassed: "All checks passed",
    issues: "issue(s)",
    openInBrowser: "Open in browser",
    fingerprintGenerated: "Fingerprint generated",
    exported: "Exported",
    imported: "Imported",
    cookies: "cookies",
    modeBrowser: "Browser",
    modeServer: "Remote Server",
    osAuto: "Auto",
    osWindows: "Windows",
    osMacos: "macOS",
    osLinux: "Linux",
    appVersion: "App Version",
    dataDir: "Data Dir",
    timezone: "Timezone",
    taskInstall: "Install",
    taskVersion: "Version",
    taskPath: "Path",
    taskTest: "Test",
    taskFetch: "Fetch",
  },
};

const state = {
  lang: localStorage.getItem("cm-lang") || "zh",
  theme: localStorage.getItem("cm-theme") || "light",
  profiles: [],
  selectedId: null,
  system: null,
  channels: [],
  selectedChannel: "github",
  selectedProfiles: new Set(),
  tagFilter: null,
  allTags: [],
  proxies: [],
  templates: [],
  sessions: [],
  formSnapshot: "",
  formDirty: false,
  firstRunDismissed: localStorage.getItem("cm-first-run-dismissed") === "1",
  updateDismissedTag: localStorage.getItem("cm-update-dismissed") || "",
  viewMode: localStorage.getItem("cm-view-mode") || "list",
  setup: null,
  setupChannel: localStorage.getItem("cm-setup-channel") || "github",
  setupPollTimer: null,
  setupAutoStarted: false,
  setupBlocking: false,
  updateInfo: null,
  updatePollTimer: null,
  updateModalOpen: false,
  lastAutoUpdateCheck: 0,
};

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => Array.from(document.querySelectorAll(selector));
const t = (key) => i18n[state.lang][key] || i18n.zh[key] || key;

function setLanguage(lang) {
  state.lang = lang;
  localStorage.setItem("cm-lang", lang);
  document.documentElement.lang = lang === "zh" ? "zh-CN" : "en";
  $$("[data-i18n]").forEach((el) => {
    const key = el.dataset.i18n;
    if (key) el.textContent = t(key);
  });
  $$("[data-i18n-placeholder]").forEach((el) => {
    el.placeholder = t(el.dataset.i18nPlaceholder) || el.placeholder;
  });
  $$("[data-lang]").forEach((button) => {
    button.classList.toggle("active", button.dataset.lang === lang);
  });
  renderSystem();
  renderProfiles();
  renderTemplates();
  renderProxyPool();
  fillProxySelect($("#proxyPoolSelect")?.value || "");
  loadProfile(state.profiles.find((item) => item.id === state.selectedId) || null, false);
  renderIcons();
}

function applyTheme(theme) {
  state.theme = theme;
  document.documentElement.dataset.theme = theme;
  localStorage.setItem("cm-theme", theme);
  const icon = document.querySelector("#themeToggle i");
  if (icon) icon.setAttribute("data-lucide", theme === "dark" ? "sun" : "moon");
  renderIcons();
}

function toggleTheme() {
  applyTheme(state.theme === "dark" ? "light" : "dark");
}

function toast(message) {
  const el = $("#toast");
  el.textContent = message;
  el.classList.add("show");
  window.clearTimeout(toast.timer);
  toast.timer = window.setTimeout(() => el.classList.remove("show"), 2800);
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const data = await response.json();
      detail = data.detail || detail;
    } catch (_) {}
    throw new Error(detail);
  }
  return response.json();
}

function splitList(value) {
  return String(value || "")
    .split(/[\n,]+/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function formToProfile() {
  const form = $("#profileForm");
  const data = new FormData(form);
  // Locale fields are mirrored by input listeners; either value is fine.
  const locale = ((data.get("locale") || data.get("fp_locale") || "") + "").trim();
  return {
    name: data.get("name") || "Untitled",
    startup_url: data.get("startup_url") || "",
    mode: data.get("mode") || "browser",
    os: data.get("os") || "auto",
    headless: Boolean(data.get("headless")),
    persistent_context: Boolean(data.get("persistent_context")),
    user_data_dir: data.get("user_data_dir") || "",
    humanize: Boolean(data.get("humanize")),
    geoip: Boolean(data.get("geoip")),
    locale,
    proxy_id: data.get("proxy_id") || "",
    proxy: {
      server: data.get("proxy_server") || "",
      username: data.get("proxy_username") || "",
      password: data.get("proxy_password") || "",
    },
    block_images: Boolean(data.get("block_images")),
    block_webrtc: Boolean(data.get("block_webrtc")),
    block_webgl: Boolean(data.get("block_webgl")),
    disable_coop: Boolean(data.get("disable_coop")),
    enable_cache: Boolean(data.get("enable_cache")),
    addons: splitList(data.get("addons")),
    extra_args: splitList(data.get("extra_args")),
    tags: splitList(data.get("tags")),
    notes: data.get("notes") || "",
    // Fingerprint
    navigator_platform: data.get("navigator_platform") || "",
    navigator_vendor: data.get("navigator_vendor") || "",
    screen_width: parseInt(data.get("screen_width")) || 0,
    screen_height: parseInt(data.get("screen_height")) || 0,
    screen_color_depth: parseInt(data.get("screen_color_depth")) || 0,
    device_pixel_ratio: parseFloat(data.get("device_pixel_ratio")) || 0,
    canvas_noise: Boolean(data.get("canvas_noise")),
    webgl_vendor: data.get("webgl_vendor") || "",
    webgl_renderer: data.get("webgl_renderer") || "",
    audio_noise: Boolean(data.get("audio_noise")),
    fonts: splitList(data.get("fonts")),
    timezone: data.get("timezone") || "",
    webrtc_mode: data.get("webrtc_mode") || "default",
    media_devices: data.get("media_devices") || "default",
    keyboard_layout: data.get("keyboard_layout") || "",
  };
}

function captureFormSnapshot() {
  try {
    state.formSnapshot = JSON.stringify(formToProfile());
    state.formDirty = false;
  } catch (_) {
    state.formSnapshot = "";
    state.formDirty = false;
  }
}

function markFormDirty() {
  try {
    const current = JSON.stringify(formToProfile());
    state.formDirty = Boolean(state.formSnapshot) && current !== state.formSnapshot;
  } catch (_) {
    state.formDirty = true;
  }
}

function confirmDiscardIfDirty() {
  if (!state.formDirty) return true;
  return window.confirm(t("unsavedChanges"));
}

function runningProfileIds() {
  return new Set(
    (state.sessions || [])
      .filter((s) => String(s.status || "").startsWith("running") || s.status === "running")
      .map((s) => s.profile_id)
      .filter(Boolean),
  );
}

function fillProxySelect(selectedId = "") {
  const select = $("#proxyPoolSelect");
  if (!select) return;
  const options = [`<option value="">${t("proxyManual")}</option>`].concat(
    (state.proxies || []).map((p) => {
      const label = `${p.name || p.server || p.id}${p.last_ok === true ? " ✓" : p.last_ok === false ? " ✗" : ""}`;
      return `<option value="${escapeHtml(p.id)}">${escapeHtml(label)}</option>`;
    }),
  );
  select.innerHTML = options.join("");
  select.value = selectedId || "";
}

function setCheckbox(form, name, value) {
  form.elements[name].checked = Boolean(value);
}

function defaultProfile() {
  const slug = `profile-${Date.now().toString(36)}`;
  return {
    name: state.lang === "zh" ? "新档案" : "New profile",
    startup_url: "https://browserleaks.com/javascript",
    mode: "browser",
    os: "auto",
    headless: false,
    persistent_context: true,
    // Backend will resolve under %APPDATA%/CamoufoxManager/profiles when relative.
    user_data_dir: `profiles/${slug}`,
    humanize: true,
    geoip: false,
    locale: "",
    proxy_id: "",
    proxy: {},
    block_images: false,
    block_webrtc: true,
    block_webgl: false,
    disable_coop: true,
    enable_cache: true,
    addons: [],
    extra_args: [],
    tags: [],
    notes: "",
  };
}

function loadProfile(profile, fillForm = true) {
  if (fillForm && state.formDirty && !confirmDiscardIfDirty()) return;
  state.selectedId = profile?.id || null;
  const form = $("#profileForm");
  const value = profile || defaultProfile();

  if (fillForm) {
    form.reset();
    form.elements.name.value = value.name || "";
    form.elements.startup_url.value = value.startup_url || "";
    form.elements.mode.value = value.mode || "browser";
    form.elements.os.value = value.os || "auto";
    form.elements.user_data_dir.value = value.user_data_dir || "";
    form.elements.locale.value = value.locale || "";
    fillProxySelect(value.proxy_id || "");
    form.elements.proxy_server.value = value.proxy?.server || "";
    form.elements.proxy_username.value = value.proxy?.username || "";
    form.elements.proxy_password.value = value.proxy?.password || "";
    form.elements.addons.value = (value.addons || []).join(", ");
    form.elements.extra_args.value = (value.extra_args || []).join(", ");
    form.elements.tags.value = (value.tags || []).join(", ");
    form.elements.notes.value = value.notes || "";
    // Fingerprint fields
    form.elements.navigator_platform.value = value.navigator_platform || "";
    form.elements.navigator_vendor.value = value.navigator_vendor || "";
    form.elements.screen_width.value = value.screen_width || "";
    form.elements.screen_height.value = value.screen_height || "";
    form.elements.screen_color_depth.value = value.screen_color_depth || "";
    form.elements.device_pixel_ratio.value = value.device_pixel_ratio || "";
    form.elements.webgl_vendor.value = value.webgl_vendor || "";
    form.elements.webgl_renderer.value = value.webgl_renderer || "";
    form.elements.timezone.value = value.timezone || "";
    if (form.elements.fp_locale) form.elements.fp_locale.value = value.locale || "";
    form.elements.webrtc_mode.value = value.webrtc_mode || "default";
    form.elements.media_devices.value = value.media_devices || "default";
    form.elements.fonts.value = (value.fonts || []).join(", ");
    setCheckbox(form, "canvas_noise", value.canvas_noise !== false);
    setCheckbox(form, "audio_noise", value.audio_noise !== false);
    [
      "headless",
      "persistent_context",
      "humanize",
      "geoip",
      "block_images",
      "block_webrtc",
      "block_webgl",
      "disable_coop",
      "enable_cache",
    ].forEach((name) => setCheckbox(form, name, value[name]));
    // Reset to basic tab
    $$(".tab-bar button").forEach((btn) => btn.classList.remove("active"));
    $$(".tab-content").forEach((tc) => tc.classList.remove("active"));
    const basicTab = $(".tab-bar button[data-tab='basic']");
    const basicContent = $(".tab-content[data-tab-content='basic']");
    if (basicTab) basicTab.classList.add("active");
    if (basicContent) basicContent.classList.add("active");
    // Clear proxy test result
    const proxyResult = $("#proxyResult");
    if (proxyResult) proxyResult.innerHTML = "";
    captureFormSnapshot();
  }

  $("#editorHint").textContent = state.selectedId ? `${t("editing")} ${value.name}` : t("unsaved");
  $("#cloneBtn").disabled = !state.selectedId;
  $("#openDirBtn").disabled = !state.selectedId;
  renderProfiles();
}

function profileTags(profile) {
  const tags = [profile.mode, profile.os, profile.headless ? "headless" : "visible"];
  if (profile.proxy?.server || profile.proxy_id) tags.push("proxy");
  if (profile.geoip) tags.push("geoip");
  if (profile.persistent_context) tags.push("persistent");
  return tags;
}

const TAG_I18N = {
  browser: { zh: "浏览器", en: "browser" },
  server: { zh: "服务端", en: "server" },
  windows: { zh: "Windows", en: "Windows" },
  macos: { zh: "macOS", en: "macOS" },
  linux: { zh: "Linux", en: "Linux" },
  auto: { zh: "自动", en: "auto" },
  headless: { zh: "无界面", en: "headless" },
  visible: { zh: "有界面", en: "visible" },
  proxy: { zh: "代理", en: "proxy" },
  geoip: { zh: "地理位置", en: "geoip" },
  persistent: { zh: "持久化", en: "persistent" },
};

function translateTag(tag) {
  const entry = TAG_I18N[tag];
  if (!entry) return tag;
  return entry[state.lang] || entry.en || tag;
}

function renderTagFilter() {
  const bar = $("#tagFilterBar");
  if (!bar) return;
  const allTags = new Set();
  state.profiles.forEach((p) => {
    profileTags(p).forEach((tag) => allTags.add(tag));
    (p.tags || []).forEach((tag) => allTags.add(tag));
  });
  state.allTags = [...allTags].sort();
  if (!state.allTags.length) {
    bar.style.display = "none";
    return;
  }
  bar.style.display = "flex";
  bar.innerHTML = `<button class="tag ${state.tagFilter === null ? "running" : ""}" data-tag-filter="" type="button">${t("allTags")}</button>` +
    state.allTags.map((tag) =>
      `<button class="tag ${state.tagFilter === tag ? "running" : ""}" data-tag-filter="${escapeHtml(tag)}" type="button">${escapeHtml(translateTag(tag))}</button>`
    ).join("");
  bar.querySelectorAll("[data-tag-filter]").forEach((btn) => {
    btn.addEventListener("click", () => {
      state.tagFilter = btn.dataset.tagFilter || null;
      renderProfiles();
      renderTagFilter();
    });
  });
}

function renderProfiles() {
  const list = $("#profileList");
  if (!list) return;
  let profiles = state.profiles;
  // Apply search filter
  const searchEl = $("#profileSearch");
  const searchTerm = searchEl ? searchEl.value.trim().toLowerCase() : "";
  if (searchTerm) {
    profiles = profiles.filter((p) => {
      return (p.name || "").toLowerCase().includes(searchTerm) ||
        (p.startup_url || "").toLowerCase().includes(searchTerm) ||
        (p.notes || "").toLowerCase().includes(searchTerm) ||
        (p.tags || []).some((tag) => tag.toLowerCase().includes(searchTerm));
    });
  }
  // Apply tag filter
  if (state.tagFilter) {
    profiles = profiles.filter((p) => {
      const computed = profileTags(p);
      const user = p.tags || [];
      return computed.includes(state.tagFilter) || user.includes(state.tagFilter);
    });
  }
  renderTagFilter();
  // Table view mode
  if (state.viewMode === "table") {
    renderProfileTable(profiles);
    return;
  }
  if (!profiles.length) {
    list.innerHTML = `<div class="empty">${t("noProfiles")}</div>`;
    updateBatchBar();
    return;
  }
  const running = runningProfileIds();
  list.innerHTML = profiles
    .map(
      (profile) => `
        <article class="profile-row ${profile.id === state.selectedId ? "selected" : ""} has-batch" data-profile-id="${profile.id}">
          <input type="checkbox" class="batch-check" data-batch-id="${profile.id}" ${state.selectedProfiles.has(profile.id) ? "checked" : ""} />
          <div class="row-main">
            <div>
              <div class="row-title">${escapeHtml(profile.name)}${running.has(profile.id) ? ` <span class="live-dot" title="${t("runningBadge")}"></span>` : ""}</div>
              <div class="row-meta">${escapeHtml(profile.startup_url || "about:blank")}</div>
            </div>
            <button class="button secondary delete-profile icon-only" data-delete-id="${profile.id}" type="button" title="Delete">
              <i data-lucide="trash-2"></i>
            </button>
          </div>
          <div class="tagline">
            ${running.has(profile.id) ? `<span class="tag running">${t("runningBadge")}</span>` : ""}
            ${profileTags(profile).map((tag) => `<span class="tag">${escapeHtml(translateTag(tag))}</span>`).join("")}
            ${(profile.tags || []).map((tag) => `<span class="tag" style="background:var(--accent);color:white">${escapeHtml(tag)}</span>`).join("")}
          </div>
        </article>
      `,
    )
    .join("");

  $$(".profile-row").forEach((row) => {
    row.addEventListener("click", (event) => {
      if (event.target.closest(".delete-profile") || event.target.closest(".batch-check")) return;
      const profile = state.profiles.find((item) => item.id === row.dataset.profileId);
      loadProfile(profile);
    });
    row.addEventListener("contextmenu", (event) => {
      event.preventDefault();
      showContextMenu(event, row.dataset.profileId);
    });
  });
  $$(".delete-profile").forEach((button) => {
    button.addEventListener("click", async () => deleteProfile(button.dataset.deleteId));
  });
  $$(".batch-check").forEach((cb) => {
    cb.addEventListener("change", () => {
      if (cb.checked) state.selectedProfiles.add(cb.dataset.batchId);
      else state.selectedProfiles.delete(cb.dataset.batchId);
      updateBatchBar();
    });
  });
  renderIcons();
  updateBatchBar();
}

function updateBatchBar() {
  const bar = $("#batchBar");
  const count = $("#batchCount");
  if (!bar || !count) return;
  const n = state.selectedProfiles.size;
  if (n < 2) {
    bar.classList.add("hidden");
    return;
  }
  bar.classList.remove("hidden");
  count.textContent = t("selectedCount").replace("{n}", n);
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => {
    const map = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;" };
    return map[char];
  });
}

async function loadProfiles() {
  state.profiles = await api("/api/profiles");
  if (!state.selectedId && state.profiles[0]) {
    loadProfile(state.profiles[0]);
  } else {
    const selected = state.profiles.find((item) => item.id === state.selectedId);
    if (selected) loadProfile(selected, false);
    renderProfiles();
  }
}

async function saveProfile() {
  const payload = formToProfile();
  const path = state.selectedId ? `/api/profiles/${state.selectedId}` : "/api/profiles";
  const method = state.selectedId ? "PUT" : "POST";
  const saved = await api(path, { method, body: JSON.stringify(payload) });
  state.selectedId = saved.id;
  state.formDirty = false;
  await loadProfiles();
  loadProfile(saved);
  toast(t("profileSaved"));
  return saved;
}

async function deleteProfile(id) {
  const profile = state.profiles.find((item) => item.id === id);
  const label = profile?.name || id;
  if (!confirm(`${t("delete")} "${label}"?`)) return;
  await api(`/api/profiles/${id}`, { method: "DELETE" });
  if (state.selectedId === id) state.selectedId = null;
  await loadProfiles();
  if (state.profiles[0]) loadProfile(state.profiles[0]);
  else loadProfile(null);
  toast(t("profileDeleted"));
}

async function cloneSelected() {
  if (!state.selectedId) return;
  const cloned = await api(`/api/profiles/${state.selectedId}/clone`, { method: "POST", body: "{}" });
  await loadProfiles();
  loadProfile(cloned);
  toast(t("profileCloned"));
}

async function openSelectedDir() {
  if (!state.selectedId) return;
  await api(`/api/profiles/${state.selectedId}/open-data-dir`, { method: "POST", body: "{}" });
  toast(t("openDirDone"));
}

async function launchSelected() {
  if (!state.selectedId) {
    await saveProfile();
  }
  const result = await api("/api/sessions", {
    method: "POST",
    body: JSON.stringify({ profile_id: state.selectedId }),
  });
  toast(`${t("launched")} ${result.label}`);
  await loadSessions();
}

async function exportProfiles() {
  const data = await api("/api/profiles/export");
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `camoufox-profiles-${new Date().toISOString().slice(0, 10)}.json`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
  toast(t("exportDone"));
}

async function importProfiles(file) {
  const text = await file.text();
  const parsed = JSON.parse(text);
  const profiles = Array.isArray(parsed) ? parsed : parsed.profiles;
  if (!Array.isArray(profiles)) {
    throw new Error("Invalid profile export");
  }
  await api("/api/profiles/import", {
    method: "POST",
    body: JSON.stringify({ profiles, replace: false }),
  });
  await loadProfiles();
  toast(t("profileImported"));
}

function renderInstallFlow() {
  const flow = $("#installFlow");
  if (!flow || !state.system?.install_flow) return;
  const labels = {
    install: t("installStep"),
    fetch: t("fetchStep"),
    test: t("testStep"),
  };
  flow.innerHTML = state.system.install_flow
    .map((step, index) => {
      const done = Boolean(step.done);
      const current = !done && state.system.install_flow.slice(0, index).every((item) => item.done);
      return `
        <button class="install-step ${done ? "done" : ""} ${current ? "current" : ""}" data-flow-task="${step.task}" type="button">
          <span class="step-index">${done ? "✓" : index + 1}</span>
          <span>
            <strong>${escapeHtml(labels[step.task] || step.label)}</strong>
            <small>${done ? t("done") : current ? t("next") : t("pending")}</small>
          </span>
        </button>
      `;
    })
    .join("");

  $$("[data-flow-task]").forEach((button) => {
    button.addEventListener("click", async () => {
      try {
        await startTask(button.dataset.flowTask);
      } catch (error) {
        toast(error.message);
      }
    });
  });
}

function renderSystem() {
  const status = $("#installStatus");
  const grid = $("#systemGrid");
  const sys = state.system;
  if (!status || !grid) return;
  status.textContent = sys?.camoufox_installed ? t("installed") : sys ? t("missing") : t("checking");
  status.classList.toggle("good", Boolean(sys?.camoufox_installed));
  status.classList.toggle("bad", Boolean(sys && !sys.camoufox_installed));

  const version = sys?.camoufox_version?.stdout || sys?.camoufox_version?.stderr || t("unavailable");
  const path = sys?.camoufox_path?.stdout || sys?.camoufox_path?.stderr || t("unavailable");
  grid.innerHTML = `
    <dt>${t("appVersion")}</dt><dd>${escapeHtml(sys?.app_version || "")}</dd>
    <dt>${t("python")}</dt><dd>${escapeHtml(sys?.python || "")}</dd>
    <dt>${t("executable")}</dt><dd>${escapeHtml(sys?.executable || "")}</dd>
    <dt>${t("installedField")}</dt><dd>${sys?.camoufox_installed ? t("yes") : t("no")}</dd>
    <dt>${t("version")}</dt><dd>${escapeHtml(version)}</dd>
    <dt>${t("path")}</dt><dd>${escapeHtml(path)}</dd>
    <dt>${t("dataDir")}</dt><dd>${escapeHtml(sys?.data_dir || "")}</dd>
  `;
  renderInstallFlow();
}

async function loadSystem() {
  state.system = await api("/api/system");
  renderSystem();
  updateFirstRunBanner();
}

async function startTask(name) {
  const task = await api(`/api/tasks/${name}`, { method: "POST", body: JSON.stringify({ args: [] }) });
  toast(`${t("taskStarted")}：${task.label}`);
  await loadTasks();
}

function renderProcesses(selector, processes, stopLabel = t("stop"), isSession = false) {
  const list = $(selector);
  if (!processes.length) {
    list.innerHTML = `<div class="empty">${t("noProcesses")}</div>`;
    return;
  }
  list.innerHTML = processes
    .map((item) => {
      const running = item.status === "running";
      const failed = Boolean(item.failed || item.error_message);
      const started = new Date(item.started_at * 1000);
      const uptimeMs = Date.now() - item.started_at * 1000;
      const uptimeSec = Math.floor(uptimeMs / 1000);
      const uptimeStr = `${Math.floor(uptimeSec / 3600)}h ${Math.floor((uptimeSec % 3600) / 60)}m ${uptimeSec % 60}s`;
      const statusTag = failed
        ? `<span class="tag failed">${t("failed")}</span>`
        : running
          ? `<span class="tag running">${item.ready ? t("ready") : t("running")}</span>`
          : `<span class="tag failed">${t("stoppedTag")}</span>`;
      const errorBlock = item.error_message
        ? `<div class="session-error"><strong>${t("sessionError")}:</strong> ${escapeHtml(item.error_message)}</div>`
        : "";
      const wsBlock = item.ws_endpoint
        ? `<div class="session-ws">
             <span>${t("wsEndpoint")}: <code>${escapeHtml(item.ws_endpoint)}</code></span>
             <button class="button secondary copy-ws" data-ws="${escapeHtml(item.ws_endpoint)}" type="button" style="min-height:28px;font-size:12px">${t("copyEndpoint")}</button>
           </div>`
        : "";
      return `
        <article class="process-row ${failed ? "has-error" : ""}" data-process-id="${item.id}" ${isSession ? 'style="cursor:pointer"' : ""}>
          <div class="row-main">
            <div>
              <div class="row-title">${escapeHtml(item.label)}</div>
              <div class="row-meta">pid ${item.pid} · ${escapeHtml(item.status)} · ${uptimeStr}${item.mode ? ` · ${escapeHtml(item.mode)}` : ""}</div>
            </div>
            <div style="display:flex;gap:6px;align-items:center">
              ${isSession ? `<button class="button secondary expand-detail icon-only" data-detail-id="${item.id}" type="button" title="Detail"><i data-lucide="chevron-down"></i></button>` : ""}
              <button class="button ${running ? "danger" : "secondary"} stop-process" data-process-id="${item.id}" type="button" ${running ? "" : "disabled"}>
                ${stopLabel}
              </button>
            </div>
          </div>
          <div class="tagline">${statusTag}</div>
          ${errorBlock}
          ${wsBlock}
          <div class="session-detail" id="detail-${item.id}">
            <div class="session-meta-grid">
              <dt>${t("startTime")}</dt>
              <dd>${started.toLocaleString()}</dd>
              <dt>${t("uptime")}</dt>
              <dd>${uptimeStr}</dd>
              ${item.ws_endpoint ? `<dt>${t("wsEndpoint")}</dt><dd><code>${escapeHtml(item.ws_endpoint)}</code></dd>` : ""}
              ${item.error_message ? `<dt>${t("sessionError")}</dt><dd style="color:var(--danger)">${escapeHtml(item.error_message)}</dd>` : ""}
            </div>
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">
              <span style="font-size:13px;font-weight:650;color:var(--muted)">${t("logs")}</span>
              <button class="button secondary download-logs" data-log-id="${item.id}" type="button" style="min-height:28px;font-size:12px">
                <i data-lucide="download"></i> ${t("downloadLogs")}
              </button>
            </div>
            <pre class="log">${escapeHtml((item.logs || []).slice(-120).join("\n") || t("noLogs"))}</pre>
          </div>
        </article>
      `;
    })
    .join("");

  $$(".stop-process").forEach((button) => {
    button.addEventListener("click", async (e) => {
      e.stopPropagation();
      await api(`/api/processes/${button.dataset.processId}/stop`, { method: "POST", body: "{}" });
      toast(t("stopped"));
      await Promise.all([loadSessions(), loadTasks()]);
    });
  });
  $$(".expand-detail").forEach((button) => {
    button.addEventListener("click", (e) => {
      e.stopPropagation();
      const detail = $(`#detail-${button.dataset.detailId}`);
      if (detail) detail.classList.toggle("open");
    });
  });
  $$(".download-logs").forEach((button) => {
    button.addEventListener("click", async (e) => {
      e.stopPropagation();
      try {
        const response = await fetch(`/api/sessions/${button.dataset.logId}/logs/download`);
        const blob = await response.blob();
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = url;
        link.download = `session-${button.dataset.logId}.log`;
        document.body.appendChild(link);
        link.click();
        link.remove();
        URL.revokeObjectURL(url);
      } catch (err) {
        toast(err.message);
      }
    });
  });
  $$(".copy-ws").forEach((button) => {
    button.addEventListener("click", async (e) => {
      e.stopPropagation();
      try {
        await navigator.clipboard.writeText(button.dataset.ws || "");
        toast(t("copied"));
      } catch (_) {
        toast(button.dataset.ws || "");
      }
    });
  });
  renderIcons();
}

function updateSessionBadge(sessions) {
  const badge = $("#sessionBadge");
  if (!badge) return;
  const running = (sessions || []).filter((s) => s.status === "running").length;
  if (running > 0) {
    badge.textContent = String(running);
    badge.classList.remove("hidden");
  } else {
    badge.classList.add("hidden");
  }
}

async function loadSessions() {
  const sessions = await api("/api/sessions");
  state.sessions = sessions;
  updateSessionBadge(sessions);
  renderProcesses("#sessionList", sessions, t("stop"), true);
  // Keep profile running badges fresh without full reload
  if ($("#profileList") && state.viewMode !== "table") {
    renderProfiles();
  }
}

async function loadTasks() {
  const tasks = await api("/api/tasks");
  renderProcesses("#taskList", tasks, t("terminate"), false);
}

async function loadChannels() {
  try {
    state.channels = await api("/api/channels");
    renderChannels();
  } catch (_) {}
}

function renderChannels() {
  const selector = $("#channelSelector");
  const customRow = $("#channelCustomRow");
  if (!selector) return;
  selector.innerHTML = state.channels
    .map((ch) => `<button type="button" class="${ch.id === state.selectedChannel ? "active" : ""}" data-channel="${ch.id}">${t("channel" + ch.id.charAt(0).toUpperCase() + ch.id.slice(1)) || ch.name}</button>`)
    .join("");
  selector.querySelectorAll("button").forEach((btn) => {
    btn.addEventListener("click", () => {
      state.selectedChannel = btn.dataset.channel;
      renderChannels();
      if (customRow) customRow.style.display = btn.dataset.channel === "custom" ? "block" : "none";
    });
  });
}

async function channelFetch() {
  const channel = state.channels.find((ch) => ch.id === state.selectedChannel);
  if (!channel) return;
  if (channel.id === "custom") {
    const url = $("#customMirrorInput")?.value?.trim();
    if (!url) return toast("Please enter a mirror URL");
    await api("/api/channels", { method: "PUT", body: JSON.stringify({ id: "custom", prefix: url }) });
  }
  const result = await api(`/api/channels/${state.selectedChannel}/fetch`, { method: "POST", body: JSON.stringify({ args: [] }) });
  toast(`${t("taskStarted")}: ${result.label}`);
  await loadTasks();
}

async function testProxy() {
  const form = $("#profileForm");
  const data = new FormData(form);
  const server = data.get("proxy_server") || "";
  const username = data.get("proxy_username") || "";
  const password = data.get("proxy_password") || "";
  if (!server) {
    toast(t("proxyFailed"));
    return;
  }
  const resultEl = $("#proxyResult");
  const btn = $("#testProxyBtn");
  btn.disabled = true;
  resultEl.innerHTML = `<span class="proxy-result" style="background:var(--surface-strong);color:var(--muted)">${t("testing")}</span>`;
  try {
    const result = await api("/api/proxy/test", {
      method: "POST",
      body: JSON.stringify({ server, username, password }),
    });
    if (result.ok) {
      resultEl.innerHTML = `<span class="proxy-result ok">${t("proxyOk")} · ${t("exitIp")}: ${escapeHtml(result.exit_ip)} · ${t("latency")}: ${result.latency_ms}ms</span>`;
    } else {
      resultEl.innerHTML = `<span class="proxy-result fail">${t("proxyFailed")} · ${escapeHtml(result.error)}</span>`;
    }
  } catch (err) {
    resultEl.innerHTML = `<span class="proxy-result fail">${t("proxyFailed")} · ${escapeHtml(err.message)}</span>`;
  } finally {
    btn.disabled = false;
  }
}

async function batchStart() {
  const ids = [...state.selectedProfiles];
  if (ids.length < 2) return;
  try {
    const result = await api("/api/sessions/batch", {
      method: "POST",
      body: JSON.stringify({ profile_ids: ids }),
    });
    toast(`${t("batchStart")}: ${result.started} / ${ids.length}`);
    state.selectedProfiles.clear();
    updateBatchBar();
    renderProfiles();
    await loadSessions();
  } catch (err) {
    toast(err.message);
  }
}

// --- Random Fingerprint ---
async function randomFingerprint() {
  try {
    const result = await api("/api/fingerprint/generate?target_os=auto", { method: "POST", body: "{}" });
    const form = $("#profileForm");
    if (result.navigator_platform) form.elements.navigator_platform.value = result.navigator_platform;
    if (result.navigator_vendor) form.elements.navigator_vendor.value = result.navigator_vendor;
    if (result.screen_width) form.elements.screen_width.value = result.screen_width;
    if (result.screen_height) form.elements.screen_height.value = result.screen_height;
    if (result.screen_color_depth) form.elements.screen_color_depth.value = result.screen_color_depth;
    if (result.device_pixel_ratio) form.elements.device_pixel_ratio.value = result.device_pixel_ratio;
    if (result.webgl_vendor) form.elements.webgl_vendor.value = result.webgl_vendor;
    if (result.webgl_renderer) form.elements.webgl_renderer.value = result.webgl_renderer;
    if (result.timezone) form.elements.timezone.value = result.timezone;
    if (result.locale) {
      if (form.elements.fp_locale) form.elements.fp_locale.value = result.locale;
      if (form.elements.locale) form.elements.locale.value = result.locale;
    }
    if (result.webrtc_mode) form.elements.webrtc_mode.value = result.webrtc_mode;
    if (result.media_devices) form.elements.media_devices.value = result.media_devices;
    toast(t("fingerprintGenerated"));
  } catch (err) {
    toast(err.message);
  }
}

// --- Cookie Export/Import ---
async function exportCookies() {
  if (!state.selectedId) return;
  try {
    const result = await api(`/api/profiles/${state.selectedId}/cookies`);
    const blob = new Blob([JSON.stringify(result.cookies, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `cookies-${state.selectedId.slice(0, 8)}.json`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
    toast(`${t("exported")} ${result.count} ${t("cookies")}`);
  } catch (err) {
    toast(err.message);
  }
}

async function importCookies() {
  if (!state.selectedId) return;
  const input = document.createElement("input");
  input.type = "file";
  input.accept = ".json,.txt,.cookies";
  input.onchange = async () => {
    const file = input.files[0];
    if (!file) return;
    try {
      const text = await file.text();
      let body;
      const name = (file.name || "").toLowerCase();
      if (name.endsWith(".json") || text.trim().startsWith("[") || text.trim().startsWith("{")) {
        const data = JSON.parse(text);
        const cookies = Array.isArray(data) ? data : data.cookies || [];
        body = { cookies };
      } else {
        body = { text, format: "netscape" };
      }
      const result = await api(`/api/profiles/${state.selectedId}/cookies`, {
        method: "POST",
        body: JSON.stringify(body),
      });
      toast(`${t("imported")} ${result.count ?? 0} ${t("cookies")}`);
    } catch (err) {
      toast(err.message);
    }
  };
  input.click();
}

// --- Proxy Pool ---
async function loadProxies() {
  try {
    state.proxies = await api("/api/proxies");
  } catch (_) {
    state.proxies = [];
  }
  fillProxySelect($("#proxyPoolSelect")?.value || "");
  renderProxyPool();
}

function renderProxyPool() {
  const list = $("#proxyPoolList");
  if (!list) return;
  if (!state.proxies.length) {
    list.innerHTML = `<div class="empty">${t("noProxies")}</div>`;
    return;
  }
  list.innerHTML = state.proxies
    .map((p) => {
      const testTag =
        p.last_ok === true
          ? `<span class="tag running">${t("proxyOk")}${p.last_exit_ip ? ` · ${escapeHtml(p.last_exit_ip)}` : ""}</span>`
          : p.last_ok === false
            ? `<span class="tag failed">${t("proxyFailed")}</span>`
            : `<span class="tag">${t("neverTested")}</span>`;
      return `
        <article class="process-row" data-proxy-id="${escapeHtml(p.id)}">
          <div class="row-main">
            <div>
              <div class="row-title">${escapeHtml(p.name || p.server || p.id)}</div>
              <div class="row-meta">${escapeHtml(p.server || "")}${p.username ? ` · ${escapeHtml(p.username)}` : ""}</div>
            </div>
            <div style="display:flex;gap:6px;align-items:center">
              <button class="button secondary proxy-test" data-proxy-id="${escapeHtml(p.id)}" type="button">${t("testProxy")}</button>
              <button class="button secondary proxy-assign" data-proxy-id="${escapeHtml(p.id)}" type="button">${t("assignProxy")}</button>
              <button class="button danger proxy-delete icon-only" data-proxy-id="${escapeHtml(p.id)}" type="button" title="Delete"><i data-lucide="trash-2"></i></button>
            </div>
          </div>
          <div class="tagline">${testTag}</div>
        </article>
      `;
    })
    .join("");

  $$(".proxy-test").forEach((btn) => {
    btn.addEventListener("click", async () => {
      btn.disabled = true;
      try {
        const result = await api(`/api/proxies/${btn.dataset.proxyId}/test`, { method: "POST", body: "{}" });
        toast(result.ok ? `${t("proxyOk")} ${result.exit_ip || ""}` : `${t("proxyFailed")}: ${result.error || ""}`);
        await loadProxies();
      } catch (err) {
        toast(err.message);
      } finally {
        btn.disabled = false;
      }
    });
  });
  $$(".proxy-delete").forEach((btn) => {
    btn.addEventListener("click", async () => {
      if (!confirm(t("delete") + "?")) return;
      await api(`/api/proxies/${btn.dataset.proxyId}`, { method: "DELETE" });
      toast(t("proxyDeleted"));
      await loadProxies();
    });
  });
  $$(".proxy-assign").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const ids = [...state.selectedProfiles];
      if (!ids.length && state.selectedId) ids.push(state.selectedId);
      if (!ids.length) {
        toast(t("choose"));
        return;
      }
      await api("/api/proxies/assign", {
        method: "POST",
        body: JSON.stringify({ profile_ids: ids, proxy_id: btn.dataset.proxyId }),
      });
      toast(t("profileSaved"));
      await loadProfiles();
    });
  });
  renderIcons();
}

async function addProxyFromForm() {
  const name = $("#proxyNameInput")?.value?.trim() || "";
  const server = $("#proxyServerInput")?.value?.trim() || "";
  const username = $("#proxyUserInput")?.value?.trim() || "";
  const password = $("#proxyPassInput")?.value || "";
  if (!server) {
    toast(t("proxyFailed"));
    return;
  }
  await api("/api/proxies", {
    method: "POST",
    body: JSON.stringify({ name, server, username, password }),
  });
  $("#proxyNameInput").value = "";
  $("#proxyServerInput").value = "";
  $("#proxyUserInput").value = "";
  $("#proxyPassInput").value = "";
  toast(t("proxyCreated"));
  await loadProxies();
}

async function importProxyPool() {
  const textarea = $("#proxyPoolImportInput");
  if (!textarea) return;
  const lines = textarea.value.split("\n").map((l) => l.trim()).filter(Boolean);
  if (!lines.length) return;
  const result = await api("/api/proxies/import", {
    method: "POST",
    body: JSON.stringify({ lines, replace: false }),
  });
  textarea.value = "";
  toast(`${t("proxyImported")}: ${result.count}`);
  await loadProxies();
}

// --- Templates ---
async function loadTemplates() {
  try {
    state.templates = await api("/api/templates");
  } catch (_) {
    state.templates = [];
  }
  renderTemplates();
}

function renderTemplates() {
  const bar = $("#templateBar");
  if (!bar) return;
  if (!state.templates.length) {
    bar.innerHTML = "";
    bar.style.display = "none";
    return;
  }
  bar.style.display = "flex";
  bar.innerHTML = state.templates
    .map((tpl) => {
      const name = typeof tpl.name === "object" ? tpl.name[state.lang] || tpl.name.en || tpl.id : tpl.name;
      const desc = typeof tpl.description === "object" ? tpl.description[state.lang] || tpl.description.en || "" : tpl.description || "";
      return `<button type="button" class="template-chip" data-template-id="${escapeHtml(tpl.id)}" title="${escapeHtml(desc)}">${escapeHtml(name)}</button>`;
    })
    .join("");
  bar.querySelectorAll("[data-template-id]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      try {
        const created = await api(`/api/templates/${btn.dataset.templateId}/create`, { method: "POST", body: "{}" });
        toast(t("templateCreated"));
        await loadProfiles();
        loadProfile(created);
      } catch (err) {
        toast(err.message);
      }
    });
  });
}

// --- Guided first-run setup (auto install environment) ---
function setupStepLabel(id) {
  const map = {
    check: t("setupStepCheck"),
    package: t("setupStepPackage"),
    fetch: t("setupStepFetch"),
    verify: t("setupStepVerify"),
  };
  return map[id] || id;
}

function setupStatusLabel(status, currentStep) {
  if (status === "done") return t("setupDone");
  if (status === "failed") return t("setupFailed");
  if (currentStep === "package") return t("setupInstalling");
  if (currentStep === "fetch") return t("setupDownloading");
  if (currentStep === "verify") return t("setupVerifying");
  return t("setupPreparing");
}

function renderSetupWizard() {
  const overlay = $("#setupOverlay");
  if (!overlay) return;
  const setup = state.setup || {};
  const steps = setup.steps || [];
  const progress = Number(setup.progress || 0);
  const fill = $("#setupProgressFill");
  const pct = $("#setupProgressPct");
  const statusText = $("#setupStatusText");
  const stepsEl = $("#setupSteps");
  const logEl = $("#setupLog");
  const retryBtn = $("#setupRetryBtn");
  const continueBtn = $("#setupContinueBtn");

  if (fill) fill.style.width = `${Math.max(0, Math.min(100, progress))}%`;
  if (pct) pct.textContent = `${Math.max(0, Math.min(100, progress))}%`;
  if (statusText) statusText.textContent = setupStatusLabel(setup.status, setup.current_step);

  if (stepsEl) {
    const statusLabel = (st) => {
      if (st === "done") return t("stepDone");
      if (st === "skipped") return t("stepSkipped");
      if (st === "failed") return t("stepFailed");
      if (st === "running") return t("stepRunning");
      return t("stepPending");
    };
    stepsEl.innerHTML = steps
      .map((step) => {
        const st = step.status || "pending";
        const icon =
          st === "done" || st === "skipped"
            ? "✓"
            : st === "failed"
              ? "!"
              : st === "running"
                ? "…"
                : "·";
        return `<li class="${escapeHtml(st)}">
          <span class="step-icon">${icon}</span>
          <span>${escapeHtml(setupStepLabel(step.id) || step.label || step.id)}</span>
          <span class="step-status" data-status="${escapeHtml(st)}">${escapeHtml(statusLabel(st))}</span>
          ${step.detail ? `<div class="step-detail">${escapeHtml(step.detail)}</div>` : ""}
        </li>`;
      })
      .join("");
  }

  if (logEl) {
    const logs = setup.logs || [];
    logEl.textContent = logs.slice(-80).join("\n") || "…";
    logEl.scrollTop = logEl.scrollHeight;
  }

  $$("[data-setup-channel]").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.setupChannel === state.setupChannel);
    btn.disabled = setup.status === "running";
  });

  if (retryBtn) retryBtn.disabled = setup.status === "running";
  if (continueBtn) {
    const ready = setup.status === "done" || (state.system && state.system.camoufox_installed && !state.system.needs_setup);
    continueBtn.disabled = !ready;
  }

  if (state.setupBlocking) overlay.classList.remove("hidden");
  else overlay.classList.add("hidden");
  renderIcons();
}

function showSetupWizard(blocking = true) {
  state.setupBlocking = blocking;
  renderSetupWizard();
}

function hideSetupWizard() {
  state.setupBlocking = false;
  stopSetupPolling();
  $("#setupOverlay")?.classList.add("hidden");
}

function stopSetupPolling() {
  if (state.setupPollTimer) {
    window.clearInterval(state.setupPollTimer);
    state.setupPollTimer = null;
  }
}

async function pollSetupStatus() {
  try {
    state.setup = await api("/api/setup/status");
    renderSetupWizard();
    if (state.setup.status === "done") {
      stopSetupPolling();
      await loadSystem();
      // Auto-enter app after short delay so user sees success state
      window.setTimeout(() => {
        if (state.setup?.status === "done") hideSetupWizard();
      }, 700);
    } else if (state.setup.status === "failed") {
      stopSetupPolling();
    }
  } catch (_) {
    // keep polling; transient errors during long fetch are possible
  }
}

async function startGuidedSetup({ force = false } = {}) {
  showSetupWizard(true);
  try {
    state.setup = await api("/api/setup/start", {
      method: "POST",
      body: JSON.stringify({
        channel: state.setupChannel || "github",
        auto: true,
        force,
      }),
    });
    state.setupAutoStarted = true;
    renderSetupWizard();
    stopSetupPolling();
    state.setupPollTimer = window.setInterval(pollSetupStatus, 1200);
    await pollSetupStatus();
  } catch (err) {
    toast(err.message);
    state.setup = {
      status: "failed",
      error: err.message,
      steps: [],
      logs: [err.message],
      progress: 0,
    };
    renderSetupWizard();
  }
}

async function maybeAutoSetup() {
  const sys = state.system;
  if (!sys) return;
  const needs = Boolean(sys.needs_setup || sys.first_run || !sys.camoufox_installed);
  const setup = sys.setup || state.setup || {};
  if (setup.status === "running") {
    state.setup = setup;
    showSetupWizard(true);
    if (!state.setupPollTimer) {
      state.setupPollTimer = window.setInterval(pollSetupStatus, 1200);
    }
    return;
  }
  if (needs) {
    // Force guided setup — do not allow silent dismiss on first install
    if (!state.setupAutoStarted || setup.status === "failed" || setup.status === "idle") {
      await startGuidedSetup({ force: setup.status === "failed" });
    } else {
      state.setup = setup;
      showSetupWizard(true);
    }
    return;
  }
  // Ready: only show wizard if user opened it manually
  if (!state.setupBlocking) {
    hideSetupWizard();
  }
}

function updateFirstRunBanner() {
  // Legacy banner removed — guided overlay handles first-run.
  maybeAutoSetup().catch(() => {});
}

async function runHealthCheck() {
  const el = $("#healthResult");
  try {
    if (el) el.textContent = t("checking") + "...";
    const result = await api("/api/system/health", { method: "POST", body: "{}" });
    const ok = Boolean(result.ok);
    const detail = result.error
      || (result.checks ? `path=${result.checks.path_value || "?"} · ${result.checks.version || ""}` : "")
      || result.detail
      || "";
    if (el) {
      el.innerHTML = ok
        ? `<span style="color:var(--success)">${t("healthOk")}</span> · ${escapeHtml(detail)}`
        : `<span style="color:var(--danger)">${t("healthFail")}</span> · ${escapeHtml(detail || JSON.stringify(result.checks || result))}`;
    }
    toast(ok ? t("healthOk") : t("healthFail"));
    await loadSystem();
  } catch (err) {
    if (el) el.innerHTML = `<span style="color:var(--danger)">${escapeHtml(err.message)}</span>`;
    toast(err.message);
  }
}

async function runCleanupRuntime() {
  try {
    const result = await api("/api/system/cleanup-runtime", { method: "POST", body: "{}" });
    toast(`${t("runtimeCleaned")}: ${result.removed ?? 0}`);
  } catch (err) {
    toast(err.message);
  }
}

function updateStatusLabel(info) {
  const status = info?.status || "idle";
  const map = {
    idle: t("updateIdle"),
    checking: t("updateChecking"),
    available: t("updateAvailable"),
    downloading: t("updateDownloading"),
    ready: t("updateReady"),
    installing: t("updateInstalling"),
    up_to_date: t("updateUpToDate"),
    failed: t("updateFailed"),
  };
  return map[status] || status;
}

function applyUpdateInfo(info) {
  if (!info) return;
  state.updateInfo = info;
  const releaseUrl = info.release_url || "https://github.com/BB0813/foxdesk/releases";
  const banner = $("#updateBanner");
  const text = $("#updateBannerText");
  const link = $("#updateBannerLink");
  const showBanner =
    info.update_available &&
    info.latest &&
    info.latest !== state.updateDismissedTag &&
    !["up_to_date", "checking"].includes(info.status);

  if (text && info.latest) text.textContent = `${info.current || ""} → ${info.latest}`;
  if (link) link.href = releaseUrl;
  if (banner) banner.classList.toggle("hidden", !showBanner);

  const openBtn = $("#updateOpenReleaseBtn");
  if (openBtn) openBtn.href = releaseUrl;

  $("#updateCurrentVer") && ($("#updateCurrentVer").textContent = info.current || "—");
  $("#updateLatestVer") && ($("#updateLatestVer").textContent = info.latest || "—");
  $("#updateStatusText") && ($("#updateStatusText").textContent = updateStatusLabel(info));
  const pct = Math.max(0, Math.min(100, Number(info.progress) || 0));
  $("#updateProgressPct") && ($("#updateProgressPct").textContent = `${pct}%`);
  const fill = $("#updateProgressFill");
  if (fill) fill.style.width = `${pct}%`;

  const logEl = $("#updateLog");
  if (logEl && Array.isArray(info.logs)) {
    logEl.textContent = info.logs.slice(-40).join("\n");
    logEl.scrollTop = logEl.scrollHeight;
  }

  const busy = ["checking", "downloading", "installing"].includes(info.status);
  const nowBtn = $("#updateNowBtn");
  if (nowBtn) {
    nowBtn.disabled = busy;
    if (info.status === "ready") nowBtn.textContent = t("updateReady");
    else if (info.status === "downloading") nowBtn.textContent = t("updateDownloading");
    else if (info.status === "installing") nowBtn.textContent = t("updateInstalling");
    else if (!info.can_one_click && info.update_available) nowBtn.textContent = t("openRelease");
    else nowBtn.textContent = t("oneClickUpdate");
  }
  if (info.error && state.updateModalOpen) {
    // keep error visible in log already
  }
  renderIcons();
}

function showUpdateModal(force = false) {
  const overlay = $("#updateOverlay");
  if (!overlay) return;
  const info = state.updateInfo;
  if (!force && info?.latest && info.latest === state.updateDismissedTag) return;
  state.updateModalOpen = true;
  overlay.classList.remove("hidden");
  applyUpdateInfo(info || {});
  renderIcons();
}

function hideUpdateModal() {
  state.updateModalOpen = false;
  $("#updateOverlay")?.classList.add("hidden");
  stopUpdatePoll();
}

function stopUpdatePoll() {
  if (state.updatePollTimer) {
    window.clearInterval(state.updatePollTimer);
    state.updatePollTimer = null;
  }
}

function startUpdatePoll() {
  stopUpdatePoll();
  state.updatePollTimer = window.setInterval(async () => {
    try {
      const info = await api("/api/system/updates/status");
      applyUpdateInfo(info);
      if (["ready", "failed", "up_to_date", "available", "idle"].includes(info.status)) {
        if (info.status === "ready") {
          // leave poll briefly then stop; user may click install or auto-install
          stopUpdatePoll();
        } else if (info.status !== "available") {
          stopUpdatePoll();
        }
      }
    } catch (_) {
      /* ignore transient poll errors */
    }
  }, 900);
}

async function checkForUpdates(silent = false) {
  try {
    const result = await api("/api/system/updates/check", {
      method: "POST",
      body: JSON.stringify({}),
    });
    applyUpdateInfo(result);
    state.lastAutoUpdateCheck = Date.now();

    if (result.update_available && result.latest && result.latest !== state.updateDismissedTag) {
      if (!silent) {
        showUpdateModal(true);
        toast(`${t("updateAvailable")}: ${result.latest}`);
      } else if (!state.setupBlocking && !state.updateModalOpen) {
        // Auto-popup once per newer tag when not dismissed and setup done
        showUpdateModal(false);
      }
    } else {
      if (!silent) {
        if (result.status === "failed") toast(result.error || t("updateFailed"));
        else toast(t("updateUpToDate"));
      }
      if (!result.update_available) {
        $("#updateBanner")?.classList.add("hidden");
      }
    }
    return result;
  } catch (err) {
    if (!silent) toast(err.message);
    return null;
  }
}

async function startOneClickUpdate() {
  try {
    showUpdateModal(true);
    let info = state.updateInfo;
    if (!info?.update_available && !info?.asset_url) {
      info = await checkForUpdates(true);
    }
    if (!info?.update_available) {
      toast(t("updateUpToDate"));
      return;
    }
    if (!info.can_one_click && info.release_url) {
      window.open(info.release_url, "_blank", "noopener,noreferrer");
      toast(t("openRelease"));
      return;
    }
    const dl = await api("/api/system/updates/download", { method: "POST", body: "{}" });
    applyUpdateInfo(dl);
    startUpdatePoll();
    toast(t("updateStarted"));

    // Wait until ready then install
    const waitReady = async () => {
      for (let i = 0; i < 600; i++) {
        const st = await api("/api/system/updates/status");
        applyUpdateInfo(st);
        if (st.status === "ready") return st;
        if (st.status === "failed") throw new Error(st.error || t("updateFailed"));
        await new Promise((r) => setTimeout(r, 800));
      }
      throw new Error(t("updateFailed"));
    };
    const ready = await waitReady();
    stopUpdatePoll();
    const installed = await api("/api/system/updates/install", {
      method: "POST",
      body: JSON.stringify({ exit_after: true }),
    });
    applyUpdateInfo(installed);
    toast(t("updateInstalling"));
  } catch (err) {
    stopUpdatePoll();
    toast(err.message || t("updateFailed"));
    try {
      const st = await api("/api/system/updates/status");
      applyUpdateInfo(st);
    } catch (_) {}
  }
}

function onProxyPoolSelectChange() {
  const select = $("#proxyPoolSelect");
  if (!select) return;
  const proxy = state.proxies.find((p) => p.id === select.value);
  const form = $("#profileForm");
  if (!form) return;
  if (proxy) {
    form.elements.proxy_server.value = proxy.server || "";
    form.elements.proxy_username.value = proxy.username || "";
    form.elements.proxy_password.value = proxy.password || "";
  }
  markFormDirty();
}

// --- Context Menu ---
let contextProfileId = null;

function showContextMenu(e, profileId) {
  e.preventDefault();
  contextProfileId = profileId;
  const menu = $("#contextMenu");
  menu.style.display = "block";
  menu.style.left = `${Math.min(e.clientX, window.innerWidth - 200)}px`;
  menu.style.top = `${Math.min(e.clientY, window.innerHeight - 250)}px`;
  renderIcons();
}

function hideContextMenu() {
  const menu = $("#contextMenu");
  if (menu) menu.style.display = "none";
  contextProfileId = null;
}

async function handleContextAction(action) {
  if (!contextProfileId) return;
  hideContextMenu();
  const profile = state.profiles.find((p) => p.id === contextProfileId);
  if (!profile) return;
  switch (action) {
    case "launch":
      try {
        await api("/api/sessions", { method: "POST", body: JSON.stringify({ profile_id: contextProfileId }) });
        toast(`${t("launched")} ${profile.name}`);
        await loadSessions();
      } catch (err) { toast(err.message); }
      break;
    case "edit":
      loadProfile(profile);
      break;
    case "clone":
      try {
        const cloned = await api(`/api/profiles/${contextProfileId}/clone`, { method: "POST", body: "{}" });
        await loadProfiles();
        loadProfile(cloned);
        toast(t("profileCloned"));
      } catch (err) { toast(err.message); }
      break;
    case "export":
      try {
        const data = await api("/api/profiles/export");
        const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = url;
        link.download = `foxdesk-profiles-${new Date().toISOString().slice(0, 10)}.json`;
        document.body.appendChild(link);
        link.click();
        link.remove();
        URL.revokeObjectURL(url);
        toast(t("exportDone"));
      } catch (err) { toast(err.message); }
      break;
    case "open-dir":
      try {
        await api(`/api/profiles/${contextProfileId}/open-data-dir`, { method: "POST", body: "{}" });
        toast(t("openDirDone"));
      } catch (err) { toast(err.message); }
      break;
    case "delete":
      if (confirm(`${t("delete")} "${profile.name}"?`)) {
        try {
          await api(`/api/profiles/${contextProfileId}`, { method: "DELETE" });
          if (state.selectedId === contextProfileId) state.selectedId = null;
          await loadProfiles();
          if (state.profiles[0]) loadProfile(state.profiles[0]);
          else loadProfile(null);
          toast(t("profileDeleted"));
        } catch (err) { toast(err.message); }
      }
      break;
  }
}

// --- Activity Log ---
async function loadActivity() {
  try {
    const entries = await api("/api/activity?limit=50");
    const el = $("#activityList");
    if (!el) return;
    if (!entries.length) {
      el.innerHTML = `<div class="empty">${t("noActivity")}</div>`;
      return;
    }
    el.innerHTML = entries.reverse().map((e) =>
      `<div style="padding:6px 16px;border-top:1px solid var(--border);font-size:12px;display:flex;gap:10px">
        <span style="color:var(--subtle);white-space:nowrap">${new Date(e.time).toLocaleString()}</span>
        <span style="font-weight:600;color:var(--primary)">${escapeHtml(e.action)}</span>
        <span style="color:var(--muted)">${escapeHtml(e.detail)}</span>
      </div>`
    ).join("");
  } catch (_) {}
}

// --- Table View Toggle ---
state.viewMode = localStorage.getItem("cm-view") || "card";

function toggleView() {
  state.viewMode = state.viewMode === "card" ? "table" : "card";
  localStorage.setItem("cm-view", state.viewMode);
  const btn = $("#viewToggleBtn");
  if (btn) {
    const icon = btn.querySelector("i");
    if (icon) icon.setAttribute("data-lucide", state.viewMode === "card" ? "list" : "layout-grid");
  }
  renderProfiles();
  renderIcons();
}

function renderProfileTable(profiles) {
  const list = $("#profileList");
  if (!list) return;
  if (!profiles.length) {
    list.innerHTML = `<div class="empty">${t("noProfiles")}</div>`;
    updateBatchBar();
    return;
  }
  let html = `<table class="profile-table"><thead><tr>
    <th style="width:30px"></th>
    <th>${t("name")}</th>
    <th>${t("targetOs")}</th>
    <th>${t("proxyServer")}</th>
    <th>${t("tags")}</th>
    <th style="width:40px"></th>
  </tr></thead><tbody>`;
  profiles.forEach((p) => {
    const proxy = p.proxy?.server || "—";
    const proxyShort = proxy.length > 24 ? proxy.slice(0, 24) + "…" : proxy;
    const tags = (p.tags || []).join(", ") || "—";
    html += `<tr data-profile-id="${p.id}" class="${p.id === state.selectedId ? "selected" : ""}">
      <td><input type="checkbox" class="batch-check" data-batch-id="${p.id}" ${state.selectedProfiles.has(p.id) ? "checked" : ""} /></td>
      <td title="${escapeHtml(p.name)}"><strong>${escapeHtml(p.name)}</strong><br><span style="color:var(--subtle);font-size:11px">${escapeHtml(p.startup_url || "")}</span></td>
      <td>${escapeHtml(p.os)}</td>
      <td title="${escapeHtml(proxy)}" style="color:${p.proxy?.server ? "var(--primary)" : "var(--subtle)"}">${escapeHtml(proxyShort)}</td>
      <td>${escapeHtml(tags)}</td>
      <td><button class="button secondary icon-only delete-profile" data-delete-id="${p.id}" style="width:28px;min-height:28px" title="${t("delete")}"><i data-lucide="trash-2"></i></button></td>
    </tr>`;
  });
  html += "</tbody></table>";
  list.innerHTML = html;

  list.querySelectorAll("tr[data-profile-id]").forEach((row) => {
    row.addEventListener("click", (e) => {
      if (e.target.closest(".delete-profile") || e.target.closest(".batch-check")) return;
      const profile = state.profiles.find((item) => item.id === row.dataset.profileId);
      loadProfile(profile);
    });
    row.addEventListener("contextmenu", (e) => {
      e.preventDefault();
      showContextMenu(e, row.dataset.profileId);
    });
  });
  list.querySelectorAll(".delete-profile").forEach((btn) => {
    btn.addEventListener("click", (e) => { e.stopPropagation(); deleteProfile(btn.dataset.deleteId); });
  });
  list.querySelectorAll(".batch-check").forEach((cb) => {
    cb.addEventListener("change", () => {
      if (cb.checked) state.selectedProfiles.add(cb.dataset.batchId);
      else state.selectedProfiles.delete(cb.dataset.batchId);
      updateBatchBar();
    });
  });
  renderIcons();
  updateBatchBar();
}

// --- Fingerprint Check ---
async function checkFingerprint() {
  if (!state.selectedId) return;
  const el = $("#fpCheckResult");
  try {
    el.innerHTML = `<span style="color:var(--muted);font-size:13px">${t("checking")}...</span>`;
    el.classList.add("open");
    const result = await api(`/api/profiles/${state.selectedId}/fingerprint-check`);
    const scoreColor = result.score >= 80 ? "var(--success)" : result.score >= 50 ? "var(--warning)" : "var(--danger)";
    el.innerHTML = `
      <div style="display:flex;align-items:center;gap:12px;margin-bottom:10px">
        <div class="fp-score">
          <div class="fp-score-bar"><div class="fp-score-fill" style="width:${result.score}%;background:${scoreColor}"></div></div>
          <span style="color:${scoreColor}">${result.score}/100</span>
        </div>
        <span style="font-size:12px;color:var(--muted)">${result.issues.length === 0 ? "✓ " + t("allChecksPassed") : `${result.issues.length} ${t("issues")}`}</span>
        <a href="${result.check_url}" target="_blank" style="margin-left:auto;font-size:12px">${t("openInBrowser")} →</a>
      </div>
      ${result.issues.length ? `<ul class="fp-issues">${result.issues.map((i) => `<li>${escapeHtml(i)}</li>`).join("")}</ul>` : ""}
      <dl class="fp-checks-grid">
        <dt>${t("navigatorPlatform")}</dt><dd>${escapeHtml(result.checks.platform)}</dd>
        <dt>${t("navigatorVendor")}</dt><dd>${escapeHtml(result.checks.vendor)}</dd>
        <dt>${t("screenWidth")}×${t("screenHeight")}</dt><dd>${escapeHtml(result.checks.screen)}</dd>
        <dt>WebGL</dt><dd>${escapeHtml(result.checks.webgl)}</dd>
        <dt>Canvas</dt><dd>${result.checks.canvas_noise ? t("canvasNoise") + " ✓" : "—"}</dd>
        <dt>Audio</dt><dd>${result.checks.audio_noise ? t("audioNoise") + " ✓" : "—"}</dd>
        <dt>WebRTC</dt><dd>${escapeHtml(result.checks.webrtc_mode)}</dd>
        <dt>${t("timezone")}</dt><dd>${escapeHtml(result.checks.timezone)}</dd>
        <dt>${t("locale")}</dt><dd>${escapeHtml(result.checks.locale)}</dd>
      </dl>`;
  } catch (err) {
    el.innerHTML = `<span style="color:var(--danger);font-size:13px">${escapeHtml(err.message)}</span>`;
  }
}

// --- Bulk Proxy Import ---
async function bulkProxyImport() {
  const textarea = $("#bulkProxyInput");
  const resultEl = $("#bulkProxyResult");
  if (!textarea) return;
  const lines = textarea.value.split("\n").map((l) => l.trim()).filter(Boolean);
  if (!lines.length) return;
  try {
    const result = await api("/api/profiles/bulk-proxy", {
      method: "POST",
      body: JSON.stringify({ proxies: lines, profile_ids: [] }),
    });
    resultEl.textContent = `✓ ${result.updated} updated`;
    textarea.value = "";
    await loadProfiles();
  } catch (err) {
    resultEl.textContent = `✗ ${err.message}`;
  }
}

// --- Stop All Sessions ---
async function stopAllSessions() {
  try {
    const result = await api("/api/sessions/stop-all", { method: "POST", body: "{}" });
    toast(`${t("stopped")}: ${result.stopped}`);
    await loadSessions();
  } catch (err) {
    toast(err.message);
  }
}

async function refreshAll() {
  await Promise.all([
    loadSystem(),
    loadProxies(),
    loadTemplates(),
    loadProfiles(),
    loadSessions(),
    loadTasks(),
    loadChannels(),
  ]);
  await maybeAutoSetup();
  // Skip update popup while first-run setup is blocking the UI
  if (!state.setupBlocking) {
    checkForUpdates(true).catch(() => {});
  }
  renderIcons();
}

function renderIcons() {
  if (window.lucide) {
    window.lucide.createIcons();
  }
  // Re-apply translations to any dynamically rendered content
  $$("[data-i18n]").forEach((el) => {
    const key = el.dataset.i18n;
    if (key) el.textContent = t(key);
  });
  // Translate select options
  $$("[data-i18n-option]").forEach((el) => {
    const key = el.dataset.i18nOption;
    if (key) el.textContent = t(key);
  });
}

function switchPage(page) {
  $$(".tab-nav button").forEach((b) => b.classList.remove("active"));
  $$(".tab-page").forEach((p) => p.classList.remove("active"));
  const btn = $(`.tab-nav button[data-page="${page}"]`);
  const target = $(`.tab-page[data-page="${page}"]`);
  if (btn) btn.classList.add("active");
  if (target) target.classList.add("active");
  if (page === "sessions") loadSessions();
  if (page === "proxies") loadProxies();
  if (page === "system") {
    loadSystem();
    loadTasks();
    loadChannels();
    loadActivity();
  }
  renderIcons();
}

function bindEvents() {
  $("#refreshBtn").addEventListener("click", refreshAll);
  $("#refreshSessionsBtn").addEventListener("click", loadSessions);
  $("#newProfileBtn").addEventListener("click", () => loadProfile(null));
  $("#themeToggle").addEventListener("click", toggleTheme);
  $("#testProxyBtn").addEventListener("click", testProxy);
  $("#channelFetchBtn").addEventListener("click", channelFetch);
  $("#batchStartBtn").addEventListener("click", batchStart);
  $("#randomFpBtn")?.addEventListener("click", randomFingerprint);
  $("#exportCookiesBtn")?.addEventListener("click", exportCookies);
  $("#importCookiesBtn")?.addEventListener("click", importCookies);
  $("#viewToggleBtn")?.addEventListener("click", toggleView);
  $("#checkFpBtn")?.addEventListener("click", checkFingerprint);
  $("#bulkProxyBtn")?.addEventListener("click", bulkProxyImport);
  $("#stopAllBtn")?.addEventListener("click", stopAllSessions);
  $("#proxyAddBtn")?.addEventListener("click", () => addProxyFromForm().catch((e) => toast(e.message)));
  $("#proxyImportBtn")?.addEventListener("click", () => importProxyPool().catch((e) => toast(e.message)));
  $("#templateBtn")?.addEventListener("click", () => {
    const bar = $("#templateBar");
    if (!bar) return;
    bar.classList.toggle("open");
    if (!state.templates.length) loadTemplates();
    else renderTemplates();
  });
  $("#healthCheckBtn")?.addEventListener("click", runHealthCheck);
  $("#cleanupRuntimeBtn")?.addEventListener("click", runCleanupRuntime);
  $("#checkUpdateBtn")?.addEventListener("click", () => checkForUpdates(false));
  $("#setupRetryBtn")?.addEventListener("click", () => startGuidedSetup({ force: true }));
  $("#setupContinueBtn")?.addEventListener("click", async () => {
    try {
      await api("/api/setup/complete", { method: "POST", body: "{}" });
    } catch (_) {}
    hideSetupWizard();
    await loadSystem();
    toast(t("setupDone"));
    checkForUpdates(true).catch(() => {});
  });
  $$("[data-setup-channel]").forEach((btn) => {
    btn.addEventListener("click", () => {
      if (state.setup?.status === "running") return;
      state.setupChannel = btn.dataset.setupChannel || "github";
      localStorage.setItem("cm-setup-channel", state.setupChannel);
      renderSetupWizard();
    });
  });
  $("#updateDismissBtn")?.addEventListener("click", () => {
    const tag = state.updateInfo?.latest || $("#updateBannerText")?.textContent?.split("→").pop()?.trim() || "";
    state.updateDismissedTag = tag;
    localStorage.setItem("cm-update-dismissed", tag);
    $("#updateBanner")?.classList.add("hidden");
    hideUpdateModal();
  });
  $("#updateBannerUpdateBtn")?.addEventListener("click", () => startOneClickUpdate());
  $("#updateNowBtn")?.addEventListener("click", () => startOneClickUpdate());
  $("#updateLaterBtn")?.addEventListener("click", () => {
    const tag = state.updateInfo?.latest || "";
    if (tag) {
      state.updateDismissedTag = tag;
      localStorage.setItem("cm-update-dismissed", tag);
    }
    hideUpdateModal();
  });
  $("#updateModalCloseBtn")?.addEventListener("click", () => hideUpdateModal());
  $("#proxyPoolSelect")?.addEventListener("change", onProxyPoolSelectChange);

  // Context menu
  document.addEventListener("click", hideContextMenu);
  $$(".ctx-item").forEach((item) => {
    item.addEventListener("click", () => handleContextAction(item.dataset.action));
  });
  $("#saveBtn").addEventListener("click", async () => {
    try {
      await saveProfile();
    } catch (error) {
      toast(error.message);
    }
  });
  $("#launchBtn").addEventListener("click", async () => {
    try {
      await launchSelected();
    } catch (error) {
      toast(error.message);
    }
  });
  $("#cloneBtn").addEventListener("click", async () => {
    try {
      await cloneSelected();
    } catch (error) {
      toast(error.message);
    }
  });
  $("#openDirBtn").addEventListener("click", async () => {
    try {
      await openSelectedDir();
    } catch (error) {
      toast(error.message);
    }
  });
  $("#exportBtn").addEventListener("click", async () => {
    try {
      await exportProfiles();
    } catch (error) {
      toast(error.message);
    }
  });
  $("#importBtn").addEventListener("click", () => $("#importFile").click());
  $("#importFile").addEventListener("change", async (event) => {
    const [file] = event.target.files;
    if (!file) return;
    try {
      await importProfiles(file);
    } catch (error) {
      toast(error.message);
    } finally {
      event.target.value = "";
    }
  });
  $$("[data-task]").forEach((button) => {
    button.addEventListener("click", async () => {
      try {
        await startTask(button.dataset.task);
      } catch (error) {
        toast(error.message);
      }
    });
  });
  $$("[data-lang]").forEach((button) => {
    button.addEventListener("click", () => setLanguage(button.dataset.lang));
  });
  // Page tab switching
  $$(".tab-nav button[data-page]").forEach((btn) => {
    btn.addEventListener("click", () => switchPage(btn.dataset.page));
  });
  // Tab switching
  $$(".tab-bar button").forEach((btn) => {
    btn.addEventListener("click", () => {
      $$(".tab-bar button").forEach((b) => b.classList.remove("active"));
      $$(".tab-content").forEach((tc) => tc.classList.remove("active"));
      btn.classList.add("active");
      const content = $(`.tab-content[data-tab-content="${btn.dataset.tab}"]`);
      if (content) content.classList.add("active");
    });
  });
  // Profile search
  const searchEl = $("#profileSearch");
  if (searchEl) {
    let debounce;
    searchEl.addEventListener("input", () => {
      clearTimeout(debounce);
      debounce = setTimeout(() => renderProfiles(), 150);
    });
  }
  // Keep locale fields mirrored across Basic / Fingerprint tabs
  const form = $("#profileForm");
  if (form) {
    form.addEventListener("input", markFormDirty);
    form.addEventListener("change", markFormDirty);
    if (form.elements.locale && form.elements.fp_locale) {
      form.elements.locale.addEventListener("input", () => {
        form.elements.fp_locale.value = form.elements.locale.value;
      });
      form.elements.fp_locale.addEventListener("input", () => {
        form.elements.locale.value = form.elements.fp_locale.value;
      });
    }
  }
  // Keyboard shortcuts
  document.addEventListener("keydown", (e) => {
    if (e.target.tagName === "INPUT" || e.target.tagName === "TEXTAREA" || e.target.tagName === "SELECT") return;
    const ctrl = e.ctrlKey || e.metaKey;
    if (ctrl && e.key === "1") { e.preventDefault(); switchPage("profiles"); }
    if (ctrl && e.key === "2") { e.preventDefault(); switchPage("sessions"); }
    if (ctrl && e.key === "3") { e.preventDefault(); switchPage("proxies"); }
    if (ctrl && e.key === "4") { e.preventDefault(); switchPage("system"); }
    if (ctrl && e.key === "n") { e.preventDefault(); loadProfile(null); }
    if (ctrl && e.key === "s") { e.preventDefault(); saveProfile().catch((err) => toast(err.message)); }
  });
  window.addEventListener("beforeunload", (e) => {
    if (!state.formDirty) return;
    e.preventDefault();
    e.returnValue = "";
  });
}

bindEvents();
applyTheme(state.theme);
setLanguage(state.lang);
refreshAll().catch((error) => toast(error.message));
window.setInterval(() => {
  Promise.all([loadSessions(), loadTasks()]).catch(() => {});
}, 4000);
