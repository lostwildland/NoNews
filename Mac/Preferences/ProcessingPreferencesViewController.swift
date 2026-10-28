import AppKit
import Secrets

@MainActor protocol ProcessingPreferencesRequesting {
	func request(method: String, path: String, body: [String: Any], completion: @escaping (Result<[String: Any], Error>) -> Void)
}

@MainActor final class ProcessingEnginePreferencesRequestClient: ProcessingPreferencesRequesting {
	func request(method: String, path: String, body: [String: Any], completion: @escaping (Result<[String: Any], Error>) -> Void) {
		ProcessingEngine.shared.request(method: method, path: path, body: body, completion: completion)
	}
}

@MainActor final class ProcessingPreferencesViewController: NSViewController, NSTextFieldDelegate, NSTextViewDelegate {
	private let requestClient: ProcessingPreferencesRequesting
	private let statusLabel = NSTextField(labelWithString: "")
	private let actionButton = NSButton(title: "", target: nil, action: nil)
	private let recoveryButton = NSButton(title: "Acknowledge Unknown Saves", target: nil, action: nil)
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
	private let advancedOutput = NSStackView()
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
	private let legacyTarget = NSPopUpButton()
	private let editorGateway = NSPopUpButton()
	private let reportSection = NSPopUpButton()
	private let reportPosition = NSTextField(labelWithString: "No report")
	private let reportDetail = NSTextView()
	private let migrationStatus = NSTextField(wrappingLabelWithString: "Review legacy routing only when migrating existing settings.")
	private var reportSnapshot: String?
	private var reportCounts: [String: Int] = [:]
	private var reportIndex = 0
	private var reportGeneration = 0
	private var reportRequestInFlight = false
	private var reportRow: [String: Any] = [:]
	private var editorGatewayRows: [[String: Any]] = []
	private var migrationChoices: [String: String] = [:]
	private var editorServices: [String: String] = [:]
	private var migrationReview = MigrationReviewState()
	private var migrationWaiting = false
	private var editorReviewToken: String?
	private var previewOperation: String?
	private var previewRequestGeneration = 0
	private var pendingApply: (id: String, ticket: MigrationReviewState.ApplyTicket)?
	private var promptGeneration = 0
	private var bindingGeneration = 0
	private var serviceGeneration = 0
	private var serviceRequestGeneration = 0
	private var listGeneration = 0
	private var recoveringMutations = Set<String>()

	init(requestClient: ProcessingPreferencesRequesting = ProcessingEnginePreferencesRequestClient()) {
		self.requestClient = requestClient
		super.init(nibName: nil, bundle: nil)
	}

	required init?(coder: NSCoder) {
		self.requestClient = ProcessingEnginePreferencesRequestClient()
		super.init(coder: coder)
	}

	override func viewDidDisappear() {
		super.viewDidDisappear()
		migrationReview.invalidate()
		cancelMigrationPreview()
		releaseMigrationReport()
	}

	override func loadView() {
		view = NSView(frame: NSRect(x: 0, y: 0, width: 640, height: 620))
		let heading = NSTextField(labelWithString: NSLocalizedString("Processing", comment: "Preferences"))
		heading.font = .boldSystemFont(ofSize: NSFont.systemFontSize)
		statusLabel.lineBreakMode = .byWordWrapping
		statusLabel.maximumNumberOfLines = 3
		actionButton.target = self
		actionButton.action = #selector(changeState(_:))
		recoveryButton.target = self
		recoveryButton.action = #selector(acknowledgeUnknownSaves)
		recoveryButton.isHidden = true
		for control in [heading, statusLabel, actionButton, recoveryButton] {
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
			recoveryButton.leadingAnchor.constraint(equalTo: actionButton.trailingAnchor, constant: 12),
			recoveryButton.centerYAnchor.constraint(equalTo: actionButton.centerYAnchor),
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

	@objc private func acknowledgeUnknownSaves() {
		ProcessingEngine.shared.acknowledgeUnknownMutations()
		recoveryButton.isHidden = true
		feedback.stringValue = "Unknown save receipts acknowledged. Review the saved configuration before retrying."
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
		promptName.delegate = self
		instructions.delegate = self
		for popup in [role, target, titleLanguage, typography] { popup.target = self; popup.action = #selector(promptInputChanged) }
		history.target = self
		history.action = #selector(promptInputChanged)
		confirmLegacyOutput.target = self
		confirmLegacyOutput.action = #selector(promptInputChanged)
		credential.placeholderString = "Stored in Keychain"
		let actions = NSStackView(views: [button("New", #selector(newService)), button("Save", #selector(saveService)), button("Refresh Models or Targets", #selector(refreshService)), button("Delete", #selector(deleteService))])
		reportSection.addItems(withTitles: ["Models", "Pending", "Evidence"])
		reportSection.target = self
		reportSection.action = #selector(changeReportSection)
		let navigation = NSStackView(views: [reportSection, button("Previous", #selector(previousReportRow)), reportPosition, button("Next", #selector(nextReportRow)), button("Retry Entry", #selector(retryReportRow))])
		let details = NSScrollView()
		details.hasVerticalScroller = true
		details.borderType = .bezelBorder
		details.documentView = reportDetail
		details.widthAnchor.constraint(equalToConstant: 530).isActive = true
		details.heightAnchor.constraint(equalToConstant: 150).isActive = true
		reportDetail.isEditable = false
		reportDetail.isSelectable = true
		reportDetail.isRichText = false
		let mapping = NSStackView(views: [legacyTarget, button("Choose Mapping for Shown Model", #selector(chooseMapping))])
		let editorMapping = NSStackView(views: [editorGateway, button("Confirm Shown Editor Gateway", #selector(chooseEditorGateway))])
		let migration = NSStackView(views: [button("Preview Routing", #selector(previewMigration)), button("Pause Claims", #selector(pauseMigration)), button("Apply Mappings", #selector(applyMigration))])
		return form([NSTextField(wrappingLabelWithString: "Reading works without AI. Refresh checks the directory only."),
			row("Service", services), row("Name", serviceName), row("Type", serviceType), row("Endpoint", endpoint),
			row("Bearer credential", credential), actions, NSTextField(labelWithString: "Advanced: Legacy Magpie Routing"),
			migrationStatus, navigation, details, mapping, editorMapping, migration])
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
		let advancedButton = NSButton(title: "Advanced", target: self, action: #selector(toggleAdvancedOutput(_:)))
		advancedButton.setButtonType(.pushOnPushOff)
		advancedButton.bezelStyle = .disclosure
		advancedOutput.orientation = .vertical
		advancedOutput.alignment = .leading
		advancedOutput.spacing = 6
		advancedOutput.addArrangedSubview(row("Title language", titleLanguage))
		advancedOutput.addArrangedSubview(row("Typography", typography))
		advancedOutput.isHidden = true
		let textScroll = NSScrollView()
		textScroll.hasVerticalScroller = true
		textScroll.borderType = .bezelBorder
		textScroll.documentView = instructions
		textScroll.widthAnchor.constraint(equalToConstant: 530).isActive = true
		textScroll.heightAnchor.constraint(equalToConstant: 160).isActive = true
		instructions.isRichText = false
		instructions.isEditable = true
		let actions = NSStackView(views: [button("New", #selector(newPrompt)), button("Save", #selector(savePrompt)), button("Save as Copy", #selector(copyPromptAction)), button("Cancel", #selector(cancelPrompt)), button("Delete", #selector(deletePrompt))])
		let historyActions = NSStackView(views: [history, button("Preview", #selector(previewHistory)), button("Restore Text", #selector(restoreHistory))])
		return form([NSTextField(wrappingLabelWithString: "Prompts are reusable. Curator and Editor are chosen independently."),
			row("Prompt", prompts), row("Name", promptName), row("Role", role), row("Service", binding), row("Model or target", target),
			NSTextField(labelWithString: "Instructions"), textScroll,
			NSTextField(wrappingLabelWithString: "Available inputs include {{title}}, {{content}}, {{description}} and, for Paper, {{abstract}}. The system validates required output."),
			advancedButton, advancedOutput, confirmLegacyOutput, usedBy, actions,
			button("Copy Instructions", #selector(copyInstructions)), button("Import Legacy Prompt", #selector(importLegacy)),
			NSTextField(wrappingLabelWithString: "Restore Text keeps the currently selected service, target, and output preferences."), historyActions])
	}

	@objc private func toggleAdvancedOutput(_ sender: NSButton) {
		advancedOutput.isHidden = sender.state != .on
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
			recoveryButton.isHidden = ProcessingEngine.shared.unconfirmedMutations.isEmpty
			loadLists()
			for identity in ProcessingEngine.shared.unconfirmedMutations where recoveringMutations.insert(identity).inserted {
				ProcessingEngine.shared.recoverMutation(identity) { [weak self] result in
					guard let self else { return }
					self.recoveringMutations.remove(identity)
					switch result {
					case .success:
						self.feedback.stringValue = "A previous save was confirmed. Review the saved configuration."
						self.loadLists()
					case .failure(let error):
						self.feedback.stringValue = error as? ProcessingEngine.EngineError == .mutationNotSaved ? "The save was cancelled before it started. Your configuration was not changed." : "A previous save is still being confirmed."
					}
				}
			}
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
		if let text = view as? NSTextView { text.isEditable = enabled && text !== reportDetail }
		for child in view.subviews { setEnabled(enabled, in: child) }
	}

	private func request(_ method: String, _ path: String, _ body: [String: Any] = [:], onFailure: (() -> Void)? = nil, then: @escaping ([String: Any]) -> Void) {
		requestClient.request(method: method, path: path, body: body) { [weak self] result in
			switch result {
			case .success(let value): then(value)
			case .failure(let error):
				if let onFailure { onFailure(); return }
				if case .some(.outcomeUnknown(_)) = error as? ProcessingEngine.EngineError {
					self?.feedback.stringValue = "The save is being confirmed. Restart processing and check the saved configuration before retrying."
				} else if error as? ProcessingEngine.EngineError == .migrationBusy {
					self?.feedback.stringValue = "Routing is being updated. Try this change again when it finishes."
				} else if error as? ProcessingEngine.EngineError == .snapshotExpired {
					self?.feedback.stringValue = "The routing report expired. Preview again."
				} else if error as? ProcessingEngine.EngineError == .snapshotCapacity {
					self?.feedback.stringValue = "The routing report is too large to retain."
				} else if error as? ProcessingEngine.EngineError == .invalidConfiguration {
					self?.feedback.stringValue = "Configuration is invalid or in use. Check the binding, directory, and source references."
				} else if error as? ProcessingEngine.EngineError == .recoveryRequired {
					self?.recoveryButton.isHidden = false
					self?.feedback.stringValue = "Previous save receipts need review. Acknowledge them after checking the saved configuration."
				} else { self?.feedback.stringValue = "Could not save or load configuration. Check the processing component and try again." }
			}
		}
	}

	private func migrationRequest(_ action: String, _ body: [String: Any], onFailure: @escaping () -> Void, started: ((String) -> Void)? = nil, then: @escaping ([String: Any]) -> Void) {
		let previewGeneration = previewRequestGeneration
		var input = body
		input["cooperative"] = true
		request("POST", "/api/config/migration/\(action)", input, onFailure: onFailure) { [weak self] result in
			guard let self, let identity = result["operationId"] as? String, result["state"] as? String == "running" else { onFailure(); return }
			if action == "preview" && previewGeneration != self.previewRequestGeneration {
				self.cancelPreview(identity)
				return
			}
			if action == "preview" { self.previewOperation = identity }
			started?(identity)
			self.pollMigration(action, identity: identity, onFailure: onFailure, then: then)
		}
	}

	private func pollMigration(_ action: String, identity: String, onFailure: @escaping () -> Void, then: @escaping ([String: Any]) -> Void) {
		request("POST", "/api/config/migration/\(action)", ["operationId": identity], onFailure: onFailure) { [weak self] value in
			guard let self, value["operationId"] as? String == identity else { onFailure(); return }
			if value["state"] as? String == "complete", let result = value["result"] as? [String: Any] {
				if action == "preview", self.previewOperation == identity { self.previewOperation = nil }
				then(result)
			} else if value["state"] as? String == "running" {
				DispatchQueue.main.asyncAfter(deadline: .now() + 0.1) { [weak self] in
					self?.pollMigration(action, identity: identity, onFailure: onFailure, then: then)
				}
			} else { onFailure() }
		}
	}

	private func cancelMigrationPreview() {
		previewRequestGeneration += 1
		guard let identity = previewOperation else { return }
		previewOperation = nil
		cancelPreview(identity)
	}

	private func cancelPreview(_ identity: String) {
		request("POST", "/api/config/migration/preview", ["operationId": identity, "cancel": true], onFailure: {}) { [weak self] response in
			if let result = response["result"] as? [String: Any], let snapshot = result["snapshotId"] as? String {
				self?.releaseSnapshot(snapshot)
			}
		}
	}

	private func loadLists() {
		listGeneration += 1
		let generation = listGeneration
		loadPage("services", after: nil, collected: []) { [weak self] rows in
			guard let self, self.listGeneration == generation else { return }
			let bindingID = self.visibleBindingID()
			self.serviceRows = rows
			self.editorGatewayRows = rows.filter { $0["type"] as? String == "magpie" }
			self.editorGateway.removeAllItems()
			self.editorGateway.addItems(withTitles: self.editorGatewayRows.map { self.serviceLabel($0) })
			self.services.removeAllItems()
			self.binding.removeAllItems()
			for row in rows {
				let name = self.serviceLabel(row)
				self.services.addItem(withTitle: name)
				self.binding.addItem(withTitle: name)
			}
			if let id = self.currentService?["id"] as? String, let index = rows.firstIndex(where: { $0["id"] as? String == id }) { self.services.selectItem(at: index) }
			if let id = bindingID, let index = rows.firstIndex(where: { $0["id"] as? String == id }) { self.binding.selectItem(at: index) }
			else { self.binding.selectItem(at: -1) }
		}
		loadPage("prompts", after: nil, collected: []) { [weak self] rows in
			guard let self, self.listGeneration == generation else { return }
			let selectedID: String? = self.promptRows.indices.contains(self.prompts.indexOfSelectedItem) ? self.promptRows[self.prompts.indexOfSelectedItem]["id"] as? String : nil
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
			if let id = selectedID, let index = rows.firstIndex(where: { $0["id"] as? String == id }) { self.prompts.selectItem(at: index) }
			else { self.prompts.selectItem(at: -1) }
		}
	}

	private func serviceLabel(_ row: [String: Any]) -> String {
		let label = MigrationReviewState.serviceLabel(name: row["name"] as? String ?? "Unavailable service", id: row["id"] as? String ?? "unknown")
		return row["credentialState"] as? String == "incomplete" ? "\(label) (Credential incomplete)" : label
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
		cancelMigrationPreview()
		let index = services.indexOfSelectedItem
		guard serviceRows.indices.contains(index), let id = serviceRows[index]["id"] as? String else { return }
		if currentService?["id"] as? String != id, !confirmDiscardService() {
			if let old = currentService?["id"] as? String, let position = serviceRows.firstIndex(where: { $0["id"] as? String == old }) { services.selectItem(at: position) }
			return
		}
		serviceGeneration += 1
		serviceRequestGeneration += 1
		let generation = serviceRequestGeneration
		request("GET", "/api/config/services", ["id": id]) { [weak self] value in
			guard let self, self.serviceRequestGeneration == generation else { return }
			guard self.serviceRows.indices.contains(self.services.indexOfSelectedItem),
				  self.serviceRows[self.services.indexOfSelectedItem]["id"] as? String == id else { return }
			self.currentService = value
			self.clearMigrationReport()
			self.migrationStatus.stringValue = "Preview routing for \(self.serviceLabel(value))."
			self.legacyTarget.addItems(withTitles: value["targets"] as? [String] ?? [])
			self.serviceName.stringValue = value["name"] as? String ?? ""
			self.endpoint.stringValue = value["endpoint"] as? String ?? ""
			self.serviceType.selectItem(at: value["type"] as? String == "magpie" ? 0 : 1)
			self.credential.stringValue = ""
			let checked = value["checkedAt"] as? String ?? "never"
			if value["credentialState"] as? String == "incomplete" {
				self.feedback.stringValue = "Credential storage is incomplete. Save and verify the credential before refreshing the directory."
			} else {
				self.feedback.stringValue = value["stale"] as? Bool == true ? "Directory is stale; last checked: \(checked). Refresh to select a new target." : "Directory checked: \(checked). This does not test generation."
			}
		}
	}

	@objc private func newService() {
		guard confirmDiscardService() else { return }
		resetService()
	}

	private func resetService() {
		serviceGeneration += 1
		serviceRequestGeneration += 1
		migrationReview.invalidate()
		cancelMigrationPreview()
		clearMigrationReport()
		migrationStatus.stringValue = "Select a saved Magpie service and refresh its directory."
		currentService = nil
		serviceName.stringValue = ""
		endpoint.stringValue = ""
		credential.stringValue = ""
	}

	private func clearMigrationReport() {
		releaseMigrationReport()
		migrationChoices = [:]
		editorServices = [:]
		migrationWaiting = false
		editorReviewToken = nil
		legacyTarget.removeAllItems()
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
		let generation = serviceGeneration
		request("PUT", "/api/config/services", body) { [weak self] value in
			guard let self, let id = value["id"] as? String else { return }
			let current = self.serviceGeneration == generation
			if body["type"] as? String == "openai-compatible", !secret.isEmpty {
				do {
					try CredentialsManager.storeCredentials(Credentials(type: .oauthAccessToken, username: "credential", secret: secret), server: "nonews-ai-\(id)")
					self.updateCredentialState(id: id, state: "verified", from: body) { result in
						guard current else { return }
						switch result {
						case .success(let updated):
							self.currentService = updated
							if self.credential.stringValue == secret { self.credential.stringValue = "" }
							self.feedback.stringValue = "Service saved and credential verified. Refresh its directory before choosing a target."
						case .failure:
							self.currentService = value
							self.feedback.stringValue = "Service saved, but credential state could not be persisted. The connection is incomplete."
						}
						self.loadLists()
					}
					return
				} catch {
					self.updateCredentialState(id: id, state: "incomplete", from: body) { _ in }
					if current { self.feedback.stringValue = "Service saved, but the credential could not be stored. The connection is incomplete." }
					self.loadLists()
					return
				}
			}
			if body["type"] as? String == "openai-compatible" {
				do {
					guard try CredentialsManager.retrieveCredentials(type: .oauthAccessToken, server: "nonews-ai-\(id)", username: "credential") != nil else {
						if current { self.currentService = value; self.feedback.stringValue = "Service saved without a credential. Add one to complete the connection." }
						self.loadLists()
						return
					}
				} catch {
					self.updateCredentialState(id: id, state: "incomplete", from: body) { _ in }
					if current { self.currentService = value; self.feedback.stringValue = "Service saved, but its credential could not be read. The connection is incomplete." }
					self.loadLists()
					return
				}
			}
			if current { self.currentService = value; self.feedback.stringValue = "Service saved. Refresh its directory before choosing a target." }
			self.loadLists()
		}
	}

	private func updateCredentialState(id: String, state: String, from body: [String: Any], completion: @escaping (Result<[String: Any], Error>) -> Void) {
		var update = body
		update["id"] = id
		update["credentialState"] = state
		request("PUT", "/api/config/services", update, completion: completion)
	}

	@objc private func refreshService() {
		migrationReview.invalidate()
		guard let service = currentService, let id = service["id"] as? String else { feedback.stringValue = "Save a service first."; return }
		let generation = serviceGeneration
		var body: [String: Any] = ["id": id]
		if service["type"] as? String == "openai-compatible" {
			guard service["credentialState"] as? String == "verified" else {
				feedback.stringValue = "Save and verify the service credential before refreshing its directory."
				return
			}
			do {
				guard let stored = try CredentialsManager.retrieveCredentials(type: .oauthAccessToken, server: "nonews-ai-\(id)", username: "credential") else {
					feedback.stringValue = "Add and save the service credential first."
					return
				}
				body["credential"] = stored.secret
			} catch { feedback.stringValue = "Could not read the service credential from Keychain."; return }
		}
		request("POST", "/api/config/refresh", body) { [weak self] value in
			guard let self, self.serviceGeneration == generation, self.currentService?["id"] as? String == id else { return }
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

	func controlTextDidChange(_ notification: Notification) {
		if notification.object as? NSTextField === promptName { promptGeneration += 1; return }
		serviceGeneration += 1
		serviceRequestGeneration += 1
		migrationReview.invalidate(); cancelMigrationPreview(); releaseMigrationReport()
	}
	func textDidChange(_ notification: Notification) { if notification.object as? NSTextView === instructions { promptGeneration += 1 } }
	@objc private func promptInputChanged() { promptGeneration += 1 }
	@objc private func migrationInputChanged() { serviceGeneration += 1; serviceRequestGeneration += 1; migrationReview.invalidate(); cancelMigrationPreview() }

	private func currentMigrationInput() -> MigrationReviewState.Input? {
		let index = services.indexOfSelectedItem
		guard serviceRows.indices.contains(index), let id = currentService?["id"] as? String,
			  serviceRows[index]["id"] as? String == id, currentService?["type"] as? String == "magpie" else { return nil }
		return .init(serviceID: id, choices: migrationChoices, editorServices: editorServices)
	}

	@objc private func previewMigration() {
		startMigrationPreview()
	}

	private func startMigrationPreview() {
		guard let input = currentMigrationInput() else { migrationStatus.stringValue = "Select a saved Magpie service and refresh its directory."; return }
		cancelMigrationPreview()
		reportGeneration += 1
		let ticket = migrationReview.begin(input)
		editorReviewToken = nil
		migrationRequest("preview", ["serviceId": input.serviceID, "choices": input.choices, "editorServices": input.editorServices, "browse": true], onFailure: { [weak self] in
			guard let self, self.migrationReview.accepts(ticket, current: self.currentMigrationInput()) else { return }
			self.migrationStatus.stringValue = self.migrationReview.readbackFailure(for: input)
		}) { [weak self] result in
			guard let self else { return }
			guard let snapshot = result["snapshotId"] as? String, let counts = result["counts"] as? [String: Int],
				  self.migrationReview.complete(ticket, current: self.currentMigrationInput()) else {
				if let snapshot = result["snapshotId"] as? String { self.releaseSnapshot(snapshot) }
				return
			}
			self.releaseMigrationReport()
			self.reportSnapshot = snapshot
			self.reportCounts = counts
			self.editorReviewToken = result["editorReviewToken"] as? String
			if let pending = self.pendingApply, let receipt = result["lastApply"] as? [String: Any],
			   receipt["operationId"] as? String == pending.id, pending.ticket.input == input,
			   self.migrationReview.recordApply(status: receipt["status"] as? String ?? "", ticket: pending.ticket) {
				self.pendingApply = nil
			}
			let paused = result["paused"] as? Bool == true
			if !paused { self.migrationWaiting = false }
			let state = MigrationReviewState.status(paused: paused, waiting: self.migrationWaiting)
			self.migrationStatus.stringValue = "\(self.migrationReview.applyAcknowledgement(for: input))\(state): \(result["running"] as? Int ?? 0) running, \(counts["pending"] ?? 0) pending, \(result["blocked"] as? Int ?? 0) unresolved."
			self.reportIndex = 0
			self.loadReportRow()
		}
	}

	@objc private func pauseMigration() {
		guard currentMigrationInput() != nil else { migrationStatus.stringValue = "Select a Magpie service first."; return }
		migrationReview.invalidate()
		cancelMigrationPreview()
		migrationRequest("pause", [:], onFailure: { [weak self] in self?.migrationStatus.stringValue = "Claims could not be paused. Try again." }) { [weak self] _ in
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
		let applyTicket = migrationReview.beginApply(input)
		migrationRequest("apply", body, onFailure: { [weak self] in
			guard let self, self.currentMigrationInput() == input else { return }
			self.migrationStatus.stringValue = "Apply could not be confirmed. Preview the durable routing status before retrying."
		}, started: { [weak self] identity in self?.pendingApply = (identity, applyTicket) }) { [weak self] result in
			self?.acceptApplyResult(result, ticket: applyTicket)
		}
	}

	private func acceptApplyResult(_ result: [String: Any], ticket: MigrationReviewState.ApplyTicket) {
		if pendingApply?.id == result["operationId"] as? String { pendingApply = nil }
		guard migrationReview.recordApply(status: result["status"] as? String ?? "", ticket: ticket),
			  currentMigrationInput() == ticket.input else { return }
		migrationStatus.stringValue = result["status"] as? String == "applied" ? "Mappings applied. Refreshing the routing report." : "Claims remain paused while work drains. Refreshing the routing report."
		migrationWaiting = result["status"] as? String == "waiting"
		if currentMigrationInput() == ticket.input { startMigrationPreview() }
	}

	@objc private func chooseMapping() {
		guard reportSection.indexOfSelectedItem == 0, let kit = reportRow["kit"] as? String,
			  let role = reportRow["role"] as? String, let chosen = legacyTarget.selectedItem?.title else { return }
		migrationChoices["\(kit)/\(role)"] = chosen
		migrationReview.invalidate()
		releaseMigrationReport()
		previewMigration()
	}

	@objc private func chooseEditorGateway() {
		let index = editorGateway.indexOfSelectedItem
		guard reportSection.indexOfSelectedItem == 1, reportRow["editorTarget"] is String,
			  let job = reportRow["id"] as? String, editorGatewayRows.indices.contains(index),
			  let service = editorGatewayRows[index]["id"] as? String else { return }
		editorServices[job] = service
		migrationReview.invalidate()
		releaseMigrationReport()
		previewMigration()
	}

	private var currentReportSection: String {
		["models", "pending", "evidence"][max(0, min(2, reportSection.indexOfSelectedItem))]
	}

	private func releaseSnapshot(_ snapshot: String) {
		migrationRequest("release", ["snapshotId": snapshot], onFailure: {}) { _ in }
	}

	private func releaseMigrationReport() {
		reportGeneration += 1
		if let snapshot = reportSnapshot { releaseSnapshot(snapshot) }
		reportSnapshot = nil
		reportCounts = [:]
		reportRow = [:]
		reportPosition.stringValue = "No report"
		reportDetail.string = ""
	}

	@objc private func changeReportSection() { reportIndex = 0; loadReportRow() }
	@objc private func retryReportRow() { loadReportRow() }
	@objc private func previousReportRow() { if reportIndex > 0 { reportIndex -= 1; loadReportRow() } }
	@objc private func nextReportRow() {
		if reportIndex + 1 < (reportCounts[currentReportSection] ?? 0) { reportIndex += 1; loadReportRow() }
	}

	private func loadReportRow() {
		reportGeneration += 1
		guard !reportRequestInFlight else { return }
		let generation = reportGeneration
		let section = currentReportSection
		let count = reportCounts[section] ?? 0
		reportRow = [:]
		guard let snapshot = reportSnapshot, reportIndex < count else {
			reportPosition.stringValue = "0 of \(count)"
			reportDetail.string = "No entries in this section."
			return
		}
		let index = reportIndex
		reportPosition.stringValue = "\(index + 1) of \(count)"
		reportDetail.string = "Loading…"
		loadReportPart(snapshot: snapshot, section: section, index: index, part: 0, data: Data(), generation: generation)
	}

	private func loadReportPart(snapshot: String, section: String, index: Int, part: Int, data: Data, generation: Int) {
		reportRequestInFlight = true
		request("POST", "/api/config/migration/preview", ["snapshotId": snapshot, "section": section, "index": index, "part": part], onFailure: { [weak self] in
			guard let self else { return }
			self.reportRequestInFlight = false
			guard self.reportGeneration == generation else { self.loadReportRow(); return }
			self.reportDetail.string = "Could not load this entry. Preview again if the report expired."
		}) { [weak self] result in
			guard let self else { return }
			self.reportRequestInFlight = false
			guard self.reportGeneration == generation, self.reportSnapshot == snapshot else { self.loadReportRow(); return }
			guard result["snapshotId"] as? String == snapshot, result["section"] as? String == section,
				  result["index"] as? Int == index, result["part"] as? Int == part,
				  let encoded = result["chunk"] as? String, let chunk = Data(base64Encoded: encoded) else { self.reportDetail.string = "The entry could not be read. Preview again."; return }
			var record = data
			record.append(chunk)
			if let next = result["nextPart"] as? Int {
				self.loadReportPart(snapshot: snapshot, section: section, index: index, part: next, data: record, generation: generation)
			} else if let item = try? JSONSerialization.jsonObject(with: record, options: .fragmentsAllowed) {
				self.reportRow = item as? [String: Any] ?? [:]
				self.reportDetail.string = self.describeReportRow(item, section: section)
			} else { self.reportDetail.string = "The entry could not be read. Preview again." }
		}
	}

	private func describeReportRow(_ item: Any, section: String) -> String {
		func value(_ value: Any?) -> String {
			guard let value, !(value is NSNull) else { return "Unknown" }
			if let dict = value as? [String: Any] { return dict.keys.sorted().map { "\($0): \(valueFor(dict[$0]))" }.joined(separator: ", ") }
			if let array = value as? [Any] { return array.map { valueFor($0) }.joined(separator: ", ") }
			return String(describing: value)
		}
		func valueFor(_ item: Any?) -> String { value(item) }
		func gateway(_ id: Any?) -> String {
			guard let id = id as? String else { return "Unknown" }
			return serviceRows.first(where: { $0["id"] as? String == id }).map { serviceLabel($0) } ?? "Unavailable [\(id)]"
		}
		guard let row = item as? [String: Any] else { return value(item) }
		if section == "models" {
			return "Kit: \(value(row["kit"]))\nRole: \(value(row["role"]))\nPrior: \(value(row["old"]))\nProposed target: \(value(row["target"]))\nBasis: \(value(row["basis"]))\nService: \(gateway(row["serviceId"]))\nBlocked: \(value(row["blocked"]))"
		}
		if section == "pending" {
			return "Job: \(value(row["id"]))\nKit: \(value(row["kit"]))\nStage: \(value(row["stage"]))\nBlocked: \(value(row["blocked"]))\nPinned Editor target: \(value(row["editorTarget"]))\nKnown gateway: \(gateway(row["editorServiceId"]))\nProposed gateway: \(gateway(row["proposedEditorServiceId"]))\nAssociation reviewed: \(value(row["editorAssociationExplicit"]))"
		}
		return row.keys.sorted().map { "\($0): \(value(row[$0]))" }.joined(separator: "\n")
	}

	@objc private func deleteService() {
		guard let id = currentService?["id"] as? String else { return }
		let generation = serviceGeneration
		let using = promptRows.filter { $0["serviceId"] as? String == id }.compactMap { $0["name"] as? String }
		guard using.isEmpty else { feedback.stringValue = "Service is used by: " + using.joined(separator: ", "); return }
		let alert = NSAlert()
		alert.messageText = "Remove this service?"
		alert.addButton(withTitle: "Remove")
		alert.addButton(withTitle: "Cancel")
		guard alert.runModal() == .alertFirstButtonReturn else { return }
		request("DELETE", "/api/config/services", ["id": id]) { [weak self] _ in
			guard let self else { return }
			var failed = false
			do { try CredentialsManager.removeCredentials(type: .oauthAccessToken, server: "nonews-ai-\(id)", username: "credential") }
			catch { failed = true }
			self.loadLists()
			guard self.serviceGeneration == generation else { return }
			self.resetService()
			self.feedback.stringValue = failed ? "Service removed, but its Keychain credential could not be removed." : "Service removed. Services in use cannot be removed."
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
		promptGeneration += 1
		bindingGeneration += 1
		let generation = promptGeneration
		currentPrompt = nil
		selectedBinding = nil
		target.removeAllItems()
		versions = []
		history.removeAllItems()
		usedBy.stringValue = "Loading references…"
		request("GET", "/api/config/prompts", ["id": id]) { [weak self] value in
			guard let self, self.promptGeneration == generation else { return }
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
		promptGeneration += 1
		bindingGeneration += 1
		currentPrompt = nil
		selectedBinding = nil
		binding.selectItem(at: -1)
		target.removeAllItems()
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
		guard confirmDiscardPrompt(), let serviceID = selectedBinding?["id"] as? String, visibleBindingID() == serviceID,
			  let selectedTarget = target.selectedItem?.title else {
			feedback.stringValue = "Choose a service and target before importing."
			return
		}
		let generation = promptGeneration
		loadLegacy([:], collected: []) { [weak self] rows in
			guard let self, self.promptGeneration == generation else { return }
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
				self.loadLists()
				guard self.promptGeneration == generation else { return }
				self.currentPrompt = nil
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
		promptGeneration += 1
		let index = binding.indexOfSelectedItem
		guard serviceRows.indices.contains(index), let id = serviceRows[index]["id"] as? String else { return }
		loadBinding(id, selected: nil)
	}

	private func loadBinding(_ id: String, selected: String?) {
		bindingGeneration += 1
		let generation = bindingGeneration
		target.removeAllItems()
		selectedBinding = nil
		request("GET", "/api/config/services", ["id": id]) { [weak self] value in
			guard let self, self.bindingGeneration == generation, self.visibleBindingID() == id else { return }
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

	private func visibleBindingID() -> String? {
		let index = binding.indexOfSelectedItem
		return serviceRows.indices.contains(index) ? serviceRows[index]["id"] as? String : nil
	}

	private func promptBody() -> [String: Any]? {
		guard let body = promptBodyForComparison() else {
			feedback.stringValue = "Choose valid instructions, a service, and a model or target. Instructions are limited to 200,000 UTF-8 bytes."
			return nil
		}
		return body
	}

	private func promptBodyForComparison() -> [String: Any]? {
		guard !instructions.string.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty, instructions.string.utf8.count <= 200_000 else {
			return nil
		}
		guard let serviceID = selectedBinding?["id"] as? String, visibleBindingID() == serviceID, let chosen = target.selectedItem?.title else {
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

	private func matchesPrompt(_ body: [String: Any], generation: Int) -> Bool {
		guard promptGeneration == generation, let current = promptBodyForComparison() else { return false }
		return NSDictionary(dictionary: current).isEqual(to: body)
	}

	private func loadHistory(_ id: String, before: String?, collected: [[String: Any]], generation: Int? = nil) {
		let ticket = generation ?? promptGeneration
		var body: [String: Any] = ["id": id]
		if let before { body["before"] = before }
		request("GET", "/api/config/history", body) { [weak self] result in
			guard let self, self.promptGeneration == ticket, self.currentPrompt?["id"] as? String == id else { return }
			let all = collected + (result["versions"] as? [[String: Any]] ?? [])
			if let next = result["next"] as? String { self.loadHistory(id, before: next, collected: all, generation: ticket); return }
			self.versions = all
			self.history.removeAllItems()
			self.history.addItems(withTitles: all.map { $0["createdAt"] as? String ?? "Unknown date" })
		}
	}

	private func loadReferences(_ id: String, after: String?, collected: [[String: Any]], generation: Int? = nil, then: @escaping ([[String: Any]]) -> Void) {
		let ticket = generation ?? promptGeneration
		var body: [String: Any] = ["promptId": id]
		if let after { body["after"] = after }
		request("GET", "/api/config/references", body) { [weak self] result in
			guard let self, self.promptGeneration == ticket, self.currentPrompt?["id"] as? String == id else { return }
			let rows = collected + (result["references"] as? [[String: Any]] ?? [])
			if let next = result["next"] as? String { self.loadReferences(id, after: next, collected: rows, generation: ticket, then: then) }
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
		let generation = promptGeneration
		request("GET", "/api/config/history", ["id": id, "versionId": version]) { [weak self] value in
			guard let self, self.promptGeneration == generation, self.currentPrompt?["id"] as? String == id else { return }
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
		let generation = promptGeneration
		loadReferences(id, after: nil, collected: []) { [weak self] refs in
			guard let self, self.matchesPrompt(body, generation: generation) else { return }
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
						guard let self, self.matchesPrompt(body, generation: generation) else { return }
						var copy = body
						copy["text"] = old["text"]
						self.request("POST", "/api/config/copy", ["id": id, "name": body["name"] ?? "Copy", "configuration": copy]) { [weak self] value in
							guard let self else { return }
							self.loadLists()
							guard self.matchesPrompt(body, generation: generation) else { return }
							self.currentPrompt = value
							self.instructions.string = value["text"] as? String ?? ""
							self.feedback.stringValue = "Restored as an independent copy."
						}
					}
					return
				}
				if choice != .alertFirstButtonReturn { return }
			}
			self.request("POST", "/api/config/restore", ["id": id, "versionId": version, "configuration": body]) { [weak self] value in
				guard let self else { return }
				self.loadLists()
				guard self.matchesPrompt(body, generation: generation) else { return }
				self.currentPrompt = value
				self.instructions.string = value["text"] as? String ?? ""
				self.feedback.stringValue = "Instructions restored with the selected service, target, and output preferences."
				self.loadHistory(id, before: nil, collected: [])
			}
		}
	}

	@objc private func savePrompt() {
		guard let body = promptBody() else { return }
		let generation = promptGeneration
		if let id = body["id"] as? String {
			loadReferences(id, after: nil, collected: []) { [weak self] refs in
				guard let self, self.matchesPrompt(body, generation: generation) else { return }
				if !refs.isEmpty {
					let alert = NSAlert()
					alert.messageText = "This prompt is shared by \(refs.count) sources."
					alert.informativeText = refs.compactMap { $0["name"] as? String }.joined(separator: ", ")
					alert.addButton(withTitle: "Save Changes")
					alert.addButton(withTitle: "Save as Copy")
					alert.addButton(withTitle: "Cancel")
					let choice = alert.runModal()
					if choice == .alertSecondButtonReturn { self.copyPrompt(body, generation: generation); return }
					if choice != .alertFirstButtonReturn { return }
				}
				self.persistPrompt(body, generation: generation)
			}
		} else { persistPrompt(body, generation: generation) }
	}

	private func persistPrompt(_ body: [String: Any], generation: Int) {
		request("PUT", "/api/config/prompts", body) { [weak self] value in
			guard let self else { return }
			self.loadLists()
			guard self.matchesPrompt(body, generation: generation) else { return }
			self.currentPrompt = value
			if let id = value["id"] as? String { self.loadHistory(id, before: nil, collected: []) }
			self.feedback.stringValue = "Prompt saved. Future processing uses this configuration."
		}
	}

	@objc private func copyPromptAction() {
		guard let body = promptBody(), currentPrompt?["id"] is String else { return }
		copyPrompt(body, generation: promptGeneration)
	}

	private func copyPrompt(_ body: [String: Any], generation: Int) {
		guard let id = body["id"] as? String else { return }
		request("POST", "/api/config/copy", ["id": id, "name": body["name"] ?? "Copy", "configuration": body]) { [weak self] value in
			guard let self else { return }
			self.loadLists()
			guard self.matchesPrompt(body, generation: generation) else { return }
			self.currentPrompt = value
			self.feedback.stringValue = "Copy saved independently. Existing source references were not changed."
		}
	}

	@objc private func deletePrompt() {
		guard let id = currentPrompt?["id"] as? String, let body = promptBody() else { return }
		let generation = promptGeneration
		loadReferences(id, after: nil, collected: []) { [weak self] refs in
			guard let self, self.matchesPrompt(body, generation: generation) else { return }
			let names = refs.compactMap { $0["name"] as? String }
			guard names.isEmpty else { self.feedback.stringValue = "Prompt is used by: " + names.joined(separator: ", "); return }
			let alert = NSAlert()
			alert.messageText = "Remove this prompt?"
			alert.informativeText = "Historical instruction versions remain available to existing results."
			alert.addButton(withTitle: "Remove")
			alert.addButton(withTitle: "Cancel")
			guard alert.runModal() == .alertFirstButtonReturn else { return }
			self.request("DELETE", "/api/config/prompts", ["id": id]) { [weak self] _ in
				guard let self else { return }
				self.loadLists()
				guard self.matchesPrompt(body, generation: generation) else { return }
				self.resetPrompt()
				self.feedback.stringValue = "Prompt removed."
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

#if DEBUG
	func debugSetServices(_ rows: [[String: Any]]) {
		serviceRows = rows
		binding.removeAllItems()
		binding.addItems(withTitles: rows.map { serviceLabel($0) })
	}

	func debugSelectBinding(_ id: String, selected: String? = nil) {
		guard let index = serviceRows.firstIndex(where: { $0["id"] as? String == id }) else { return }
		binding.selectItem(at: index)
		loadBinding(id, selected: selected)
	}

	func debugVisibleBinding() -> String? { visibleBindingID() }
	func debugTargets() -> [String] { target.itemArray.compactMap { $0.title } }
	func debugPromptBody() -> [String: Any]? { promptBody() }

	func debugShowPrompt(_ id: String) { showPrompt(id) }
	func debugPromptSnapshot() -> [String: Any] {
		["id": currentPrompt?["id"] as Any, "text": instructions.string,
		 "serviceId": selectedBinding?["id"] as Any, "target": target.selectedItem?.title as Any]
	}

	func debugSetPromptEditor(_ body: [String: Any]) {
		promptGeneration += 1
		currentPrompt = body
		promptName.stringValue = body["name"] as? String ?? ""
		instructions.string = body["text"] as? String ?? ""
		role.selectItem(at: body["role"] as? String == "curator" ? 0 : 1)
		guard let serviceID = body["serviceId"] as? String,
			  let service = serviceRows.first(where: { $0["id"] as? String == serviceID }) else { return }
		selectedBinding = service
		if let index = serviceRows.firstIndex(where: { $0["id"] as? String == serviceID }) { binding.selectItem(at: index) }
		target.removeAllItems()
		target.addItem(withTitle: body["target"] as? String ?? "")
		target.selectItem(at: 0)
	}

	func debugEditPromptText(_ text: String) { promptGeneration += 1; instructions.string = text }
	func debugCopyPrompt() { copyPromptAction() }
	func debugApplyResult(_ result: [String: Any], input: MigrationReviewState.Input) {
		migrationChoices = input.choices
		editorServices = input.editorServices
		currentService = serviceRows.first(where: { $0["id"] as? String == input.serviceID })
		if let index = serviceRows.firstIndex(where: { $0["id"] as? String == input.serviceID }) { services.selectItem(at: index) }
		let ticket = migrationReview.beginApply(input)
		acceptApplyResult(result, ticket: ticket)
	}
	func debugApplyAcknowledgement(_ input: MigrationReviewState.Input) -> String {
		migrationReview.applyAcknowledgement(for: input)
	}
	func debugReadbackFailure(_ input: MigrationReviewState.Input) -> String {
		migrationReview.readbackFailure(for: input)
	}
#endif
}
