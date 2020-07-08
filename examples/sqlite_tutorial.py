import argparse
from dataclasses import dataclass
import os
import sqlite3
import tempfile
from tempfile import NamedTemporaryFile, TemporaryDirectory
from urllib import request
from zipfile import ZipFile


# The following classes are used as signals from within the
# db query method
class FileClosed:
    pass


class QueryIssue:
    def __init__(self, query):
        self.query = query

    def __str__(self):
        return f"There was a problem executing {self.query}"


class InvalidTable:
    def __str__(self):
        return "The selected table is not part of this demo"


class Results:
    __match_args__ = ("size", "results")

    def __init__(self, results):
        self.results = results

    @property
    def size(self):
        return len(self.results)


# These classes represent results of a database query
@dataclass
class Artist:
    name: str

    def __str__(self):
        return self.name


@dataclass
class Album:
    name: str
    artist: str

    def __str__(self):
        return f"{self.name} by {self.artist}"


@dataclass
class Track:
    name: str
    album: str
    artist: str

    def __str__(self):
        return f"{self.name} on {self.album} by {self.artist}"


# Temporary database accessor
class TempDB:
    """This class is a wrapper around an sqlite database. It fetches the
    database from a remote source and extracts it into a temporary file.
    A connection to this database is then created and stored.
    """
    file_url = ("https://cdn.sqlitetutorial.net/wp-content/uploads/2018/03/"
                "chinook.zip")

    def __init__(self, temp_dir):
        self._temp_dir = temp_dir
        self._populate_db()
        self._connect()
        self._valid_tables = ("tracks", "albums", "artists")

    def _populate_db(self):
        # fetch the database into a local file
        with tempfile.NamedTemporaryFile() as tmp_zip_file:
            request.urlretrieve(self.file_url, filename=tmp_zip_file.name)
            with ZipFile(tmp_zip_file, 'r') as zip_obj:
                zip_obj.extract('chinook.db', self._temp_dir)

    def _connect(self):
        # build the connections to the database
        self._connection = sqlite3.connect(os.path.join(self._temp_dir,
                                                        "chinook.db"))
        self._cursor = self._connection.cursor()

    def execute_query(self, query: str):
        """Executes a query against the stored db connection. This method
        supports a single query string which it used to generate resulting
        rows which are then matched against known row patterns. The results
        are used to construct new objects and are returned inside a results
        object.

        This function will never raise a database exception. All returns are
        instances of signalling classes. Any exceptions will be truly
        exceptional behavior.

        Additionally the method checks against a few other conditions,
        and returns various signals if appropriate.
        """
        if not os.path.exists(self._temp_dir):
            # Verify the temp directory has not been destroyed
            return FileClosed()
        if not sum((table in query for table in self._valid_tables)):
            # only query against a sub set of tables
            return InvalidTable()
        results = []
        try:
            for row in self._cursor.execute(query):
                match row:
                    # this represents rows from the artist table
                    case (_, artist):
                        results.append(Artist(artist))
                    # This case is rows from album joined with artist
                    case (_, title, _, _, artist):
                        results.append(Album(title, artist))
                    # This case is rows from track joined with album
                    # joined with artist
                    case (_, name, *_, album, _, _, artist):
                        results.append(Track(name, album, artist))
            return Results(results)

        except sqlite3.Error as e:
            # Return a query signal if there was a failure
            return QueryIssue(query)


class Runner:
    def __init__(self, args, temp_dir):
        self.args = args
        self.db = TempDB(temp_dir)
        self._recursion = 0

    def _run_impl(self, query):
        # Run the query and respond appropriately to the returned signal
        match self.db.execute_query(query):
            case FileClosed(_):
                # The file was closed some how, create a new temp file and
                # recreate the db and re-execute
                with TemporaryDirectory as temp_dir:
                    self.db = TempDB(temp_dir)
                    self._recursion += 1
                    if self._recursion < 2:
                        self._run_impl(query)
                        self._recursion = 0
                    else:
                        print("Too many layers of recursion, problem with db object")
                        return QueryIssue(query)
            case InvalidTable(return_value):
                print(return_value)
            case Results(0, _):
                print("There are no results to return")
            case Results(_, results):
                for r in results:
                    print(r)
            case QueryIssue(issue):
                print(issue)

    def run(self):
        # Generate the query and call the implementation
        if self.args.tracks is not None:
            if self.args.tracks:
                clause = f"artists.Name = '{self.args.tracks}'"
            else:
                clause = 1
            self._run_impl("select * from tracks join albums "
                           "on tracks.albumid = albums.albumid join artists "
                           "on albums.artistid = artists.artistid where "
                           f"{clause};")

        if self.args.artists:
            self._run_impl("select * from artists;")

        if self.args.albums is not None:
            if self.args.albums:
                clause = f"artists.Name = '{self.args.albums}'"
            else:
                clause = 1
            self._run_impl("select * from albums join artists "
                           "on albums.artistid = artists.artistid where "
                           f"{clause};")


if __name__ == "__main__":
    msg = "Lookup info from a collection of music"
    parser = argparse.ArgumentParser(description=msg)
    parser.add_argument("--tracks", metavar="artist",
                        help='List all the tracks from an artist in the'
                        ' database, use "" for all artists')
    parser.add_argument("--artists", action="store_const", const=True,
                        help="List all the artists in the database")
    parser.add_argument("--albums", metavar="artist",
                        help='List the albums from an artist in the database,'
                        ' use "" for all artists')

    args = parser.parse_args()
    with tempfile.TemporaryDirectory() as temp_dir:
        Runner(args, temp_dir).run()
