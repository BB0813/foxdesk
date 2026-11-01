# macOS 签名与公证路线（未实施——需要 Apple Developer 账号）

## 现状
v1.6.0 起 macOS 构建为 ad-hoc 签名（PyInstaller 自动），zip 下载后带
quarantine 标记，用户需绕过 Gatekeeper（右键打开 / xattr / brew）。

## 正式路线（需仓库所有者操作）
1. 加入 Apple Developer Program（$99/年）
2. Xcode 或钥匙串创建 **Developer ID Application** 证书
3. GitHub 仓库 secrets：
   - `MACOS_CERT_P12`（base64 的 .p12）
   - `MACOS_CERT_PASSWORD`
   - `APPLE_ID` / `APPLE_APP_SPECIFIC_PASSWORD` / `APPLE_TEAM_ID`（公证用）
4. CI macos job 中构建后加入：

```bash
# 导入证书
echo "$MACOS_CERT_P12" | base64 --decode > cert.p12
security create-keychain -p ci build.keychain
security import cert.p12 -k build.keychain -P "$MACOS_CERT_PASSWORD" -T /usr/bin/codesign
security set-key-partition-list -S apple-tool:,apple: -s -k ci build.keychain
security default-keychain -s build.keychain

# 签名（deep）
codesign --force --deep --options runtime --sign "Developer ID Application: <NAME> (<TEAMID>)" dist/FoxDesk/FoxDesk.app

# 公证 + 装订
xcrun notarytool submit FoxDesk-macos.zip --apple-id "$APPLE_ID" --team-id "$APPLE_TEAM_ID" --password "$APPLE_APP_SPECIFIC_PASSWORD" --wait
xcrun stapler staple dist/FoxDesk/FoxDesk.app
```

5. 之后用户下载即可双击打开（Gatekeeper 显示已公证的开发者）。

## 备选：brew cask（已就绪）
`tools/homebrew/FoxDesk.rb` 模板已生成；发版后更新 version/sha256 并放入
`BB0813/homebrew-foxdesk` 仓库即可让用户 `brew install --cask foxdesk`
（brew 安装无 quarantine，直接打开）。
