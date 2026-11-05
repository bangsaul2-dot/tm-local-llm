# SecureFrame version archive — staging policy

Target versions: V11.2 through V11.6.2.

Status: **source import pending confidentiality review**. Do not interpret this branch as a deployed release.

Only approved Python, shell, documentation and synthetic tests may be committed.

Never commit customer PDF/PPT/RAW(P)/PNG, original SFT diagrams, local input, SQLite, approved graphs, extracted evidence, analysis output, credentials, internal network details or private model artifacts.

Source code can itself contain customer-specific labels, formulas, paths and quoted material. Before uploading snapshots, review each source file and remove or generalize such content. A filename extension allowlist and .gitignore alone do not establish that a file is safe to publish.

Runtime workflow: clone repository, then provision authorized inputs and DBs locally outside Git tracking. GitHub is not the system of record for customer documents.

Review gate: inventory → source content scan → human security authorization → commit to this branch → review before merge. Do not fabricate historical Git commit dates.
