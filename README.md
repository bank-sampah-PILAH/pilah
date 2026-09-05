# PILAH

This repository is the PILAH workspace. It wires together the backend and
mobile application as Git submodules and stores shared development workflows.

## Prerequisites

- Git
- Python 3.12 for the backend
- Flutter 3.41.3 and Dart 3.11.1 for the mobile app
- CodeGraph, if code navigation indexes are needed
- GitHub access to `pilah-be` and `pilah-mobile`

## Clone And Set Up

Clone the workspace with both submodules:

```bash
git clone --recurse-submodules git@github.com:bank-sampah-PILAH/pilah.git
cd pilah
```

For an existing checkout, initialize or refresh the submodules:

```bash
git submodule sync --recursive
git submodule update --init --recursive
```

Check the checked-out submodule revisions with:

```bash
git submodule status
```

## Backend

See [`pilah-be/README.md`](pilah-be/README.md) for Docker and API details.

For direct local development:

```bash
cd pilah-be
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py runserver 0.0.0.0:8000
```

Run backend tests with:

```bash
python manage.py test
```

## Mobile

See [`pilah-mobile/README.md`](pilah-mobile/README.md) for flavors and
application details.

From the mobile directory:

```bash
cd pilah-mobile
flutter pub get
dart run build_runner build --delete-conflicting-outputs
flutter run
```

Run mobile validation with:

```bash
flutter analyze
flutter test
```

## CodeGraph

Initialize an index for the workspace and each application:

```bash
codegraph init .
codegraph init pilah-be
codegraph init pilah-mobile
```

`.codegraph/` contains machine-local index data. Only its ignore marker belongs
in Git; do not commit databases, logs, or runtime files.

## Folder Layout

```text
pilah/
├── .agents/                  Shared multi-repository skills
├── .codegraph/               Local CodeGraph index data
├── .gitmodules               Submodule definitions
├── AGENTS.md                 Workspace instructions
├── pilah-be/                 Backend Git submodule
├── pilah-mobile/             Mobile Git submodule
├── pilah-be-worktrees/       Local backend PR worktrees (ignored)
├── pilah-mobile-worktrees/   Local mobile PR worktrees (ignored)
└── README.md                This guide
```

The root repository owns workspace wiring and shared configuration. Keep
backend changes in `pilah-be` and mobile changes in `pilah-mobile`.

## Git Workflow

- Keep canonical submodule checkouts on `main` and clean.
- Use a sibling worktree for feature or fix work.
- Use the shared multi-ship workflow when one change spans both applications.
- Use the shared multi-LGTM workflow to preflight, merge, and clean up matching
  pull requests.
- Read the application `AGENTS.md` before running repository-specific checks.
