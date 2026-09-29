## Note on Migrations

Since the CCI Data Bridge database is always repopulated from a spreadsheet import there is no longer a need for a persistent database. The database is rebuilt by importing the spreadsheet every time the application restarts as it is a very quick process. The database sits inside the application pod in a non-persistent volume mount.

The consequences of this are that there is no need to persist migrations between versions. In some cases migrations, especially where relations are being added, will cause issues for a database that is empty. It is therefore simpler to just remove all migration files and rerun `makemigrations` when there is a change. The fresh database structure can then have the relevant content imported from the spreadsheet.