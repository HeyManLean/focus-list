import AppKit
import Foundation

final class App: NSObject, NSApplicationDelegate {
    private let statusItem = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)
    private var pollTimer: Timer?
    private var state: [String: Any] = [:]
    private var alertedEndAt: Double = 0
    private var flashTimer: Timer?
    private var flashUntil: TimeInterval = 0
    private var flashOn = false

    func applicationDidFinishLaunching(_ notification: Notification) {
        statusItem.button?.title = "🍅 25:00"
        buildMenu()
        refresh()
        pollTimer = Timer.scheduledTimer(withTimeInterval: 1.0, repeats: true) { [weak self] _ in
            self?.refresh()
        }
    }

    private func buildMenu() {
        let menu = NSMenu()
        let open = NSMenuItem(title: "打开专注清单", action: #selector(openApp), keyEquivalent: "o")
        open.target = self
        menu.addItem(open)
        menu.addItem(.separator())
        let quit = NSMenuItem(title: "退出", action: #selector(quitApp), keyEquivalent: "q")
        quit.target = self
        menu.addItem(quit)
        statusItem.menu = menu
    }

    @objc private func openApp() {
        if let url = URL(string: "http://127.0.0.1:8765") {
            NSWorkspace.shared.open(url)
        }
    }

    @objc private func quitApp() {
        NSApp.terminate(nil)
    }

    private func refresh() {
        guard let url = URL(string: "http://127.0.0.1:8765/api/timer") else { return }
        let task = URLSession.shared.dataTask(with: url) { [weak self] data, _, _ in
            guard let self = self, let data = data,
                  let obj = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else {
                DispatchQueue.main.async {
                    self?.statusItem.button?.title = "—"
                }
                return
            }
            DispatchQueue.main.async {
                self.state = obj
                self.updateTitle()
                self.checkCompletion()
            }
        }
        task.resume()
    }

    private func checkCompletion() {
        let status = state["status"] as? String ?? "idle"
        let endAt = state["endAt"] as? Double ?? 0
        if status == "running" {
            stopFlash()
        }
        guard status == "running", endAt > 0 else { return }
        let now = Date().timeIntervalSince1970 * 1000
        guard endAt <= now, endAt != alertedEndAt else { return }
        alertedEndAt = endAt
        let mode = state["mode"] as? String ?? "work"
        startFlash()
        showCompletionAlert(mode: mode)
    }

    private func startFlash() {
        flashUntil = Date().timeIntervalSince1970 + 180
        flashOn = false
        flashTimer?.invalidate()
        flashTimer = Timer.scheduledTimer(withTimeInterval: 0.6, repeats: true) { [weak self] _ in
            self?.flashTick()
        }
    }

    private func stopFlash() {
        flashTimer?.invalidate()
        flashTimer = nil
        flashOn = false
    }

    private func flashTick() {
        if Date().timeIntervalSince1970 > flashUntil {
            stopFlash()
            updateTitle()
            return
        }
        flashOn.toggle()
        statusItem.button?.title = flashOn ? "⏰ 时间到！" : "🍅 00:00"
    }

    private func showCompletionAlert(mode: String) {
        let isWork = mode == "work"
        let title = isWork ? "🍅 专注完成！" : "休息结束"
        let message = isWork ? "完成一个番茄钟，站起来休息一下吧" : "休息结束，准备好开始下一个番茄了吗？"
        DispatchQueue.main.async {
            NSApp.activate(ignoringOtherApps: true)
            NSSound.beep()
            let alert = NSAlert()
            alert.messageText = title
            alert.informativeText = message
            alert.alertStyle = .informational
            alert.window.level = .floating
            alert.addButton(withTitle: "知道了")
            alert.runModal()
        }
    }

    private func updateTitle() {
        if flashTimer != nil {
            return
        }
        let mode = state["mode"] as? String ?? "work"
        let status = state["status"] as? String ?? "idle"
        let endAt = state["endAt"] as? Double ?? 0
        let remaining = state["remaining"] as? Double ?? 1500
        var secs = remaining
        if status == "running" && endAt > 0 {
            secs = (endAt - Date().timeIntervalSince1970 * 1000) / 1000
        }
        secs = max(0, secs)
        let total = Int(ceil(secs))
        let time = String(format: "%02d:%02d", total / 60, total % 60)
        let icon: String
        switch mode {
        case "work": icon = "🍅"
        case "short": icon = "🍵"
        case "long": icon = "🌙"
        default: icon = "🍅"
        }
        let prefix = status == "paused" ? "⏸ " : ""
        statusItem.button?.title = "\(icon) \(prefix)\(time)"
        statusItem.button?.toolTip = statusText(status, mode, time)
    }

    private func statusText(_ status: String, _ mode: String, _ time: String) -> String {
        let modeName: String
        switch mode {
        case "work": modeName = "专注"
        case "short": modeName = "短休息"
        case "long": modeName = "长休息"
        default: modeName = "专注"
        }
        switch status {
        case "running": return "\(modeName)中 · 剩余 \(time)"
        case "paused": return "\(modeName)已暂停 · 剩余 \(time)"
        default: return "待机 · 当前\(modeName)时长 \(time)"
        }
    }
}

let app = NSApplication.shared
let delegate = App()
app.delegate = delegate
app.setActivationPolicy(.accessory)
app.run()
