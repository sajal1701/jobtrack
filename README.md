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

## Add your first application

1. Enter the **Company** and **Role** in the **Add an application** form.
2. Choose a **Stage**. Use Saved for a role you want to apply to, or Applied
   once you have submitted your application.
3. Optionally add a job link, follow-up date, and notes, then click
   **Save application**.
4. Your application appears under **Your opportunities**. Change its stage
   using the dropdown on its card as you make progress.

Use **Search company or role** and **All stages** to find applications.
The summary counts cover your whole tracker, even when filters are active.
Click **View role** to open a saved job link. **Delete** asks for confirmation
before removing the record; there is no undo.

## Your data

Applications are stored in `.data/jobtrack.sqlite3` inside the project folder.
They survive browser refreshes and server restarts. There is no cloud account
or sync between computers.

To make a backup, stop the app and copy `.data/jobtrack.sqlite3` to a safe
location. To restore it, stop the app and replace that file with your backup.
Replacing the file replaces the tracker’s current records.

## Current limitations

- JobTrack is intended for one person using it locally; it has no login or
  shared accounts.
- The browser shows up to 100 matching applications. Narrow the search or
  stage filter to find a record.
- You can change stages in the browser, but editing other saved details is
  still planned.
- Follow-up dates are displayed on application cards; they do not send reminders.
- CSV import and export are not available yet.

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
