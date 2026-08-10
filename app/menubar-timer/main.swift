import AppKit
import Foundation

final class App: NSObject, NSApplicationDelegate {
    private let statusItem = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)
    private var pollTimer: Timer?
    private var state: [String: Any] = [:]

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
            }
        }
        task.resume()
    }

    private func updateTitle() {
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
