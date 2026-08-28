from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class ProxyConfig(BaseModel):
    server: str = ""
    username: str = ""
    password: str = ""

    @field_validator("server")
    @classmethod
    def normalize_server(cls, value: str) -> str:
        value = value.strip()
        if not value:
            return ""
        if "://" not in value:
            value = f"http://{value}"
        allowed = ("http://", "https://", "socks4://", "socks5://")
        if not value.lower().startswith(allowed):
            raise ValueError("proxy server must use http://, https://, socks4://, or socks5://")
        return value


class ProfileIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    startup_url: str = "https://browserleaks.com/javascript"
    mode: Literal["browser", "server"] = "browser"
    # Phase A dual-engine: camoufox (Firefox) | chromium (Playwright Chromium stack)
    engine: Literal["camoufox", "chromium"] = "camoufox"
    # Phase C: chromium automation backend — playwright | patchright | auto
    # auto = prefer patchright when installed, else playwright
    chromium_backend: Literal["auto", "playwright", "patchright"] = "auto"
    # Optional Playwright channel for chromium engine: chrome | msedge | "" (bundled chromium)
    chromium_channel: str = ""
    # Phase B: normal = soft risks only; strict = high risks block launch
    consistency_policy: Literal["normal", "strict"] = "normal"
    os: Literal["auto", "windows", "macos", "linux"] = "auto"
    headless: bool = False
    persistent_context: bool = True
    user_data_dir: str = ""
    humanize: bool = True
    geoip: bool = False
    locale: str = ""
    proxy: ProxyConfig = Field(default_factory=ProxyConfig)
    proxy_id: str = ""
    block_images: bool = False
    block_webrtc: bool = True
    block_webgl: bool = False
    disable_coop: bool = True
    enable_cache: bool = True
    addons: list[str] = Field(default_factory=list)
    extra_args: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    notes: str = ""
    # Fingerprint parameters
    user_agent: str = ""
    navigator_platform: str = ""
    navigator_vendor: str = ""
    screen_width: int = 0
    screen_height: int = 0
    screen_color_depth: int = 0
    device_pixel_ratio: float = 0.0
    hardware_concurrency: int = 0
    device_memory: float = 0.0
    max_touch_points: int = -1  # -1 = leave default; 0+ override
    canvas_noise: bool = True
    webgl_vendor: str = ""
    webgl_renderer: str = ""
    audio_noise: bool = True
    fonts: list[str] = Field(default_factory=list)
    # Phase B: empty/none = no pack; auto = OS pack; windows|macos|linux = fixed pack
    font_pack: str = ""
    timezone: str = ""
    # Client Hints (Chromium; best-effort via init script / context)
    ua_ch_platform: str = ""
    ua_ch_mobile: bool = False
    webrtc_mode: Literal["default", "disable", "public_only", "force_proxy"] = "default"
    media_devices: Literal["default", "random", "empty"] = "default"
    keyboard_layout: str = ""

    @field_validator("startup_url")
    @classmethod
    def validate_startup_url(cls, value: str) -> str:
        value = value.strip()
        if value and not value.startswith(("http://", "https://", "about:")):
            raise ValueError("startup_url must start with http://, https://, or about:")
        return value

    @field_validator("engine", mode="before")
    @classmethod
    def normalize_engine(cls, value: Any) -> str:
        raw = (str(value) if value is not None else "camoufox").strip().lower()
        if raw in {"", "firefox", "camoufox", "default"}:
            return "camoufox"
        if raw in {"chromium", "chrome", "pw", "playwright"}:
            return "chromium"
        raise ValueError("engine must be camoufox or chromium")

    @field_validator("chromium_backend", mode="before")
    @classmethod
    def normalize_chromium_backend(cls, value: Any) -> str:
        raw = (str(value) if value is not None else "auto").strip().lower()
        if raw in {"", "auto", "default"}:
            return "auto"
        if raw in {"playwright", "pw"}:
            return "playwright"
        if raw in {"patchright", "pr", "patched"}:
            return "patchright"
        raise ValueError("chromium_backend must be auto, playwright, or patchright")

    @field_validator("chromium_channel", mode="before")
    @classmethod
    def normalize_chromium_channel(cls, value: Any) -> str:
        raw = (str(value) if value is not None else "").strip().lower()
        if raw in {"", "chromium", "default"}:
            return ""
        if raw in {"chrome", "msedge", "chrome-beta", "msedge-beta", "msedge-dev"}:
            return raw
        raise ValueError("chromium_channel must be empty, chrome, or msedge")

    @field_validator("consistency_policy", mode="before")
    @classmethod
    def normalize_consistency_policy(cls, value: Any) -> str:
        raw = (str(value) if value is not None else "normal").strip().lower()
        if raw in {"", "normal", "default", "soft"}:
            return "normal"
        if raw in {"strict", "hard", "block"}:
            return "strict"
        raise ValueError("consistency_policy must be normal or strict")

    @field_validator("user_agent", mode="before")
    @classmethod
    def normalize_user_agent(cls, value: Any) -> str:
        return (str(value) if value is not None else "").strip()

    @field_validator("font_pack", mode="before")
    @classmethod
    def normalize_font_pack(cls, value: Any) -> str:
        raw = (str(value) if value is not None else "").strip().lower()
        if raw in {"", "none", "off", "manual", "custom"}:
            return ""
        if raw in {"auto", "os", "default_pack"}:
            return "auto"
        if raw in {"windows", "macos", "linux"}:
            return raw
        raise ValueError("font_pack must be empty, auto, windows, macos, or linux")

    @field_validator("addons", "extra_args", "fonts")
    @classmethod
    def normalize_list(cls, value: list[str]) -> list[str]:
        return [item.strip() for item in value if item and str(item).strip()]


class Profile(ProfileIn):
    id: str
    created_at: str
    updated_at: str


class LaunchRequest(BaseModel):
    profile_id: str


class TaskRequest(BaseModel):
    args: list[str] = Field(default_factory=list)


class ImportProfilesRequest(BaseModel):
    profiles: list[dict[str, Any]]
    replace: bool = False


class ProxyTestRequest(BaseModel):
    server: str
    username: str = ""
    password: str = ""


class ChannelUpdateRequest(BaseModel):
    id: str
    prefix: str = ""


class BatchLaunchRequest(BaseModel):
    profile_ids: list[str]


class BatchStopRequest(BaseModel):
    process_ids: list[str]


class SetupStartRequest(BaseModel):
    channel: str = "github"
    auto: bool = True
    force: bool = False


class SettingsUpdateRequest(BaseModel):
    update_mirror: str | None = None
    github_token: str | None = None
    clear_github_token: bool = False
    max_concurrent_sessions: int | None = None
    idle_session_minutes: int | None = None
    proxy_auto_check: bool | None = None
    proxy_check_interval_sec: int | None = None
    proxy_assign_mode: str | None = None


class UpdateCheckRequest(BaseModel):
    include_prerelease: bool | None = None
    force: bool = False


class UpdateInstallRequest(BaseModel):
    exit_after: bool = True


class ProxyPoolIn(BaseModel):
    name: str = "Proxy"
    server: str
    username: str = ""
    password: str = ""
    tags: list[str] = Field(default_factory=list)
    notes: str = ""


class ProxyPoolImportRequest(BaseModel):
    lines: list[str]
    replace: bool = False


class ProxyAssignRequest(BaseModel):
    profile_ids: list[str]
    proxy_id: str = ""


class BulkProxyRequest(BaseModel):
    proxies: list[str]
    profile_ids: list[str] = Field(default_factory=list)


class ApplySuggestionRequest(BaseModel):
    code: str


class NavigateRequest(BaseModel):
    url: str


class EvaluateRequest(BaseModel):
    expression: str = Field(min_length=1, max_length=1500)


class ScreenshotRequest(BaseModel):
    full_page: bool = False


class BackupRequest(BaseModel):
    password: str = Field(min_length=4, max_length=128)
    include_profiles_dirs: bool = False


class BackupRestoreRequest(BaseModel):
    password: str = Field(min_length=4, max_length=128)
    path: str = Field(min_length=1, max_length=1024)
    # When true, write restored files over current data_dir (after pre-restore snapshot).
    overwrite: bool = True
    # Restore only listed names; empty = all safe names in archive.
    include: list[str] = Field(default_factory=list)
