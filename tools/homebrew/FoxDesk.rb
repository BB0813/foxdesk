# Homebrew Cask for FoxDesk macOS builds.
#
# 用法：
#   1. 创建仓库 BB0813/homebrew-foxdesk（GitHub 上新建）
#   2. 把本文件复制为 Casks/foxdesk.rb（改名小写）
#   3. 更新 version/sha256 后用户即可：
#        brew tap BB0813/foxdesk
#        brew install --cask foxdesk
#      brew 安装的应用不带 quarantine 标记，可直接打开（无需绕 Gatekeeper）。
#
# 每次发版后更新 version 与 sha256（取 release 资产 SHA256SUMS-macos）。
cask "foxdesk" do
  version "1.6.0"
  sha256 "d36dccc21c1fe38ba03d4c957e4d9e861f383ed47ffadbdb71c28a4541976ca2"

  url "https://github.com/BB0813/foxdesk/releases/download/v#{version}/FoxDesk-macos-#{version}.zip"
  name "FoxDesk"
  desc "Local fingerprint browser manager (Camoufox + Chromium)"
  homepage "https://github.com/BB0813/foxdesk"

  # 打包结构：zip 内含 FoxDesk/FoxDesk.app（旧构建）或 FoxDesk.app（新构建）
  # 两种都适配：appcast 自动装到 /Applications
  app "FoxDesk.app"
  app "FoxDesk/FoxDesk.app"

  caveats <<~EOS
    Experimental macOS build (unsigned). If installed via brew there is no
    quarantine flag; if downloaded manually, right-click -> Open or run:
      xattr -cr /Applications/FoxDesk.app
    No anti-detect/payment/signup guarantees are provided.
  EOS
end
