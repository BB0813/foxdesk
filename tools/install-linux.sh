#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════
#  FoxDesk Linux 一键安装脚本
#
#  一键执行：
#    curl -fsSL https://raw.githubusercontent.com/BB0813/foxdesk/main/tools/install-linux.sh | sudo bash
#
#  或先下载再执行：
#    wget https://raw.githubusercontent.com/BB0813/foxdesk/main/tools/install-linux.sh
#    sudo bash install-linux.sh [选项]
#
#  选项：
#    --version X.Y.Z   安装指定版本（默认取 GitHub 最新 release）
#    --dir <path>      安装目录（默认 /opt/FoxDesk）
#    --mirror          使用 ghproxy 镜像下载（国内网络推荐）
#    --no-symlink      不创建 /usr/local/bin/foxdesk 软链接
#    --no-desktop      不创建桌面快捷方式
#    --uninstall       卸载
# ═══════════════════════════════════════════════════════════════
set -euo pipefail

GITHUB_REPO="BB0813/foxdesk"
INSTALL_DIR="/opt/FoxDesk"
SYMLINK=1
DESKTOP_ENTRY=1
USE_MIRROR=0
VERSION=""

gh_api() {
    # GitHub API（自动跟随重定向；带超时）
    curl -fsSL --connect-timeout 10 --max-time 30 \
        -H "Accept: application/vnd.github+json" \
        "https://api.github.com/repos/${GITHUB_REPO}$1" 2>/dev/null
}

dl() {
    # dl <url> <output>：直连优先，失败自动切 ghproxy 镜像
    local url="$1" out="$2"
    if [ "$USE_MIRROR" -eq 1 ] && curl -fsSL --connect-timeout 10 --max-time 600 -o "$out" \
        "https://mirror.ghproxy.com/${url}" 2>/dev/null; then
        return 0
    fi
    curl -fsSL --connect-timeout 10 --max-time 600 -o "$out" "$url"
}

msg() { printf '\n\033[1;36m[FoxDesk]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[警告]\033[0m %s\n' "$*"; }
fail() { printf '\033[1;31m[失败]\033[0m %s\n' "$*"; exit 1; }

# ── 参数解析 ──
while [ $# -gt 0 ]; do
    case "$1" in
        --version)  VERSION="${2:-}"; shift 2 ;;
        --dir)      INSTALL_DIR="${2:-}"; shift 2 ;;
        --mirror)   USE_MIRROR=1; shift ;;
        --no-symlink) SYMLINK=0; shift ;;
        --no-desktop) DESKTOP_ENTRY=0; shift ;;
        --uninstall) ACTION="uninstall"; shift ;;
        -h|--help)
            sed -n '2,20p' "$0"; exit 0 ;;
        *) warn "未知参数: $1"; shift ;;
    esac
done

# ── 卸载 ──
if [ "${ACTION:-}" = "uninstall" ]; then
    msg "卸载 FoxDesk..."
    rm -rf "$INSTALL_DIR"
    rm -f /usr/local/bin/foxdesk
    rm -f /usr/share/applications/foxdesk.desktop
    msg "已卸载。用户数据保留在 ~/.config/FoxDesk（如需删除请手动）"
    exit 0
fi

# ── 前置检查 ──
command -v curl >/dev/null 2>&1 || command -v wget >/dev/null 2>&1 || fail "需要 curl 或 wget"
if [ "$INSTALL_DIR" = "/opt/FoxDesk" ] && [ "$(id -u)" -ne 0 ]; then
    warn "/opt/FoxDesk 需要 root 权限——使用 sudo 重新运行，或改用 --dir \$HOME/FoxDesk"
    INSTALL_DIR="$HOME/FoxDesk"
    msg "改用安装目录: $INSTALL_DIR"
fi

# ── 版本探测 ──
if [ -z "$VERSION" ]; then
    msg "探测最新版本..."
    VERSION=$(gh_api "/releases/latest" | grep -o '"tag_name": *"[^"]*"' | head -1 | cut -d'"' -f4 | sed 's/^v//') || true
    if [ -z "$VERSION" ]; then
        # API 失败（国内常见）→ 走 ghproxy 读 latest 重定向
        VERSION=$(curl -fsSL -o /dev/null -w '%{url_effective}' \
            "https://mirror.ghproxy.com/https://github.com/${GITHUB_REPO}/releases/latest" \
            2>/dev/null | sed 's#.*/tag/##') || true
    fi
    [ -z "$VERSION" ] && fail "无法探测最新版本——请用 --version X.Y.Z 手动指定"
fi
msg "版本: v${VERSION}"

BASE_URL="https://github.com/${GITHUB_REPO}/releases/download/v${VERSION}"
TARBALL="FoxDesk-linux-x64-${VERSION}.tar.gz"
SUMS="SHA256SUMS-linux"

# ── 下载 ──
TMP_DIR=$(mktemp -d)
trap 'rm -rf "$TMP_DIR"' EXIT
msg "下载 ${TARBALL}..."
dl "${BASE_URL}/${TARBALL}" "${TMP_DIR}/${TARBALL}" || fail "下载失败（可加 --mirror 参数走镜像）"
[ -s "${TMP_DIR}/${TARBALL}" ] || fail "下载的文件为空"

msg "下载校验文件..."
dl "${BASE_URL}/${SUMS}" "${TMP_DIR}/${SUMS}" || warn "校验文件下载失败——跳过 SHA256 验证"

# ── SHA256 校验 ──
if [ -s "${TMP_DIR}/${SUMS}" ]; then
    EXPECTED=$(grep "${TARBALL}" "${TMP_DIR}/${SUMS}" | awk '{print $1}')
    ACTUAL=$(sha256sum "${TMP_DIR}/${TARBALL}" | awk '{print $1}')
    if [ -n "$EXPECTED" ] && [ "$EXPECTED" != "$ACTUAL" ]; then
        fail "SHA256 不匹配！期望 ${EXPECTED}，实际 ${ACTUAL}"
    fi
    msg "SHA256 校验通过"
fi

# ── 安装 ──
msg "安装到 ${INSTALL_DIR}..."
mkdir -p "$INSTALL_DIR"
tar -xzf "${TMP_DIR}/${TARBALL}" -C "$INSTALL_DIR" --strip-components=0
chmod +x "${INSTALL_DIR}/FoxDesk/FoxDesk"

# ── 软链接 ──
if [ "$SYMLINK" -eq 1 ] && [ -w /usr/local/bin ] || [ "$SYMLINK" -eq 1 ] && [ "$(id -u)" -eq 0 ]; then
    ln -sf "${INSTALL_DIR}/FoxDesk/FoxDesk" /usr/local/bin/foxdesk
    msg "已创建命令: foxdesk（终端直接运行）"
elif [ "$SYMLINK" -eq 1 ]; then
    warn "无 /usr/local/bin 写权限——跳过软链接（可用 sudo 手动创建）"
fi

# ── 桌面快捷方式 ──
if [ "$DESKTOP_ENTRY" -eq 1 ]; then
    DESKTOP_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
    mkdir -p "$DESKTOP_DIR"
    cat > "${DESKTOP_DIR}/foxdesk.desktop" <<DESKTOP
[Desktop Entry]
Name=FoxDesk
Comment=Local fingerprint browser manager
Exec=${INSTALL_DIR}/FoxDesk/FoxDesk
Icon=${INSTALL_DIR}/FoxDesk/_internal/static/logo.png
Type=Application
Categories=Network;Utility;
DESKTOP
    msg "已创建桌面快捷方式"
fi

# ── 依赖检查 ──
GUI_DEPS_MISSING=0
for lib in libwebkit2gtk; do
    ldconfig -p 2>/dev/null | grep -q "$lib" || { GUI_DEPS_MISSING=1; break; }
done
if [ "$GUI_DEPS_MISSING" -eq 1 ]; then
    warn "缺少 GUI 运行库（图形界面需要）——可用 --serve 模式 + 浏览器替代："
    warn "  Debian/Ubuntu: sudo apt install libwebkit2gtk-4.1-0 gir1.2-gtk-3.0"
    warn "  启动服务:      ${INSTALL_DIR}/FoxDesk/FoxDesk --serve 8765"
fi

# ── 完成 ──
msg "════════════════════════════════════════"
msg "安装完成！"
msg "  启动:        foxdesk 或 ${INSTALL_DIR}/FoxDesk/FoxDesk"
msg "  无图形模式:  ${INSTALL_DIR}/FoxDesk/FoxDesk --serve 8765"
msg "  数据目录:    ~/.config/FoxDesk"
msg "  卸载:        curl -fsSL <本脚本URL> | sudo bash -s -- --uninstall"
msg "════════════════════════════════════════"
