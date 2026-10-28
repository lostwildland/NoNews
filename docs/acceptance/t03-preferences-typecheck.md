# T03 narrow preferences typecheck

The coordinator checked the actual ProcessingEngine and ProcessingPreferencesViewController sources without starting an engine, application or Xcode build. Existing compiled Swift dependencies came from the accepted T02 Debug products; no dependency was rebuilt.

The earlier missing RSDatabaseObjC diagnostic was caused by generated Clang module maps pointing into a removed acceptance-source copy. Two temporary module maps named RSDatabaseObjC and RSCoreObjC used the existing accepted T02 header tree instead. The maps, extracted source and private module cache lived in a TemporaryDirectory and were removed afterward. No shared build cache or generated module map was edited.

At pinned5154f96, both native files typechecked successfully with Swift6, DEBUG, the installed macOS SDK and arm64-apple-macos15.0. This exposed a warning: the nested gatewayName function accessed main-actor state from a nonisolated context. Source324f40d preserves that function, including its use of the service-label method.

The coordinator added an explicit MainActor annotation to that function. The current two native files then passed the same narrow typecheck with warnings-as-errors and no diagnostics. The effective command was `xcrun swiftc -typecheck -warnings-as-errors -swift-version 6 -D DEBUG -target arm64-apple-macos15.0`, with the SDK path, accepted Debug product/module search paths, the two temporary Clang maps and private module-cache path supplied explicitly. This is source typechecking, not a linked app build.

The owner's failing greater-than16MiB public migration regression and its existing evidence note were preserved uncommitted. This check does not establish complete large-report handling, declared-runtime or native request behavior, Keychain, UI layout/accessibility, signing or T11 runner continuity. Fresh correction review and the final native acceptance gates remain required.
