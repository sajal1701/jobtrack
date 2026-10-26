# JobTrack

Keep your job applications, notes, and next steps in one place. JobTrack runs
on your computer and saves your applications locally, so you can pick up where
you left off after closing the app.

## What you can do

- Save a company, role, job link, notes, and an optional follow-up date.
- Track each application as Saved, Applied, Interview, Offer, or Rejected.
- Search by company or role and filter by stage.
- See your total applications, interviews, and offers at a glance.
- Open the original job listing or delete an application you no longer need.
- Download matching applications as a CSV file.

## Get started

You need Python 3.11 or newer, Git, and a terminal with Bash. The commands below
are intended for macOS or Linux. Setup needs an internet connection to download
dependencies.

```bash
git clone https://github.com/sajal1701/jobtrack.git
cd jobtrack
bash scripts/setup.sh
bash scripts/run.sh
```

Open [JobTrack](http://127.0.0.1:8010) in your browser. Keep the terminal running
while you use the app. To stop it, press **Control+C** in that terminal.

Setup is only needed the first time. To use JobTrack again, open a terminal in
the `jobtrack` folder and run:

```bash
bash scripts/run.sh
```

## Your account

Choose a username and a password on the sign-in screen, then click **Create
account**. Usernames use 3–50 letters, numbers, underscores, or hyphens and are
case-insensitive. Passwords require 12–128 characters.

Each account has its own applications, statistics, and CSV exports. Sessions
last up to 24 hours; use **Sign out** to end a session immediately. Sign in with
the same account next time. Password reset is not available yet.

## Add your first application

1. Enter the **Company** and **Role** in the **Add an application** form.
2. Choose a **Stage**. Use Saved for a role you want to apply to, or Applied
   once you have submitted your application.
3. Optionally add a job link, follow-up date, and notes, then click
   **Save application**.
4. Your application appears under **Your opportunities**. Change its stage
   using the dropdown on its card as you make progress.

Use **Search company or role** and **All stages** to find applications.
Click **Clear filters** to reset both filters and show all applications again.
You can also press **Escape** while the search field is focused.
The summary counts cover your whole tracker, even when filters are active.
Click **View role** to open a saved job link. **Delete** asks for confirmation
before removing the record; there is no undo.

Click **Download CSV** to export all applications matching your current search
and stage filter, including matches beyond the 100 shown in the browser. Clear
the search and choose **All stages** to export the whole tracker. The file
includes notes and follow-up dates; an empty result downloads column headers.

## Your data

Applications are stored in `.data/jobtrack.sqlite3` inside the project folder.
They survive browser refreshes and server restarts. Accounts are stored in the same local database. There is no sync between
computers. A database backup includes accounts and sessions, so keep it private.

To make a backup, stop the app and copy `.data/jobtrack.sqlite3` to a safe
location. To restore it, stop the app and replace that file with your backup.
Replacing the file replaces the tracker’s current records.

## Current limitations

- JobTrack runs locally by default. Public hosting still needs HTTPS, secure
  cookie configuration, and persistent storage (see the development guide).
- The browser shows up to 100 matching applications. Narrow the search or
  stage filter to find a record.
- You can change stages in the browser, but editing other saved details is
  still planned.
- Follow-up dates are displayed on application cards; they do not send reminders.
- CSV import is not available yet.

## Upgrading from the version without accounts

Existing applications are preserved, but remain hidden until a local
administrator assigns them to an account. Register your account, stop the app,
back up the database, then run (replace `your_username` with your account):

```bash
.venv/bin/python scripts/claim_legacy.py your_username
```

This assigns all unowned records to that account. It leaves records already
owned by other accounts unchanged. Restart the app to see your applications.

## Troubleshooting

- **Python version error:** setup requires Python 3.11 or newer. If you have
  multiple versions installed, select one with
  `PYTHON_BIN=python3.12 bash scripts/setup.sh`.
- **“Run bash scripts/setup.sh first”:** run setup from the project folder,
  then start the app again.
- **The browser cannot connect:** keep the server terminal open and check it
  for errors. The app uses port 8010; another process using that port must be
  stopped before JobTrack can start.

For technical details, API endpoints, and test commands, see
[the development guide](DEVELOPMENT.md). Planned features are listed in
[the roadmap](ROADMAP.md).
