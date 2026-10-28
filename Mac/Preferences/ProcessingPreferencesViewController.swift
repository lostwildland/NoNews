import AppKit
import Secrets

final class ProcessingPreferencesViewController: NSViewController, NSTextFieldDelegate {
	private let statusLabel = NSTextField(labelWithString: "")
	private let actionButton = NSButton(title: "", target: nil, action: nil)
	private let services = NSPopUpButton()
	private let serviceName = NSTextField()
	private let serviceType = NSPopUpButton()
	private let endpoint = NSTextField()
	private let credential = NSSecureTextField()
	private let prompts = NSPopUpButton()
	private let promptName = NSTextField()
	private let role = NSPopUpButton()
	private let binding = NSPopUpButton()
	private let target = NSPopUpButton()
	private let instructions = NSTextView()
	private let titleLanguage = NSPopUpButton()
	private let typography = NSPopUpButton()
	private let confirmLegacyOutput = NSButton(checkboxWithTitle: "I reviewed the imported output preferences", target: nil, action: nil)
	private let history = NSPopUpButton()
	private let usedBy = NSTextField(wrappingLabelWithString: "Used by: none")
	private let feedback = NSTextField(wrappingLabelWithString: "")
	private let configurationTabs = NSTabView()
	private var serviceRows: [[String: Any]] = []
	private var promptRows: [[String: Any]] = []
	private var currentService: [String: Any]?
	private var currentPrompt: [String: Any]?
	private var selectedBinding: [String: Any]?
	private var versions: [[String: Any]] = []
	private let legacyBinding = NSPopUpButton()
	private let legacyTarget = NSPopUpButton()
	private let legacyJob = NSPopUpButton()
	private let editorGateway = NSPopUpButton()
	private let migrationStatus = NSTextField(wrappingLabelWithString: "Review legacy routing only when migrating existing settings.")
	private var legacyRows: [[String: Any]] = []
	private var legacyJobs: [[String: Any]] = []
	private var editorGatewayRows: [[String: Any]] = []
	private var migrationChoices: [String: String] = [:]
	private var editorServices: [String: String] = [:]
	private var migrationReview = MigrationReviewState()
	private var migrationWaiting = false
	private var editorReviewToken: String?

	override func loadView() {
		view = NSView(frame: NSRect(x: 0, y: 0, width: 640, height: 620))
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
		let tabs = configurationTabs
		tabs.translatesAutoresizingMaskIntoConstraints = false
		view.addSubview(tabs)
		let serviceTab = NSTabViewItem(identifier: "services")
		serviceTab.label = "Services"
		serviceTab.view = serviceForm()
		tabs.addTabViewItem(serviceTab)
		let promptTab = NSTabViewItem(identifier: "prompts")
		promptTab.label = "Prompts"
		promptTab.view = promptForm()
		tabs.addTabViewItem(promptTab)
		feedback.translatesAutoresizingMaskIntoConstraints = false
		view.addSubview(feedback)
		NSLayoutConstraint.activate([
			heading.leadingAnchor.constraint(equalTo: view.leadingAnchor, constant: 24),
			heading.topAnchor.constraint(equalTo: view.topAnchor, constant: 24),
			statusLabel.leadingAnchor.constraint(equalTo: heading.leadingAnchor),
			statusLabel.trailingAnchor.constraint(lessThanOrEqualTo: view.trailingAnchor, constant: -24),
			statusLabel.topAnchor.constraint(equalTo: heading.bottomAnchor, constant: 12),
			actionButton.leadingAnchor.constraint(equalTo: heading.leadingAnchor),
			actionButton.topAnchor.constraint(equalTo: statusLabel.bottomAnchor, constant: 12),
			tabs.leadingAnchor.constraint(equalTo: view.leadingAnchor, constant: 20),
			tabs.trailingAnchor.constraint(equalTo: view.trailingAnchor, constant: -20),
			tabs.topAnchor.constraint(equalTo: actionButton.bottomAnchor, constant: 12),
			tabs.bottomAnchor.constraint(equalTo: feedback.topAnchor, constant: -8),
			feedback.leadingAnchor.constraint(equalTo: tabs.leadingAnchor),
			feedback.trailingAnchor.constraint(equalTo: tabs.trailingAnchor),
			feedback.bottomAnchor.constraint(equalTo: view.bottomAnchor, constant: -16)
		])
		NotificationCenter.default.addObserver(self, selector: #selector(updateStatus), name: ProcessingEngine.didChange, object: ProcessingEngine.shared)
		updateStatus()
	}

	private func button(_ title: String, _ action: Selector) -> NSButton {
		NSButton(title: title, target: self, action: action)
	}

	private func row(_ label: String, _ control: NSView) -> NSStackView {
		let title = NSTextField(labelWithString: label)
		title.setContentHuggingPriority(.required, for: .horizontal)
		let result = NSStackView(views: [title, control])
		result.orientation = .horizontal
		result.spacing = 8
		return result
	}

	private func form(_ controls: [NSView]) -> NSView {
		let stack = NSStackView(views: controls)
		stack.orientation = .vertical
		stack.alignment = .leading
		stack.spacing = 10
		stack.translatesAutoresizingMaskIntoConstraints = false
		let scroll = NSScrollView()
		scroll.hasVerticalScroller = true
		scroll.documentView = stack
		NSLayoutConstraint.activate([stack.leadingAnchor.constraint(equalTo: scroll.contentView.leadingAnchor, constant: 12),
			stack.trailingAnchor.constraint(equalTo: scroll.contentView.trailingAnchor, constant: -12),
			stack.topAnchor.constraint(equalTo: scroll.contentView.topAnchor, constant: 12),
			stack.widthAnchor.constraint(equalTo: scroll.contentView.widthAnchor, constant: -24)])
		return scroll
	}

	private func serviceForm() -> NSView {
		services.target = self
		services.action = #selector(selectService)
		serviceType.addItems(withTitles: ["Magpie", "OpenAI-compatible"])
		serviceType.target = self
		serviceType.action = #selector(migrationInputChanged)
		for field in [serviceName, endpoint, credential] { field.delegate = self }
		for popup in [legacyBinding, legacyTarget, legacyJob, editorGateway] {
			popup.target = self
			popup.action = #selector(migrationInputChanged)
		}
		credential.placeholderString = "Stored in Keychain"
		let actions = NSStackView(views: [button("New", #selector(newService)), button("Save", #selector(saveService)), button("Refresh Models or Targets", #selector(refreshService)), button("Delete", #selector(deleteService))])
		let mapping = NSStackView(views: [legacyBinding, legacyTarget, button("Choose Mapping", #selector(chooseMapping))])
		let editorMapping = NSStackView(views: [legacyJob, editorGateway, button("Confirm Editor Gateway", #selector(chooseEditorGateway))])
		let migration = NSStackView(views: [button("Preview Routing", #selector(previewMigration)), button("Pause Claims", #selector(pauseMigration)), button("Apply Mappings", #selector(applyMigration))])
		return form([NSTextField(wrappingLabelWithString: "Reading works without AI. Refresh checks the directory only."),
			row("Service", services), row("Name", serviceName), row("Type", serviceType), row("Endpoint", endpoint),
			row("Bearer credential", credential), actions, NSTextField(labelWithString: "Advanced: Legacy Magpie Routing"),
			migrationStatus, mapping, editorMapping, migration])
	}

	private func promptForm() -> NSView {
		prompts.target = self
		prompts.action = #selector(selectPrompt)
		binding.target = self
		binding.action = #selector(selectBinding)
		role.addItems(withTitles: ["Curator", "Editor"])
		confirmLegacyOutput.isHidden = true
		titleLanguage.addItems(withTitles: ["Follow instructions", "Chinese"])
		typography.addItems(withTitles: ["Preserve generated text", "Chinese editorial style"])
		let textScroll = NSScrollView()
		textScroll.hasVerticalScroller = true
		textScroll.borderType = .bezelBorder
		textScroll.documentView = instructions
		textScroll.widthAnchor.constraint(equalToConstant: 530).isActive = true
		textScroll.heightAnchor.constraint(equalToConstant: 160).isActive = true
		instructions.isRichText = false
		instructions.isEditable = true
		let actions = NSStackView(views: [button("New", #selector(newPrompt)), button("Save", #selector(savePrompt)), button("Save as Copy", #selector(copyPrompt)), button("Cancel", #selector(cancelPrompt)), button("Delete", #selector(deletePrompt))])
		let historyActions = NSStackView(views: [history, button("Preview", #selector(previewHistory)), button("Restore Text", #selector(restoreHistory))])
		return form([NSTextField(wrappingLabelWithString: "Prompts are reusable. Curator and Editor are chosen independently."),
			row("Prompt", prompts), row("Name", promptName), row("Role", role), row("Service", binding), row("Model or target", target),
			NSTextField(labelWithString: "Instructions"), textScroll,
			NSTextField(wrappingLabelWithString: "Available inputs include {{title}}, {{content}}, {{description}} and, for Paper, {{abstract}}. The system validates required output."),
			row("Title language", titleLanguage), row("Typography", typography), confirmLegacyOutput, usedBy, actions,
			button("Copy Instructions", #selector(copyInstructions)), button("Import Legacy Prompt", #selector(importLegacy)),
			NSTextField(wrappingLabelWithString: "Restore Text keeps the currently selected service, target, and output preferences."), historyActions])
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
			loadLists()
		case .stopping:
			statusLabel.stringValue = NSLocalizedString("Stopping…", comment: "Processing status")
			actionButton.title = NSLocalizedString("Stop", comment: "Processing action")
			actionButton.isEnabled = false
		case .failed(let message):
			statusLabel.stringValue = message
			actionButton.title = NSLocalizedString("Retry", comment: "Processing action")
			actionButton.isEnabled = true
		}
		setEnabled(ProcessingEngine.shared.state == .ready, in: configurationTabs)
	}

	private func setEnabled(_ enabled: Bool, in view: NSView) {
		if let control = view as? NSControl { control.isEnabled = enabled }
		if let text = view as? NSTextView { text.isEditable = enabled }
		for child in view.subviews { setEnabled(enabled, in: child) }
	}

	private func request(_ method: String, _ path: String, _ body: [String: Any] = [:], then: @escaping ([String: Any]) -> Void) {
		ProcessingEngine.shared.request(method: method, path: path, body: body) { [weak self] result in
			switch result {
			case .success(let value): then(value)
			case .failure(let error):
				if error as? ProcessingEngine.EngineError == .snapshotExpired {
					self?.feedback.stringValue = "The routing report expired. Preview again."
				} else if error as? ProcessingEngine.EngineError == .snapshotCapacity {
					self?.feedback.stringValue = "The routing report is too large to retain. No mappings were applied."
				} else if error as? ProcessingEngine.EngineError == .invalidConfiguration {
					self?.feedback.stringValue = "Configuration is invalid or in use. Check the binding, directory, and source references."
				} else { self?.feedback.stringValue = "Could not save or load configuration. Check the processing component and try again." }
			}
		}
	}

	private func loadLists() {
		loadPage("services", after: nil, collected: []) { [weak self] rows in
			guard let self else { return }
			self.serviceRows = rows
			self.editorGatewayRows = rows.filter { $0["type"] as? String == "magpie" }
			self.editorGateway.removeAllItems()
			self.editorGateway.addItems(withTitles: self.editorGatewayRows.map { $0["name"] as? String ?? "Unavailable service" })
			self.services.removeAllItems()
			self.binding.removeAllItems()
			for row in rows {
				let name = row["name"] as? String ?? "Unavailable service"
				self.services.addItem(withTitle: name)
				self.binding.addItem(withTitle: name)
			}
			if let id = self.currentService?["id"] as? String, let index = rows.firstIndex(where: { $0["id"] as? String == id }) { self.services.selectItem(at: index) }
			if let id = self.selectedBinding?["id"] as? String, let index = rows.firstIndex(where: { $0["id"] as? String == id }) { self.binding.selectItem(at: index) }
		}
		loadPage("prompts", after: nil, collected: []) { [weak self] rows in
			guard let self else { return }
			let rows = rows.sorted {
				let first = ($0["role"] as? String ?? "", $0["name"] as? String ?? "")
				let second = ($1["role"] as? String ?? "", $1["name"] as? String ?? "")
				return first < second
			}
			self.promptRows = rows
			self.prompts.removeAllItems()
			for row in rows {
				let name = row["name"] as? String ?? "Unavailable prompt"
				let role = (row["role"] as? String ?? "").capitalized
				self.prompts.addItem(withTitle: "\(role): \(name)")
			}
			if let id = self.currentPrompt?["id"] as? String, let index = rows.firstIndex(where: { $0["id"] as? String == id }) { self.prompts.selectItem(at: index) }
		}
	}

	private func loadPage(_ kind: String, after: String?, collected: [[String: Any]], then: @escaping ([[String: Any]]) -> Void) {
		var body: [String: Any] = [:]
		if let after { body["after"] = after }
		request("GET", "/api/config/\(kind)", body) { [weak self] value in
			let rows = collected + (value[kind] as? [[String: Any]] ?? [])
			if let next = value["next"] as? String {
				self?.loadPage(kind, after: next, collected: rows, then: then)
			} else { then(rows) }
		}
	}

	@objc private func selectService() {
		migrationReview.invalidate()
		let index = services.indexOfSelectedItem
		guard serviceRows.indices.contains(index), let id = serviceRows[index]["id"] as? String else { return }
		if currentService?["id"] as? String != id, !confirmDiscardService() {
			if let old = currentService?["id"] as? String, let position = serviceRows.firstIndex(where: { $0["id"] as? String == old }) { services.selectItem(at: position) }
			return
		}
		request("GET", "/api/config/services", ["id": id]) { [weak self] value in
			guard let self else { return }
			guard self.serviceRows.indices.contains(self.services.indexOfSelectedItem),
				  self.serviceRows[self.services.indexOfSelectedItem]["id"] as? String == id else { return }
			self.currentService = value
			self.migrationChoices = [:]
			self.editorServices = [:]
			self.migrationWaiting = false
			self.legacyRows = []
			self.legacyBinding.removeAllItems()
			self.legacyTarget.removeAllItems()
			self.legacyTarget.addItems(withTitles: value["targets"] as? [String] ?? [])
			self.serviceName.stringValue = value["name"] as? String ?? ""
			self.endpoint.stringValue = value["endpoint"] as? String ?? ""
			self.serviceType.selectItem(at: value["type"] as? String == "magpie" ? 0 : 1)
			self.credential.stringValue = ""
			let checked = value["checkedAt"] as? String ?? "never"
			self.feedback.stringValue = value["stale"] as? Bool == true ? "Directory is stale; last checked: \(checked). Refresh to select a new target." : "Directory checked: \(checked). This does not test generation."
		}
	}

	@objc private func newService() {
		guard confirmDiscardService() else { return }
		resetService()
	}

	private func resetService() {
		migrationReview.invalidate()
		migrationWaiting = false
		currentService = nil
		serviceName.stringValue = ""
		endpoint.stringValue = ""
		credential.stringValue = ""
	}

	private func confirmDiscardService() -> Bool {
		let dirty: Bool
		if let current = currentService {
			dirty = serviceName.stringValue != current["name"] as? String || endpoint.stringValue != current["endpoint"] as? String ||
				(serviceType.indexOfSelectedItem == 0) != (current["type"] as? String == "magpie") || !credential.stringValue.isEmpty
		} else { dirty = !serviceName.stringValue.isEmpty || !endpoint.stringValue.isEmpty || !credential.stringValue.isEmpty }
		guard dirty else { return true }
		let alert = NSAlert()
		alert.messageText = "Discard unsaved service changes?"
		alert.addButton(withTitle: "Keep Editing")
		alert.addButton(withTitle: "Discard")
		return alert.runModal() == .alertSecondButtonReturn
	}

	@objc private func saveService() {
		migrationReview.invalidate()
		var body: [String: Any] = ["name": serviceName.stringValue, "type": serviceType.indexOfSelectedItem == 0 ? "magpie" : "openai-compatible", "endpoint": endpoint.stringValue]
		if let id = currentService?["id"] as? String { body["id"] = id }
		let secret = credential.stringValue
		request("PUT", "/api/config/services", body) { [weak self] value in
			guard let self, let id = value["id"] as? String else { return }
			self.currentService = value
			if body["type"] as? String == "openai-compatible", !secret.isEmpty {
				do {
					try CredentialsManager.storeCredentials(Credentials(type: .oauthAccessToken, username: "credential", secret: secret), server: "nonews-ai-\(id)")
					self.credential.stringValue = ""
				} catch {
					self.feedback.stringValue = "Service saved, but the credential could not be stored. The connection is incomplete."
					self.loadLists()
					return
				}
			}
			if body["type"] as? String == "openai-compatible" {
				do {
					guard try CredentialsManager.retrieveCredentials(type: .oauthAccessToken, server: "nonews-ai-\(id)", username: "credential") != nil else {
						self.feedback.stringValue = "Service saved without a credential. Add one to complete the connection."
						self.loadLists()
						return
					}
				} catch {
					self.feedback.stringValue = "Service saved, but its credential could not be read. The connection is incomplete."
					self.loadLists()
					return
				}
			}
			self.feedback.stringValue = "Service saved. Refresh its directory before choosing a target."
			self.loadLists()
		}
	}

	@objc private func refreshService() {
		migrationReview.invalidate()
		guard let service = currentService, let id = service["id"] as? String else { feedback.stringValue = "Save a service first."; return }
		var body: [String: Any] = ["id": id]
		if service["type"] as? String == "openai-compatible" {
			do {
				guard let stored = try CredentialsManager.retrieveCredentials(type: .oauthAccessToken, server: "nonews-ai-\(id)", username: "credential") else {
					feedback.stringValue = "Add and save the service credential first."
					return
				}
				body["credential"] = stored.secret
			} catch { feedback.stringValue = "Could not read the service credential from Keychain."; return }
		}
		request("POST", "/api/config/refresh", body) { [weak self] value in
			guard let self, self.currentService?["id"] as? String == id else { return }
			self.currentService = value
			self.migrationReview.invalidate()
			self.legacyTarget.removeAllItems()
			self.legacyTarget.addItems(withTitles: value["targets"] as? [String] ?? [])
			switch value["error"] as? String {
			case "authentication": self.feedback.stringValue = "Authentication failed. Check the credential; the previous directory is stale."
			case "network": self.feedback.stringValue = "Could not reach the directory. The previous directory is stale."
			case "invalid_output": self.feedback.stringValue = "The directory returned an invalid response. The previous directory is stale."
			default: self.feedback.stringValue = "Directory checked. This does not test generation."
			}
		}
	}

	func controlTextDidChange(_ notification: Notification) { migrationReview.invalidate() }
	@objc private func migrationInputChanged() { migrationReview.invalidate() }

	private func currentMigrationInput() -> MigrationReviewState.Input? {
		let index = services.indexOfSelectedItem
		guard serviceRows.indices.contains(index), let id = currentService?["id"] as? String,
			  serviceRows[index]["id"] as? String == id, currentService?["type"] as? String == "magpie" else { return nil }
		return .init(serviceID: id, choices: migrationChoices, editorServices: editorServices)
	}

	@objc private func previewMigration() {
		guard let input = currentMigrationInput() else { migrationStatus.stringValue = "Select a saved Magpie service and refresh its directory."; return }
		let ticket = migrationReview.begin(input)
		editorReviewToken = nil
		request("POST", "/api/config/migration/preview", ["serviceId": input.serviceID, "choices": input.choices, "editorServices": input.editorServices]) { [weak self] result in
			guard let self, self.migrationReview.accepts(ticket, current: self.currentMigrationInput()) else { return }
			self.loadMigrationReport(result, data: Data(), ticket: ticket) { [weak self] report in
				guard let self, self.migrationReview.complete(ticket, current: self.currentMigrationInput()) else { return }
				self.editorReviewToken = report["editorReviewToken"] as? String
				self.showMigrationReport(report)
			}
		}
	}

	@objc private func pauseMigration() {
		guard currentMigrationInput() != nil else { migrationStatus.stringValue = "Select a Magpie service first."; return }
		migrationReview.invalidate()
		request("POST", "/api/config/migration/pause", [:]) { [weak self] _ in
			self?.migrationWaiting = false
			self?.previewMigration()
		}
	}
	@objc private func applyMigration() {
		guard let input = migrationReview.reviewed, input == currentMigrationInput() else { migrationStatus.stringValue = "Preview and review the current mappings first."; return }
		let alert = NSAlert()
		alert.messageText = "Apply the reviewed legacy mappings?"
		alert.informativeText = "Claims must be paused and running work must finish. Unresolved work remains blocked."
		alert.addButton(withTitle: "Apply Mappings")
		alert.addButton(withTitle: "Cancel")
		guard alert.runModal() == .alertFirstButtonReturn, migrationReview.reviewed == input, currentMigrationInput() == input else { return }
		if !input.editorServices.isEmpty && editorReviewToken == nil { migrationStatus.stringValue = "Review the Editor gateway associations again."; return }
		var body: [String: Any] = ["serviceId": input.serviceID, "choices": input.choices, "editorServices": input.editorServices]
		if let token = editorReviewToken { body["reviewToken"] = token }
		migrationReview.invalidate()
		request("POST", "/api/config/migration/apply", body) { [weak self] result in
			guard let self else { return }
			self.migrationWaiting = result["status"] as? String == "waiting"
			if self.currentMigrationInput() == input { self.previewMigration() }
		}
	}

	@objc private func chooseMapping() {
		let index = legacyBinding.indexOfSelectedItem
		guard legacyRows.indices.contains(index), let kit = legacyRows[index]["kit"] as? String,
			  let role = legacyRows[index]["role"] as? String, let chosen = legacyTarget.selectedItem?.title else { return }
		migrationChoices["\(kit)/\(role)"] = chosen
		migrationReview.invalidate()
		previewMigration()
	}

	@objc private func chooseEditorGateway() {
		let jobIndex = legacyJob.indexOfSelectedItem
		let gatewayIndex = editorGateway.indexOfSelectedItem
		guard legacyJobs.indices.contains(jobIndex), editorGatewayRows.indices.contains(gatewayIndex),
			  let job = legacyJobs[jobIndex]["id"] as? String, let service = editorGatewayRows[gatewayIndex]["id"] as? String else { return }
		editorServices[job] = service
		migrationReview.invalidate()
		previewMigration()
	}

	private func loadMigrationReport(_ page: [String: Any], data: Data, ticket: MigrationReviewState.Ticket, then: @escaping ([String: Any]) -> Void) {
		guard migrationReview.accepts(ticket, current: currentMigrationInput()) else { return }
		guard let encoded = page["chunk"] as? String else { then(page); return }
		guard let chunk = Data(base64Encoded: encoded) else { feedback.stringValue = "Could not read the routing report."; return }
		var accumulated = data
		accumulated.append(chunk)
		if let next = page["next"] as? [String: Any] {
			request("POST", "/api/config/migration/preview", next) { [weak self] result in
				self?.loadMigrationReport(result, data: accumulated, ticket: ticket, then: then)
			}
		} else if let result = try? JSONSerialization.jsonObject(with: accumulated) as? [String: Any] {
			then(result)
			if let snapshot = page["snapshotId"] as? String {
				request("POST", "/api/config/migration/release", ["snapshotId": snapshot]) { _ in }
			}
		} else { feedback.stringValue = "Could not read the routing report." }
	}

	private func showMigrationReport(_ result: [String: Any]) {
			self.legacyRows = result["models"] as? [[String: Any]] ?? []
			self.legacyBinding.removeAllItems()
			for row in self.legacyRows {
				let old = row["old"] as? [String: Any] ?? [:]
				let source = "\(old["provider"] as? String ?? "")/\(old["model"] as? String ?? "")"
				let destination = row["target"] as? String ?? "Unresolved"
				self.legacyBinding.addItem(withTitle: "\(row["kit"] as? String ?? "") / \(row["role"] as? String ?? ""): \(source) → \(destination)")
			}
			let jobs = result["pending"] as? [[String: Any]] ?? []
			let blocked = jobs.filter { !($0["blocked"] as? [String] ?? []).isEmpty }.count
			let running = result["running"] as? Int ?? 0
			let paused = result["paused"] as? Bool == true
			if !paused { migrationWaiting = false }
			let state = MigrationReviewState.status(paused: paused, waiting: migrationWaiting)
			self.legacyJobs = jobs.filter { $0["editorTarget"] is String }
			self.legacyJob.removeAllItems()
			self.legacyJob.addItems(withTitles: self.legacyJobs.map { $0["id"] as? String ?? "Unknown job" })
			let details = jobs.map { job in
				let reasons = (job["blocked"] as? [String] ?? []).joined(separator: ", ")
				let target = job["editorTarget"] as? String
				func gatewayName(_ id: String?) -> String {
					guard let id else { return "unknown" }
					return self.serviceRows.first { $0["id"] as? String == id }?["name"] as? String ?? "Unavailable (\(id))"
				}
				let known = gatewayName(job["editorServiceId"] as? String)
				let proposed = gatewayName(job["proposedEditorServiceId"] as? String)
				let knownID = job["editorServiceId"] as? String
				let proposedID = job["proposedEditorServiceId"] as? String
				let confirmation = knownID != nil ? (knownID == proposedID ? "existing association" : "conflicting proposal") :
					(job["editorAssociationExplicit"] as? Bool == true ? "selected for review" : "not confirmed")
				let editor = target.map { " Editor target: \($0); known gateway: \(known); proposed gateway: \(proposed) (\(confirmation))." } ?? ""
				return "\(job["id"] as? String ?? "Unknown job"): \(reasons.isEmpty ? "ready for mapping" : reasons).\(editor)"
			}.joined(separator: "\n")
			self.migrationStatus.stringValue = "\(state): \(running) running, \(jobs.count) pending, \(blocked) unresolved. Select a binding and target to choose a mapping.\n\(details)"
	}

	@objc private func deleteService() {
		guard let id = currentService?["id"] as? String else { return }
		let using = promptRows.filter { $0["serviceId"] as? String == id }.compactMap { $0["name"] as? String }
		guard using.isEmpty else { feedback.stringValue = "Service is used by: " + using.joined(separator: ", "); return }
		let alert = NSAlert()
		alert.messageText = "Remove this service?"
		alert.addButton(withTitle: "Remove")
		alert.addButton(withTitle: "Cancel")
		guard alert.runModal() == .alertFirstButtonReturn else { return }
		request("DELETE", "/api/config/services", ["id": id]) { [weak self] _ in
			do { try CredentialsManager.removeCredentials(type: .oauthAccessToken, server: "nonews-ai-\(id)", username: "credential") }
			catch {
				self?.resetService()
				self?.loadLists()
				self?.feedback.stringValue = "Service removed, but its Keychain credential could not be removed."
				return
			}
			self?.resetService()
			self?.loadLists()
			self?.feedback.stringValue = "Service removed. Services in use cannot be removed."
		}
	}

	@objc private func selectPrompt() {
		let index = prompts.indexOfSelectedItem
		guard promptRows.indices.contains(index), let id = promptRows[index]["id"] as? String else { return }
		if currentPrompt?["id"] as? String != id, !confirmDiscardPrompt() {
			if let old = currentPrompt?["id"] as? String, let position = promptRows.firstIndex(where: { $0["id"] as? String == old }) { prompts.selectItem(at: position) }
			return
		}
		showPrompt(id)
	}

	private func showPrompt(_ id: String) {
		request("GET", "/api/config/prompts", ["id": id]) { [weak self] value in
			guard let self else { return }
			self.currentPrompt = value
			self.promptName.stringValue = value["name"] as? String ?? ""
			self.role.selectItem(at: value["role"] as? String == "curator" ? 0 : 1)
			self.role.isEnabled = false
			self.titleLanguage.selectItem(at: value["titleLanguage"] as? String == "chinese" ? 1 : 0)
			self.typography.selectItem(at: value["typography"] as? String == "chinese" ? 1 : 0)
			self.confirmLegacyOutput.isHidden = value["legacyOutputStatus"] as? String != "needs_review"
			self.confirmLegacyOutput.state = .off
			self.instructions.string = value["text"] as? String ?? ""
			self.loadHistory(id, before: nil, collected: [])
			self.loadReferences(id, after: nil, collected: []) { [weak self] refs in
				let names = refs.compactMap { $0["name"] as? String }
				self?.usedBy.stringValue = names.isEmpty ? "Used by: none" : "Used by: " + names.joined(separator: ", ")
			}
			if let serviceID = value["serviceId"] as? String,
			   let position = self.serviceRows.firstIndex(where: { $0["id"] as? String == serviceID }) {
				self.binding.selectItem(at: position)
				self.loadBinding(serviceID, selected: value["target"] as? String)
			} else { self.target.removeAllItems(); self.feedback.stringValue = "The bound service is unavailable." }
		}
	}

	@objc private func newPrompt() {
		guard confirmDiscardPrompt() else { return }
		resetPrompt()
	}

	private func resetPrompt() {
		currentPrompt = nil
		role.isEnabled = true
		promptName.stringValue = ""
		instructions.string = ""
		titleLanguage.selectItem(at: 0)
		typography.selectItem(at: 0)
		confirmLegacyOutput.isHidden = true
		confirmLegacyOutput.state = .off
		versions = []
		history.removeAllItems()
		usedBy.stringValue = "Used by: none"
	}

	@objc private func cancelPrompt() {
		if let id = currentPrompt?["id"] as? String { showPrompt(id) } else { resetPrompt() }
	}

	@objc private func copyInstructions() {
		NSPasteboard.general.clearContents()
		NSPasteboard.general.setString(instructions.string, forType: .string)
		feedback.stringValue = "Instructions copied."
	}

	@objc private func importLegacy() {
		guard confirmDiscardPrompt(), let serviceID = selectedBinding?["id"] as? String,
			  let selectedTarget = target.selectedItem?.title else {
			feedback.stringValue = "Choose a service and target before importing."
			return
		}
		loadLegacy([:], collected: []) { [weak self] rows in
			guard let self else { return }
			guard !rows.isEmpty else { self.feedback.stringValue = "No legacy prompts are available."; return }
			let choices = NSPopUpButton()
			choices.addItems(withTitles: rows.map { "\($0["kit"] as? String ?? "") / \($0["role"] as? String ?? "")" })
			let name = NSTextField()
			name.placeholderString = "Name for the imported prompt"
			let fields = NSStackView(views: [choices, name])
			fields.orientation = .vertical
			fields.frame = NSRect(x: 0, y: 0, width: 400, height: 70)
			let alert = NSAlert()
			alert.messageText = "Import a legacy prompt"
			alert.informativeText = "Existing instruction versions are preserved. Review the imported output preferences before use."
			alert.accessoryView = fields
			alert.addButton(withTitle: "Import")
			alert.addButton(withTitle: "Cancel")
			guard alert.runModal() == .alertFirstButtonReturn, rows.indices.contains(choices.indexOfSelectedItem) else { return }
			let selected = rows[choices.indexOfSelectedItem]
			guard let kit = selected["kit"] as? String, let role = selected["role"] as? String else { return }
			self.request("POST", "/api/config/import-legacy", ["kit": kit, "role": role, "name": name.stringValue,
				"serviceId": serviceID, "target": selectedTarget]) { [weak self] value in
				guard let self, let id = value["id"] as? String else { return }
				self.currentPrompt = nil
				self.loadLists()
				self.showPrompt(id)
				self.feedback.stringValue = "Imported. Review and confirm output preferences before processing."
			}
		}
	}

	private func loadLegacy(_ cursor: [String: Any], collected: [[String: Any]], then: @escaping ([[String: Any]]) -> Void) {
		request("GET", "/api/config/legacy", cursor) { [weak self] result in
			let rows = collected + (result["prompts"] as? [[String: Any]] ?? [])
			if let next = result["next"] as? [String: Any] { self?.loadLegacy(next, collected: rows, then: then) }
			else { then(rows) }
		}
	}

	private func confirmDiscardPrompt() -> Bool {
		let dirty: Bool
		if let current = currentPrompt {
			dirty = promptName.stringValue != current["name"] as? String || instructions.string != current["text"] as? String ||
				target.selectedItem?.title != current["target"] as? String || selectedBinding?["id"] as? String != current["serviceId"] as? String ||
				(titleLanguage.indexOfSelectedItem == 1) != (current["titleLanguage"] as? String == "chinese") ||
				(typography.indexOfSelectedItem == 1) != (current["typography"] as? String == "chinese")
		} else { dirty = !promptName.stringValue.isEmpty || !instructions.string.isEmpty }
		guard dirty else { return true }
		let alert = NSAlert()
		alert.messageText = "Discard unsaved prompt changes?"
		alert.addButton(withTitle: "Keep Editing")
		alert.addButton(withTitle: "Discard")
		return alert.runModal() == .alertSecondButtonReturn
	}

	@objc private func selectBinding() {
		let index = binding.indexOfSelectedItem
		guard serviceRows.indices.contains(index), let id = serviceRows[index]["id"] as? String else { return }
		loadBinding(id, selected: nil)
	}

	private func loadBinding(_ id: String, selected: String?) {
		target.removeAllItems()
		selectedBinding = nil
		request("GET", "/api/config/services", ["id": id]) { [weak self] value in
			guard let self else { return }
			self.selectedBinding = value
			let targets = value["targets"] as? [String] ?? []
			self.target.addItems(withTitles: targets)
			if let selected {
				if !targets.contains(selected) { self.target.addItem(withTitle: selected) }
				self.target.selectItem(withTitle: selected)
			} else { self.target.selectItem(at: -1) }
			if value["stale"] as? Bool == true { self.feedback.stringValue = "Directory is stale. Refresh the service before selecting a new target." }
		}
	}

	private func promptBody() -> [String: Any]? {
		guard !instructions.string.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty, instructions.string.utf8.count <= 200_000 else {
			feedback.stringValue = "Instructions must be nonempty and at most 200,000 UTF-8 bytes."
			return nil
		}
		guard let serviceID = selectedBinding?["id"] as? String, let chosen = target.selectedItem?.title else {
			feedback.stringValue = "Choose a service and model or target."
			return nil
		}
		var body: [String: Any] = ["name": promptName.stringValue, "role": role.indexOfSelectedItem == 0 ? "curator" : "editor",
			"text": instructions.string, "serviceId": serviceID, "target": chosen]
		if let id = currentPrompt?["id"] as? String { body["id"] = id }
		body["titleLanguage"] = titleLanguage.indexOfSelectedItem == 1 ? "chinese" : "instructions"
		body["typography"] = typography.indexOfSelectedItem == 1 ? "chinese" : "preserve"
		if !confirmLegacyOutput.isHidden && confirmLegacyOutput.state == .on { body["confirmLegacyOutput"] = true }
		return body
	}

	private func loadHistory(_ id: String, before: String?, collected: [[String: Any]]) {
		var body: [String: Any] = ["id": id]
		if let before { body["before"] = before }
		request("GET", "/api/config/history", body) { [weak self] result in
			guard let self else { return }
			let all = collected + (result["versions"] as? [[String: Any]] ?? [])
			if let next = result["next"] as? String { self.loadHistory(id, before: next, collected: all); return }
			self.versions = all
			self.history.removeAllItems()
			self.history.addItems(withTitles: all.map { $0["createdAt"] as? String ?? "Unknown date" })
		}
	}

	private func loadReferences(_ id: String, after: String?, collected: [[String: Any]], then: @escaping ([[String: Any]]) -> Void) {
		var body: [String: Any] = ["promptId": id]
		if let after { body["after"] = after }
		request("GET", "/api/config/references", body) { [weak self] result in
			let rows = collected + (result["references"] as? [[String: Any]] ?? [])
			if let next = result["next"] as? String { self?.loadReferences(id, after: next, collected: rows, then: then) }
			else { then(rows) }
		}
	}

	private func selectedVersion() -> (String, String)? {
		let index = history.indexOfSelectedItem
		guard versions.indices.contains(index), let version = versions[index]["id"] as? String,
			  let id = currentPrompt?["id"] as? String else { return nil }
		return (id, version)
	}

	@objc private func previewHistory() {
		guard let (id, version) = selectedVersion() else { return }
		request("GET", "/api/config/history", ["id": id, "versionId": version]) { value in
			let alert = NSAlert()
			alert.messageText = "Instruction history"
			let scroll = NSScrollView(frame: NSRect(x: 0, y: 0, width: 500, height: 260))
			scroll.hasVerticalScroller = true
			let text = NSTextView(frame: scroll.bounds)
			text.isEditable = false
			text.string = value["text"] as? String ?? ""
			scroll.documentView = text
			alert.accessoryView = scroll
			alert.addButton(withTitle: "Close")
			alert.runModal()
		}
	}

	@objc private func restoreHistory() {
		guard let (id, version) = selectedVersion(), let body = promptBody() else { return }
		loadReferences(id, after: nil, collected: []) { [weak self] refs in
			guard let self else { return }
			if !refs.isEmpty {
				let alert = NSAlert()
				alert.messageText = "This prompt is shared by \(refs.count) sources."
				alert.informativeText = refs.compactMap { $0["name"] as? String }.joined(separator: ", ")
				alert.addButton(withTitle: "Restore Text")
				alert.addButton(withTitle: "Restore as Copy")
				alert.addButton(withTitle: "Cancel")
				let choice = alert.runModal()
				if choice == .alertSecondButtonReturn {
					self.request("GET", "/api/config/history", ["id": id, "versionId": version]) { [weak self] old in
						var copy = body
						copy["text"] = old["text"]
						self?.request("POST", "/api/config/copy", ["id": id, "name": self?.promptName.stringValue ?? "Copy", "configuration": copy]) { [weak self] value in
							self?.currentPrompt = value
							self?.instructions.string = value["text"] as? String ?? ""
							self?.feedback.stringValue = "Restored as an independent copy."
							self?.loadLists()
						}
					}
					return
				}
				if choice != .alertFirstButtonReturn { return }
			}
			self.request("POST", "/api/config/restore", ["id": id, "versionId": version, "configuration": body]) { [weak self] value in
				self?.currentPrompt = value
				self?.instructions.string = value["text"] as? String ?? ""
				self?.feedback.stringValue = "Instructions restored with the selected service, target, and output preferences."
				self?.loadHistory(id, before: nil, collected: [])
			}
		}
	}

	@objc private func savePrompt() {
		guard let body = promptBody() else { return }
		if let id = body["id"] as? String {
			loadReferences(id, after: nil, collected: []) { [weak self] refs in
				guard let self else { return }
				if !refs.isEmpty {
					let alert = NSAlert()
					alert.messageText = "This prompt is shared by \(refs.count) sources."
					alert.informativeText = refs.compactMap { $0["name"] as? String }.joined(separator: ", ")
					alert.addButton(withTitle: "Save Changes")
					alert.addButton(withTitle: "Save as Copy")
					alert.addButton(withTitle: "Cancel")
					let choice = alert.runModal()
					if choice == .alertSecondButtonReturn { self.copyPrompt(); return }
					if choice != .alertFirstButtonReturn { return }
				}
				self.persistPrompt(body)
			}
		} else { persistPrompt(body) }
	}

	private func persistPrompt(_ body: [String: Any]) {
		request("PUT", "/api/config/prompts", body) { [weak self] value in
			self?.currentPrompt = value
			if let id = value["id"] as? String { self?.loadHistory(id, before: nil, collected: []) }
			self?.feedback.stringValue = "Prompt saved. Future processing uses this configuration."
			self?.loadLists()
		}
	}

	@objc private func copyPrompt() {
		guard let body = promptBody(), let id = currentPrompt?["id"] as? String else { return }
		request("POST", "/api/config/copy", ["id": id, "name": promptName.stringValue, "configuration": body]) { [weak self] value in
			self?.currentPrompt = value
			self?.feedback.stringValue = "Copy saved independently. Existing source references were not changed."
			self?.loadLists()
		}
	}

	@objc private func deletePrompt() {
		guard let id = currentPrompt?["id"] as? String else { return }
		loadReferences(id, after: nil, collected: []) { [weak self] refs in
			guard let self else { return }
			let names = refs.compactMap { $0["name"] as? String }
			guard names.isEmpty else { self.feedback.stringValue = "Prompt is used by: " + names.joined(separator: ", "); return }
			let alert = NSAlert()
			alert.messageText = "Remove this prompt?"
			alert.informativeText = "Historical instruction versions remain available to existing results."
			alert.addButton(withTitle: "Remove")
			alert.addButton(withTitle: "Cancel")
			guard alert.runModal() == .alertFirstButtonReturn else { return }
			self.request("DELETE", "/api/config/prompts", ["id": id]) { [weak self] _ in
				self?.resetPrompt()
				self?.loadLists()
				self?.feedback.stringValue = "Prompt removed."
			}
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
