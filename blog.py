# all the imports
import os
import sqlite3
from flask import Flask, request, session, g, redirect, url_for, abort, \
    render_template, flash

# create our little application
app = Flask(__name__)
app.config.from_object(__name__)

# Load default config and override config from an environment variable
app.config.update(dict(
    DATABASE=os.path.join(app.root_path, 'flaskr.db'),
    SECRET_KEY='development key',
    USERNAME='admin',
    PASSWORD='default'
))
app.config.from_envvar('FLASKR_SETTINGS', silent=True)


def connect_db():
    """Connects to the specific database."""
    rv = sqlite3.connect(app.config['DATABASE'])
    rv.row_factory = sqlite3.Row
    return rv


def get_db():
    """Opens a new database connection if there is none yet for the
    current application context.
    """
    if not hasattr(g, 'sqlite_db'):
        g.sqlite_db = connect_db()
    return g.sqlite_db


@app.teardown_appcontext
def close_db(error):
    """Close the databse again at the end of request."""
    if hasattr(g, 'sqlite_db'):
        g.sqlite_db.close()


def init_db():
    db = get_db()
    with app.open_resource('schema.sql', mode='r') as f:
        db.cursor().executescript(f.read())
    db.commit()


@app.cli.command('initdb')
def initdb_command():
    """Initializes the database."""
    init_db()
    print 'Initialized the databse.'


@app.route('/')
def show_entries():
    db = get_db()
    cur = db.execute("select id, title, text from entries where status='published' order by id desc")
    entries = cur.fetchall()
    return render_template('show_entries.html', entries=entries)


@app.route('/admin')
def administration():
    if not session.get('logged_in'):
        abort(401)
    return render_template('admin_main.html')

@app.route('/admin/drafts')
def draft_list():
    db = get_db()
    cur = db.execute("select id, title from entries where status='draft' order by id desc")
    drafts = cur.fetchall()
    return render_template('show_drafts.html', drafts=drafts)

@app.route('/admin/new_draft', methods=['POST', 'GET'])
def add_draft():
    if not session.get('logged_in'):
        abort(401)
    if request.method == 'POST':
        status = 'published' if 'publish' in request.form else 'draft'
        db = get_db()
        db.execute("insert into entries (title, text, status) values (?, ?, ?)",
                   [request.form['title'], request.form['text'], status])
        db.commit()
        flash('New entry was successfully posted')
        if status == 'published':
            return redirect(url_for('post_list'))
        else:
            return redirect(url_for('draft_list'))
    return render_template('write_entry.html')

@app.route('/admin/edit_draft/<int:draft_id>', methods=['POST', 'GET'])
def edit_draft(draft_id):
    if not session.get('logged_in'):
        abort(401)
    db = get_db()
    if request.method == 'POST':
        status = 'published' if 'publish' in request.form else 'draft'
        query = "UPDATE entries SET title=?,text=?,status=? WHERE id=?"
        db.execute(query, [request.form['title'], request.form['text'], status, draft_id])
        db.commit()
        flash('Entry was successfully updated')
        if status == 'published':
            return redirect(url_for('post_list'))
        else:
            return redirect(url_for('draft_list'))
    cur = db.execute('SELECT id, title, text from entries where id=(?)', [draft_id])
    entry = cur.fetchone()
    return render_template('write_entry.html', entry=entry)

@app.route('/admin/delete_entry/<int:entry_id>', methods=['GET'])
def delete_entry(entry_id):
    if not session.get('logged_in'):
        abort(401)
    db = get_db()
    db.execute("DELETE FROM entries WHERE id=(?)", [entry_id])
    db.commit()
    flash('Entry was successfully deleted')
    return redirect(redirect_url())

@app.route('/admin/posts', methods=['GET'])
def post_list():
    db = get_db()
    cur = db.execute("SELECT id, title FROM entries WHERE status='published' ORDER BY id DESC")
    posts = cur.fetchall()
    return render_template('show_posts.html', posts=posts)

@app.route('/view/<int:post_id>', methods=['GET'])
def view_entry(post_id):
    db = get_db()
    cur = db.execute('select title, text from entries where id=(?)', [post_id])
    entry = cur.fetchone()
    return render_template('show_entry.html', entry=entry)


@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        if request.form['username'] != app.config['USERNAME']:
            error = 'Invalid username'
        elif request.form['password'] != app.config['PASSWORD']:
            error = 'Invalid password'
        else:
            session['logged_in'] = True
            flash('You were logged in')
            return redirect(url_for('show_entries'))
    return render_template('login.html', error=error)


@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    flash('You were logged out')
    return redirect(url_for('show_entries'))

def redirect_url(default='index'):
    return request.args.get('next') or \
           request.referrer or \
           url_for(default)