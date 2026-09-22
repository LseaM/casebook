# XMind handoff

AITest modification based on Casebook 0.9.0.

Open a YAML file in the Casebook review page. Tick individual case IDs, or use **Select file** to select the complete current file. **Export selected XMind** downloads the selected cases across the active scan scope. **Export all XMind** downloads every case in that scope. **Clear** removes the current selection.

**Mark AI** adds `[AI]` before each stable case ID in the XMind topic title. It is a manual export choice. Casebook's `auto` field means automated execution; it is not an AI origin flag. The export does not record a review decision or calculate a metric.

The file contains module and feature branches, then one topic per case with its ID, title, description, priority, type, preconditions, steps, and expected results. It is an editable handoff copy and never updates the YAML source.

When Casebook is reading an AITest `casebook-workspace` projection, the download also verifies that the formal case file and traceability file still match the hashes bound to the projection. It rejects a projection changed in the review page or stripped of its source binding. Apply accepted edits to the formal YAML, validate the workflow, and regenerate the Casebook projection before downloading.
