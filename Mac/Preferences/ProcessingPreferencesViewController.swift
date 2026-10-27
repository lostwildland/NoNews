import AppKit

final class ProcessingPreferencesViewController: NSViewController {
	private let statusLabel = NSTextField(labelWithString: "")
	private let actionButton = NSButton(title: "", target: nil, action: nil)

	override func loadView() {
		view = NSView(frame: NSRect(x: 0, y: 0, width: 512, height: 150))
		let heading = NSTextField(labelWithString: NSLocalizedString("Processing", comment: "Preferences"))
		heading.font = .boldSystemFont(ofSize: NSFont.systemFontSize)
		statusLabel.lineBreakMode = .byWordWrapping
		statusLabel.maximumNumberOfLines = 3
		actionButton.target = self
		actionButton.action = #selector(changeState(_:))
		for control in [heading, statusLabel, actionButton] {
			control.translatesAutoresizingMaskIntoConstraints = false
			view.addSubview(control)
		}
		NSLayoutConstraint.activate([
			heading.leadingAnchor.constraint(equalTo: view.leadingAnchor, constant: 24),
			heading.topAnchor.constraint(equalTo: view.topAnchor, constant: 24),
			statusLabel.leadingAnchor.constraint(equalTo: heading.leadingAnchor),
			statusLabel.trailingAnchor.constraint(lessThanOrEqualTo: view.trailingAnchor, constant: -24),
			statusLabel.topAnchor.constraint(equalTo: heading.bottomAnchor, constant: 12),
			actionButton.leadingAnchor.constraint(equalTo: heading.leadingAnchor),
			actionButton.topAnchor.constraint(equalTo: statusLabel.bottomAnchor, constant: 12)
		])
		NotificationCenter.default.addObserver(self, selector: #selector(updateStatus), name: ProcessingEngine.didChange, object: ProcessingEngine.shared)
		updateStatus()
	}

	@objc private func updateStatus() {
		switch ProcessingEngine.shared.state {
		case .stopped:
			statusLabel.stringValue = NSLocalizedString("Stopped", comment: "Processing status")
			actionButton.title = NSLocalizedString("Start", comment: "Processing action")
			actionButton.isEnabled = true
		case .starting:
			statusLabel.stringValue = NSLocalizedString("Starting…", comment: "Processing status")
			actionButton.title = NSLocalizedString("Stop", comment: "Processing action")
			actionButton.isEnabled = true
		case .ready:
			statusLabel.stringValue = NSLocalizedString("Ready", comment: "Processing status")
			actionButton.title = NSLocalizedString("Stop", comment: "Processing action")
			actionButton.isEnabled = true
		case .stopping:
			statusLabel.stringValue = NSLocalizedString("Stopping…", comment: "Processing status")
			actionButton.title = NSLocalizedString("Stop", comment: "Processing action")
			actionButton.isEnabled = false
		case .failed(let message):
			statusLabel.stringValue = message
			actionButton.title = NSLocalizedString("Retry", comment: "Processing action")
			actionButton.isEnabled = true
		}
	}

	@objc private func changeState(_ sender: Any?) {
		switch ProcessingEngine.shared.state {
		case .starting, .ready: ProcessingEngine.shared.stop()
		case .stopped, .failed: ProcessingEngine.shared.start()
		case .stopping: break
		}
	}
}
