# Native UI observation status

2026-10-28. These observations concern the isolated acceptance app only. They are not a rendered UX audit, visible Ready proof or score.

Before the r8 launch notification, CUA `getState` returned no inventory error but listed only the installed regular NetNewsWire identifier as not running; no acceptance surface was listed. The coordinator did not select or launch that regular/private profile.

After the original T02 owner delivered r8, the coordinator verified the relocated normal app at `/tmp/nonews-t02-r8-installed/NetNewsWire.app`: deep strict signature and isolated identity passed; its embedded `server.py` matched current source with SHA-256 `eb3b5c247c3a7fa0fed7123f79f91888478f9e38241e42ef093352ab0407f41d`. Process readback showed app PID43073 at that exact bundle path and bundled Python child PID43078 with parent43073. Artifact code HEAD is `4985b2f4bfe634edd7a6f0ca62567b96d45c12a3`; branch HEAD `3e218ade1fae4c9ff5a459979b6a1b3c3f920037` adds evidence only.

The bounded current-build CUA selection `cua.getApp('/tmp/nonews-t02-r8-installed/NetNewsWire.app')` returned `Computer Use server error -10005: cgWindowNotFound`. No AX tree, screenshot, Settings pane, focus, appearance or accessibility state was observed. A running app/child is insufficient proof that the UI is visible or Ready.

No permission, display, account or security setting was changed. No AppleScript/JXA/shell screenshot or alternate native-input workaround was used. Do not infer a locked screen or a particular permission failure from this error. The prior operational user question remains unanswered; do not repeat it or treat elapsed time as an answer.

Native UI/accessibility/Impeccable acceptance remains open. Subsequent native tests may gracefully stop this exact isolated app after rechecking process identities; the listed PIDs are observations, not permanent authority. Meaningful implementation and review work can continue while this UI evidence is unavailable. No goal completion or blanket ticket acceptance follows from this record.
