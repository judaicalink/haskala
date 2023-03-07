# The Library of the Haskala

The Library of the [Haskala](https://www.haskala-library.net/) is a database for the Haskala.

It is a built on Django 4.2. and Wagtail 4.1.2.

The data is build as RDF-Turtle, which was exported from the previous project (a Drupal database).
To serve the data you need a triple store (Apache Jena Fuseki).
The data is fetched from the triple store with [pubby-django] (https://github.com/lod-pubby/pubby-django).

## Installation
Clone the repositoryi `git clone `. 

Go into the directory `cd haskala`.

Activate the venv `source venv/bin/activate`.

Install the requirements `pip install -r requirements.txt`.

Migrate and apply the migrations `python manage.py makemigrations && python manage.py migrate`.

Start the server with `python manage.py runserver`.

## Data

There is a directory named `data` for the data containing the triple files.

To apply the data run the script.
